#要改日期
from pymongo import MongoClient
import requests
from datetime import datetime, timedelta
import time

# 連接到 MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['test']  # 替換為你的資料庫名稱
collection = db['price']  # 替換為你的資料集名稱

# 定義日期區間的起始和結束日期
start_date_str = "2024-11-29"  # 起始日期
end_date_str = "2024-12-10"  # 結束日期

# 將日期轉換為 datetime 物件
start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

# 遍歷日期區間內的每一天
current_date = start_date
while current_date <= end_date:
    query_date = current_date.strftime("%Y-%m-%d")  # 資料庫中的日期格式
    twse_date = current_date.strftime("%Y%m%d")  # API 請求中的日期格式

    print(f"Fetching data for {query_date}...")

    # 從指定的網址抓取交易量的 JSON 資料
    url = f"https://wwwc.twse.com.tw/rwd/zh/fund/T86?date={twse_date}&selectType=ALLBUT0999&response=json"
    response = requests.get(url)

    # 檢查是否成功取得資料
    if response.status_code == 200:
        data = response.json()

        # 如果 JSON 檔案裡 stat 提示沒有資料，則跳過該日期
        if data.get("stat") == "很抱歉，沒有符合條件的資料!":
            print(f"No data available for {query_date}, skipping...")
        else:
            # 查詢資料庫中指定日期的資料
            docs = collection.find({"date": query_date})

            # 開始比對資料庫中的代號
            for doc in docs:
                code = doc['code']  # 資料庫中的證券代號

                # 尋找抓取資料中匹配的代號
                for entry in data['data']:
                    if entry[0] == code:  # 假設 entry[0] 是 JSON 中的證券代號
                        # 將四筆交易量資料存入該筆資料
                        foreign = int(entry[4].replace(",", ""))  # 外資
                        investment = int(entry[10].replace(",", ""))  # 投信
                        dealer = int(entry[11].replace(",", ""))  # 自營商
                        investors = int(entry[-1].replace(",", ""))  # 三大法人

                        # 更新資料庫
                        collection.update_one(
                            {"_id": doc['_id']},
                            {"$set": {
                                "foreign": foreign,
                                "investment": investment,
                                "dealer": dealer,
                                "investors": investors
                            }}
                        )

            print(f"{query_date} completed")
    else:
        print(f"Failed to fetch data from the URL for {query_date}, status code: {response.status_code}")

    # 移動到下一天
    current_date += timedelta(days=1)
    time.sleep(10)

print("Data fetching completed.")
