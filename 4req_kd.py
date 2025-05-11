#不用輸入日期
from pymongo import MongoClient
import pandas as pd
from pymongo import UpdateOne
import numpy as np

# 連接到 MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['test']  # 替換為您的資料庫名稱
collection = db['price']  # 替換為您的資料集合名稱

# 查詢每支股票的數據，轉換為 pandas DataFrame
def get_stock_data(stock_code):
    cursor = collection.find({"code": stock_code}, {"_id": 0, "date": 1, "close": 1, "high": 1, "low": 1})
    data = list(cursor)
    
    # 將查詢結果轉換為 pandas DataFrame
    df = pd.DataFrame(data)
    
    # 確保日期格式正確，並且按日期排序
    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
    df = df.sort_values(by='date')

    return df

# 計算 KD 指標
def calculate_kd(df, period=9):
    df['low_min'] = df['low'].rolling(window=period, min_periods=1).min()  # 週期內最低價
    df['high_max'] = df['high'].rolling(window=period, min_periods=1).max()  # 週期內最高價
    
    # 計算分母
    df['denominator'] = df['high_max'] - df['low_min']
    
    # 處理分母為零的情況，避免除以零
    df['RSV'] = np.where(
        df['denominator'] != 0,
        (df['close'] - df['low_min']) / df['denominator'] * 100,
        50  # 或者設定為您認為合適的值，例如 50
    )
    
    # 確保 RSV 在 0 到 100 之間
    df['RSV'] = df['RSV'].clip(lower=0, upper=100)
    
    # 填充可能的 NaN 值
    df['RSV'] = df['RSV'].fillna(50)  # 當 RSV 計算出 NaN 時，設置預設值為 50
    
    # 初始化 K 和 D，確保型別為 float
    df['K'] = 50.0
    df['D'] = 50.0
    
    # 從第二行開始計算 K 和 D（K 和 D 的初始值設為 50）
    for i in range(1, len(df)):
        df.loc[df.index[i], 'K'] = ((2/3) * df.loc[df.index[i-1], 'K']) + ((1/3) * df.loc[df.index[i], 'RSV'])
        df.loc[df.index[i], 'D'] = ((2/3) * df.loc[df.index[i-1], 'D']) + ((1/3) * df.loc[df.index[i], 'K'])
    
    # 確保 K 和 D 在 0 到 100 之間
    df['K'] = df['K'].clip(lower=0, upper=100)
    df['D'] = df['D'].clip(lower=0, upper=100)
    
    return df[['date', 'K', 'D']]

# 批量更新每支股票的 KD 到資料庫
def update_stock_with_kd(stock_code, df):
    operations = []
    for index, row in df.iterrows():
        k_value = row['K']
        d_value = row['D']
        
        # 檢查 K 和 D 是否為 NaN，若為 NaN 則設置為 0，否則進行四捨五入
        if pd.isna(k_value):
            k_value = 0  # 這裡設置為 0，您可以根據需求設置其他值
        else:
            k_value = round(k_value, 2)

        if pd.isna(d_value):
            d_value = 0  # 這裡設置為 0，您可以根據需求設置其他值
        else:
            d_value = round(d_value, 2)

        operations.append(UpdateOne(
            {"code": stock_code, "date": row['date'].strftime('%Y-%m-%d')},
            {"$set": {
                "K": k_value,  # 設置處理後的 K 值
                "D": d_value   # 設置處理後的 D 值
            }},
            upsert=True
        ))
    
    # 批量更新
    if operations:
        collection.bulk_write(operations)

# 處理每支股票
def process_all_stocks(batch_size=100):
    # 查詢所有股票代碼
    stock_codes = collection.distinct("code")

    # 分批處理股票代碼
    for i in range(0, len(stock_codes), batch_size):
        batch = stock_codes[i:i + batch_size]
        for stock_code in batch:
            print(f"處理股票: {stock_code}")
            
            # 1. 獲取該股票的所有數據
            stock_data = get_stock_data(stock_code)
            
            if not stock_data.empty:
                # 2. 計算 KD
                kd_result = calculate_kd(stock_data)
                
                # 3. 更新 KD 到資料庫
                update_stock_with_kd(stock_code, kd_result)

# 執行所有股票的處理
process_all_stocks()
