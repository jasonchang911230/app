#不用輸入日期
from pymongo import MongoClient
import pandas as pd

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

    # 填充或處理 null 值
    df['close'] = df['close'].ffill()  # 用前一個有效值填充
    df['close'] = df['close'].fillna(0)  # 如果前面沒有有效值，則填 0
    
    return df

# 計算 MACD 指標
def calculate_macd(df):
    # 計算指數移動平均 (EMA)
    def calculate_ema(series, span):
        return series.ewm(span=span, adjust=False).mean()

    df['12_EMA'] = calculate_ema(df['close'], 12)
    df['26_EMA'] = calculate_ema(df['close'], 26)
    df['MACD'] = df['12_EMA'] - df['26_EMA']
    df['Signal'] = calculate_ema(df['MACD'], 9)
    df['MACD_Histogram'] = df['MACD'] - df['Signal']
    
    # 將所有值四捨五入到小數點後兩位
    df['MACD'] = df['MACD'].round(2)
    df['Signal'] = df['Signal'].round(2)
    df['MACD_Histogram'] = df['MACD_Histogram'].round(2)
    
    return df[['date', 'MACD', 'Signal', 'MACD_Histogram']]

# 批量更新每支股票的技術指標到資料庫
from pymongo import UpdateOne

def update_stock_with_macd(stock_code, df):
    operations = []
    for index, row in df.iterrows():
        operations.append(UpdateOne(
            {"code": stock_code, "date": row['date'].strftime('%Y-%m-%d')},
            {"$set": {
                "MACD": row['MACD'],
                "Signal": row['Signal'],
                "MACD_Histogram": row['MACD_Histogram']
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
            
            # 1. 獲取該股票的數據
            stock_data = get_stock_data(stock_code)
            
            if not stock_data.empty:
                # 2. 計算 MACD
                macd_result = calculate_macd(stock_data)
                
                # 3. 更新資料庫
                update_stock_with_macd(stock_code, macd_result)

# 執行所有股票的處理
process_all_stocks()
