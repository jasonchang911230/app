#不用輸入日期
from pymongo import MongoClient
import pandas as pd
from pymongo import UpdateOne

# 連接到 MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['test']  # 替換為您的資料庫名稱
collection = db['price']  # 替換為您的資料集合名稱

# 查詢每支股票的數據，轉換為 pandas DataFrame
def get_stock_data(stock_code):
    cursor = collection.find({"code": stock_code}, {"_id": 0, "date": 1, "close": 1})
    data = list(cursor)
    
    # 將查詢結果轉換為 pandas DataFrame
    df = pd.DataFrame(data)
    
    # 確保日期格式正確，並且按日期排序
    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
    df = df.sort_values(by='date')

    return df

# 計算 RSI
def calculate_rsi(df, period=14):
    df['price_diff'] = df['close'].diff()  # 計算收盤價的變動
    df['gain'] = df['price_diff'].apply(lambda x: x if x > 0 else 0)  # 上漲部分
    df['loss'] = df['price_diff'].apply(lambda x: -x if x < 0 else 0)  # 下跌部分

    # 計算平均上漲和下跌
    df['avg_gain'] = df['gain'].rolling(window=period, min_periods=1).mean()
    df['avg_loss'] = df['loss'].rolling(window=period, min_periods=1).mean()

    # 計算 RS 和 RSI
    df['RS'] = df['avg_gain'] / df['avg_loss']
    df['RSI'] = 100 - (100 / (1 + df['RS']))

    # 只保留 RSI 和日期欄位
    return df[['date', 'RSI']]

# 批量更新每支股票的 RSI 到資料庫
def update_stock_with_rsi(stock_code, df):
    operations = []
    for index, row in df.iterrows():
        rsi_value = row['RSI']
        
        # 檢查 RSI 是否為 NaN，如果是則設為 0 或跳過
        if pd.isna(rsi_value):
            rsi_value = 0  # 可以根據需求設置 NaN 的預設值
        else:
            rsi_value = round(rsi_value, 2)

        operations.append(UpdateOne(
            {"code": stock_code, "date": row['date'].strftime('%Y-%m-%d')},
            {"$set": {
                "RSI": rsi_value  # 設置四捨五入後的 RSI 值或預設值
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
                # 2. 計算 RSI
                rsi_result = calculate_rsi(stock_data)
                
                # 3. 更新 RSI 到資料庫
                update_stock_with_rsi(stock_code, rsi_result)

# 執行所有股票的處理
process_all_stocks()
