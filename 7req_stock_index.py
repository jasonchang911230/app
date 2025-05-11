#輸入日期
import requests
import pymongo
from datetime import datetime, timedelta
import time

def get_date_list(start_date_str, end_date_str):
    start_date = datetime.strptime(start_date_str, '%Y%m%d')
    end_date = datetime.strptime(end_date_str, '%Y%m%d')
    date_list = []
    delta = timedelta(days=1)
    while start_date <= end_date:
        date_list.append(start_date.strftime('%Y%m%d'))
        start_date += delta
    return date_list

# 定義開始和結束日期，格式為 'YYYYMMDD'
start_date_str = '20241129'
end_date_str = '20241210'

dates = get_date_list(start_date_str, end_date_str)

# 連接到 MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["test"]
collection = db["market_index"]

for date in dates:
    try:
        url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={date}&type=IND"
        response = requests.get(url)
        data = response.json()

        if "data1" not in data or not data["data1"]:
            print(f'{date} 無資料，跳過。')
            time.sleep(8)
            continue

        value = data["data1"][1][1]
        value = value.replace(',', '')
        value_int = int(float(value))

        # 插入資料到 MongoDB
        record = {"date": date, "value": value_int}
        collection.insert_one(record)
        print(f'{date} 股票指數獲取成功！')
    except Exception as e:
        print(f'{date} 獲取資料出錯：{e}')
        time.sleep(8)
        continue

    time.sleep(8)
