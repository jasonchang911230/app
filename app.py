from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
import sqlite3
from pymongo import MongoClient
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from dateutil import parser

app = Flask(__name__)
app.secret_key = 'anfinsfns38fhsjlk3h8f'

client = MongoClient('mongodb://localhost:27017/')
db = client['test']
#collection = db['price']

def get_stock_data():  #大盤
    client = MongoClient('mongodb://localhost:27017/')
    db = client['test']
    collection = db['market_index']

    query = collection.find({}, {"_id": 0, "date": 1, "value": 1}).sort("date", -1).limit(10)

    rows = list(query)

    client.close()

    rows = rows[::-1]

    dates = [row['date'] for row in rows]
    values = [row['value'] for row in rows]

    return dates, values

@app.route('/')#主頁路由
def index():
    dates, values = get_stock_data()
    return render_template('index.html', dates=dates, values=values)

@app.route('/register', methods=['GET', 'POST'])#註冊路由
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        collection = db['user']
        
        existing_user = collection.find_one({"username": username})
        if existing_user:
            flash('用戶名已存在，請選擇其他用戶名')
            return redirect(url_for('register'))

        if not username or not password:
            flash('用戶名和密碼不能為空')
            return redirect(url_for('register'))
        
        # 加密密碼
        hashed_password = generate_password_hash(password)
        
        # 將新用戶插入 MongoDB
        collection.insert_one({
            "username": username,
            "password": hashed_password
        })
        
        flash('註冊成功')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])#登入路由
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        collection = db['user']
        user = collection.find_one({"username": username})
        
        if user and check_password_hash(user['password'], password):  # 驗證密碼
            session['username'] = username
            flash('登入成功')
            return redirect(url_for('index'))
        else:
            flash('登入失敗，請重試')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('登出成功')
    return redirect(url_for('index'))

@app.route('/stock_search.html')
def stock_search():
    return render_template('stock_search.html')

def convert_date(date_str):
    if '/' in date_str:  # 如果日期是 "113/01/02" 這種格式
        year, month, day = date_str.split('/')
        year = int(year) + 1911  # 將民國年轉換為西元年
        return datetime(year, int(month), int(day))
    elif '-' in date_str:  # 如果日期是 "2024-01-04" 這種格式
        year, month, day = date_str.split('-')
        return datetime(int(year), int(month), int(day))
    else:
        raise ValueError(f"無法解析的日期格式: {date_str}")

'''@app.route('/api/data', methods=['GET'])
def get_code():
    stock_code = request.args.get('stock_code', '')
    query = {'code': {'$regex': f'^{stock_code}'}}
    code_data = list(db['price'].find(query, {
        '_id': 0,
        'name': 1,
        'code': 1,
        'date': 1,
        'open': 1,
        'high': 1,
        'low': 1,
        'close': 1,
        'price_change': 1,
        'changed_percent': 1
    }).sort('date', -1).limit(10))
    code_data.sort(key=lambda x: convert_date(x['date']), reverse=True)

    return jsonify(code_data)'''

'''@app.route('/revenue', methods=['GET'])
def revenue():
    months = db['revenue'].distinct('month')

    month = request.args.get('month')

    if month:

        raw_data = list(db['revenue'].find({'month': month}, {'_id': 0, 'stock_name': 1, 'stock_code': 1, 'month': 1, 'revenue': 1}))

        data = []
        for item in raw_data:
            revenue_str = item['revenue']
            revenue = int(revenue_str)
            item['revenue'] = revenue
            data.append(item)

        data = sorted(data, key=lambda x: x['revenue'], reverse=True)[:10]
    else:
        data = []

    return render_template('revenue.html', data=data, months=months)'''
    
@app.route('/revenue', methods=['GET'])
def revenue():
    months = db['revenue'].distinct('month')
    months.sort(reverse=True)

    month = request.args.get('month')

    if month:
        current_month_data = list(db['revenue'].find({'month': month}, {'_id': 0, 'stock_name': 1, 'stock_code': 1, 'month': 1, 'revenue': 1, 'growth_rate': 1}))

        for item in current_month_data:
            growth_rate = item.get('growth_rate', 0)
            if isinstance(growth_rate, str):
                try:
                    growth_rate = float(growth_rate)
                except ValueError:
                    growth_rate = 0.0
            item['growth_rate'] = growth_rate

        top_10_data = sorted(current_month_data, key=lambda x: x['growth_rate'], reverse=True)[:10]

        try:
            current_year, current_month = month.split('/')
            current_year = int(current_year)
            current_month = int(current_month)
            current_year += 1911
            current_month_dt = datetime(year=current_year, month=current_month, day=1)
            previous_month_dt = current_month_dt - timedelta(days=1)
            previous_year_minguo = previous_month_dt.year - 1911
            previous_month = f"{previous_year_minguo}/{previous_month_dt.month}"
        except ValueError:
            previous_month = None

        for item in top_10_data:
            stock_code = item['stock_code']
            if previous_month:
                last_month_data = db['revenue'].find_one({'stock_code': stock_code, 'month': previous_month}, {'revenue': 1})
                if last_month_data:
                    item['last_month_revenue'] = last_month_data['revenue']
                else:
                    item['last_month_revenue'] = None
            else:
                item['last_month_revenue'] = None

    else:
        top_10_data = []
        previous_month = None

    return render_template('revenue.html', data=top_10_data, months=months)

def get_top_10_pe_stocks():
    client = MongoClient('mongodb://localhost:27017/')
    db = client['test']
    
    # 查詢最新的日期
    latest_date = db['peratio'].find_one(sort=[("date", -1)])['date']
    
    # 在最新日期範圍內排序並取前 10 筆
    top_stocks = list(db['peratio'].find({"date": latest_date}).sort("pe_ratio", -1).limit(10))
    
    return top_stocks

@app.route('/peratio')
def peratio():
    top_stocks = get_top_10_pe_stocks()
    return render_template('peratio.html', stocks=top_stocks)

capitalization_col = db['capitalization']
eps_col = db['eps']
peratio_col = db['peratio']
revenue_col = db['revenue']
price_col = db['price']
chips_col = db['price']
user_col = db['user']
strategies_col = db['strategies']
yield_col = db['yield']

@app.route('/yield')
def yield_ranking():
    latest_data = yield_col.find_one(sort=[('date', -1)])
    if not latest_data:
        return "沒有數據"

    latest_date = latest_data['date']

    stocks = list(yield_col.find({'date': latest_date}))

    for stock in stocks:
        yield_str = stock.get('yield', '0%')
        try:
            yield_value = float(yield_str.strip('%'))
        except ValueError:
            yield_value = 0.0
        stock['yield_value'] = yield_value

    stocks.sort(key=lambda x: x['yield_value'], reverse=True)

    top_10_stocks = stocks[:10]

    return render_template('yield.html', stocks=top_10_stocks)

@app.route('/investors', methods=['GET'])
def investors_ranking():
    latest_data = price_col.find_one(sort=[('date', -1)])
    if not latest_data:
        return "沒有數據"

    latest_date = latest_data['date']

    stocks = list(price_col.find({'date': latest_date}, {
        '_id': 0,
        'code': 1,
        'name': 1,
        'date': 1,
        'dealer': 1,
        'foreign': 1,
        'investment': 1,
        'investors': 1
    }))

    for stock in stocks:
        investors_value = stock.get('investors', 0)
        if investors_value is None:
            investors_value = 0
        stock['investors_value'] = investors_value

    stocks.sort(key=lambda x: x['investors_value'], reverse=True)

    top_10_stocks = stocks[:10]

    return render_template('investors.html', stocks=top_10_stocks)

@app.route('/volume', methods=['GET'])
def volume_ranking():
    latest_data = price_col.find_one(sort=[('date', -1)])
    if not latest_data:
        return "沒有數據"

    latest_date = latest_data['date']

    stocks = list(price_col.find({'date': latest_date}, {
        '_id': 0,
        'code': 1,
        'name': 1,
        'date': 1,
        'volume': 1
    }))

    for stock in stocks:
        volume_value = stock.get('volume', 0)
        if volume_value is None:
            volume_value = 0
        stock['volume_value'] = volume_value

    stocks.sort(key=lambda x: x['volume_value'], reverse=True)

    top_10_stocks = stocks[:10]

    return render_template('volume.html', stocks=top_10_stocks)

def parse_date(date_str):
    try:
        return parser.parse(date_str)
    except ValueError:
        raise ValueError(f"無法解析的日期格式: {date_str}")

def parse_month(month_str):
    # month_str format: "113/8" (ROC year)
    roc_year, month = month_str.split('/')
    year = int(roc_year) + 1911  # Convert ROC year to Gregorian year
    month = int(month)
    return datetime(year, month, 1)

def parse_quarter(quarter_str):
    # quarter_str format: "2024/Q2"
    year, q = quarter_str.split('/Q')
    year = int(year)
    quarter = int(q)
    return (year, quarter)

@app.route('/stock_selection', methods=['GET', 'POST'])
def stock_selection():
    if request.method == 'POST':
        # 取得使用者輸入
        fundamental_condition = request.form.get('fundamental_condition')
        fundamental_value = request.form.get('fundamental_value')
        technical_condition = request.form.get('technical_condition')
        technical_value = request.form.get('technical_value')
        chip_condition = request.form.get('chip_condition')
        chip_value = request.form.get('chip_value')
        
        # 檢查至少選擇了一個條件
        if not fundamental_condition and not technical_condition and not chip_condition:
            flash('請至少選擇一個條件')
            return redirect(url_for('stock_selection'))
        
        # 初始化選定的股票代號集合
        selected_stock_codes = None  # 最終的股票代號集合
        fundamental_stock_codes = set()
        technical_stock_codes = set()
        chip_stock_codes = set()
        
        # 應用基本面條件
        if fundamental_condition:
            if fundamental_condition == '1':
                # 股本超過 "X" 億元
                if not fundamental_value:
                    flash('請輸入基本面條件的值')
                    return redirect(url_for('stock_selection'))
                try:
                    X = float(fundamental_value) * 1e8  # 轉換為元
                except ValueError:
                    flash('基本面條件的值必須是數字')
                    return redirect(url_for('stock_selection'))
                cursor = capitalization_col.find({'capitalization': {'$gt': X}}, {'stock_code': 1})
                fundamental_stock_codes = set(doc.get('stock_code') for doc in cursor if doc.get('stock_code'))
                
            elif fundamental_condition == '2':
                # 最近4季每股盈餘總和超過 "X" 元
                if not fundamental_value:
                    flash('請輸入基本面條件的值')
                    return redirect(url_for('stock_selection'))
                try:
                    X = float(fundamental_value)
                except ValueError:
                    flash('基本面條件的值必須是數字')
                    return redirect(url_for('stock_selection'))
                codes = eps_col.distinct('stock_code')
                for code in codes:
                    quarters = eps_col.find({'stock_code': code}).distinct('quarter')
                    quarters = sorted(quarters, key=parse_quarter, reverse=True)[:4]
                    cursor = eps_col.find({'stock_code': code, 'quarter': {'$in': quarters}})
                    total_eps = sum(float(doc.get('eps', 0)) for doc in cursor)
                    if total_eps > X:
                        fundamental_stock_codes.add(code)
                        
            elif fundamental_condition == '3':
                # 本益比高於 "X"
                if not fundamental_value:
                    flash('請輸入基本面條件的值')
                    return redirect(url_for('stock_selection'))
                try:
                    X = float(fundamental_value)
                except ValueError:
                    flash('基本面條件的值必須是數字')
                    return redirect(url_for('stock_selection'))
                dates = peratio_col.distinct('date')
                dates = sorted(dates, key=parse_date, reverse=True)
                if not dates:
                    flash('本益比資料不可用')
                    return redirect(url_for('stock_selection'))
                latest_date = dates[0]
                cursor = peratio_col.find({'date': latest_date, 'pe_ratio': {'$gt': X}})
                fundamental_stock_codes = set(doc.get('stock_code') for doc in cursor if doc.get('stock_code'))
                
            elif fundamental_condition == '4':
                # 最近一個月的營收較前一月成長超過 "X" %
                if not fundamental_value:
                    flash('請輸入基本面條件的值')
                    return redirect(url_for('stock_selection'))
                try:
                    X = float(fundamental_value)
                except ValueError:
                    flash('基本面條件的值必須是數字')
                    return redirect(url_for('stock_selection'))
                months = revenue_col.distinct('month')
                months = sorted(months, key=parse_month, reverse=True)
                if not months:
                    flash('營收資料不可用')
                    return redirect(url_for('stock_selection'))
                latest_month = months[0]
                cursor = revenue_col.find({'month': latest_month, 'growth_rate': {'$gt': X}})
                fundamental_stock_codes = set(doc.get('stock_code') for doc in cursor if doc.get('stock_code'))
                
            else:
                flash('無效的基本面條件')
                return redirect(url_for('stock_selection'))
            
            selected_stock_codes = fundamental_stock_codes
        
        # 應用技術面條件
        if technical_condition:
            # 確定要應用技術面條件的股票代號
            if selected_stock_codes is None:
                # 如果沒有基本面條件，取得所有股票代號
                all_stock_codes = set(price_col.distinct('code'))
                selected_stock_codes = all_stock_codes
            technical_stock_codes = set()
            if technical_condition == '1':
                # 5日MA由下向上突破10日MA
                for code in selected_stock_codes:
                    cursor = price_col.find({'code': code}).sort('date', -1).limit(2)
                    docs = list(cursor)
                    if len(docs) < 2:
                        continue
                    latest, previous = docs[0], docs[1]
                    if (latest.get('5dma') is not None and latest.get('10dma') is not None and
                        previous.get('5dma') is not None and previous.get('10dma') is not None and
                        latest.get('5dma') > latest.get('10dma') and
                        previous.get('5dma') < previous.get('10dma')):
                        technical_stock_codes.add(code)
                        
            elif technical_condition == '2':
                # DIF向上突破MACD
                for code in selected_stock_codes:
                    cursor = price_col.find({'code': code}).sort('date', -1).limit(2)
                    docs = list(cursor)
                    if len(docs) < 2:
                        continue
                    latest, previous = docs[0], docs[1]
                    if (latest.get('MACD') is not None and latest.get('Signal') is not None and
                        previous.get('MACD') is not None and previous.get('Signal') is not None and
                        latest.get('MACD') > latest.get('Signal') and
                        previous.get('MACD') < previous.get('Signal')):
                        technical_stock_codes.add(code)
                        
            elif technical_condition == '3':
                # RSI超過 "X"
                if not technical_value:
                    flash('請輸入技術面條件的值')
                    return redirect(url_for('stock_selection'))
                try:
                    X = float(technical_value)
                except ValueError:
                    flash('技術面條件的值必須是數字')
                    return redirect(url_for('stock_selection'))
                for code in selected_stock_codes:
                    cursor = price_col.find({'code': code}).sort('date', -1).limit(1)
                    docs = list(cursor)
                    if not docs:
                        continue
                    doc = docs[0]
                    if doc.get('RSI') is not None and doc.get('RSI') > X:
                        technical_stock_codes.add(code)
                        
            elif technical_condition == '4':
                # 9日KD黃金交叉且KD值小於20
                for code in selected_stock_codes:
                    cursor = price_col.find({'code': code}).sort('date', -1).limit(2)
                    docs = list(cursor)
                    if len(docs) < 2:
                        continue
                    latest, previous = docs[0], docs[1]
                    if (latest.get('K') is not None and latest.get('D') is not None and
                        previous.get('K') is not None and previous.get('D') is not None and
                        latest.get('K') > latest.get('D') and
                        previous.get('K') < previous.get('D') and
                        latest.get('K') < 20 and latest.get('D') < 20 and
                        previous.get('K') < 20 and previous.get('D') < 20):
                        technical_stock_codes.add(code)
            else:
                flash('無效的技術面條件')
                return redirect(url_for('stock_selection'))
            
            # 更新選定的股票代號集合
            if fundamental_condition:
                selected_stock_codes = selected_stock_codes.intersection(technical_stock_codes)
            else:
                selected_stock_codes = technical_stock_codes
        
        if chip_condition:
            # 確定要應用籌碼面條件的股票代號
            if selected_stock_codes is None:
                # 如果沒有基本面和技術面條件，取得所有股票代號
                all_stock_codes = set(chips_col.distinct('code'))
                selected_stock_codes = all_stock_codes
            chip_stock_codes = set()
    
            # 獲取最新的 5 個交易日日期
            dates = chips_col.distinct('date')
            dates = sorted(dates, key=parse_date, reverse=True)
            if len(dates) < 5:
                flash('籌碼面資料不足')
                return redirect(url_for('stock_selection'))
            latest_dates = dates[:5]
            
            if chip_condition == '1':
                # 外資最近 5 天內買超 4 天以上
                for code in selected_stock_codes:
                    cursor = chips_col.find({'code': code, 'date': {'$in': latest_dates}})
                    records = list(cursor)
                    if len(records) < 5:
                        continue  # 資料不足 5 天的股票跳過
                    buy_days = sum(1 for record in records if record.get('foreign', 0) > 0)
                    if buy_days >= 4:
                        chip_stock_codes.add(code)
            elif chip_condition == '2':
                # 投信最近 5 天內買超 4 天以上
                for code in selected_stock_codes:
                    cursor = chips_col.find({'code': code, 'date': {'$in': latest_dates}})
                    records = list(cursor)
                    if len(records) < 5:
                        continue
                    buy_days = sum(1 for record in records if record.get('investment', 0) > 0)
                    if buy_days >= 4:
                        chip_stock_codes.add(code)
            elif chip_condition == '3':
                # 自營商最近 5 天內買超 4 天以上
                for code in selected_stock_codes:
                    cursor = chips_col.find({'code': code, 'date': {'$in': latest_dates}})
                    records = list(cursor)
                    if len(records) < 5:
                        continue
                    buy_days = sum(1 for record in records if record.get('dealer', 0) > 0)
                    if buy_days >= 4:
                        chip_stock_codes.add(code)
            elif chip_condition == '4':
                # 三大法人最近 5 天內買超 4 天以上
                for code in selected_stock_codes:
                    cursor = chips_col.find({'code': code, 'date': {'$in': latest_dates}})
                    records = list(cursor)
                    if len(records) < 5:
                       continue
                    buy_days = sum(1 for record in records if record.get('investors', 0) > 0)
                    if buy_days >= 4:
                        chip_stock_codes.add(code)
            else:
                flash('無效的籌碼面條件')
                return redirect(url_for('stock_selection'))
    
            # 更新 selected_stock_codes
            if selected_stock_codes is None:
                selected_stock_codes = chip_stock_codes
            else:
                selected_stock_codes = selected_stock_codes.intersection(chip_stock_codes)
        
        # 獲取最終的股票資料
        result = []
        for code in selected_stock_codes:
            cursor = price_col.find({'code': code}).sort('date', -1).limit(1)
            docs = list(cursor)
            if not docs:
                continue
            doc = docs[0]
            data = {
                'code': doc.get('code'),
                'name': doc.get('name'),
                'date': doc.get('date'),
                'close': doc.get('close'),
                'price_change': doc.get('price_change'),
                'changed_percent': doc.get('changed_percent')
            }
            result.append(data)
        
        # 渲染結果頁面
        return render_template('stock_selection_result.html', stocks=result)
        
    else:
        # 渲染選股表單頁面
        return render_template('stock_selection.html')




@app.route('/add_to_followlist', methods=['POST'])
def add_to_followlist():
    if 'username' not in session:
        flash('請先註冊並登入')
        return redirect(url_for('index'))
    
    stock_code = request.form.get('stock_code')
    username = session['username']
    
    if stock_code:
        collection = db['user']
        
        # 檢查股票是否已在關注清單中
        user = collection.find_one({'username': username})
        follow_code = user.get('follow_code', [])
        
        # 檢查是否已關注該股票
        already_followed = False
        for item in follow_code:
            if (isinstance(item, dict) and item.get('code') == stock_code) or (item == stock_code):
                already_followed = True
                break
        
        if already_followed:
            flash('該股票已在您的關注清單中')
            return redirect(url_for('stock_search'))
        
        # 獲取最新的股票數據
        latest_stock_data = price_col.find_one({'code': stock_code}, sort=[('date', -1)])
        
        if not latest_stock_data:
            flash('無法獲取該股票的數據')
            return redirect(url_for('stock_search'))
        
        follow_date = latest_stock_data.get('date')
        follow_price = latest_stock_data.get('close', 0)
        
        # 保存使用者添加的日期（可選）
        added_date = datetime.now().strftime('%Y-%m-%d')
        
        # 構建新的關注項目
        new_follow_item = {
            'code': stock_code,
            'group': 'nogroup',
            'follow_date': added_date ,
            'follow_price': follow_price
        }
        
        follow_code.append(new_follow_item)
        
        # 更新資料庫
        collection.update_one(
            {'username': username},
            {'$set': {'follow_code': follow_code}},
            upsert=True
        )
        
        flash(f'已成功將 {stock_code} 加入關注清單! (關注日期：{follow_date}，收盤價：{follow_price})')
        return redirect(request.referrer or url_for('followlist'))
    else:
        flash("股票代號無效")
        return redirect(request.referrer or url_for('followlist'))
    

@app.route('/followlist', methods=['GET'])
def followlist():
    if 'username' not in session:
        flash('請先登入')
        return redirect(url_for('login', next=request.url))
    
    username = session['username']
    user = db['user'].find_one({'username': username})
    
    if not user:
        flash('使用者不存在')
        return redirect(url_for('login'))
    
    follow_code = user.get('follow_code', [])
    
    # 從資料庫中取得股票資訊
    stocks = []
    for item in follow_code:
        if isinstance(item, dict):
            code = item['code']
            group = item.get('group', 'nogroup')
            follow_date = item.get('follow_date')
            follow_price = item.get('follow_price')
        else:
            # 如果 item 是字串，視為股票代碼，群組設為 'nogroup'
            code = item
            group = 'nogroup'
            follow_date = None
            follow_price = None
        
        # 獲取最新的收盤價
        latest_stock_data = price_col.find_one({'code': code}, sort=[('date', -1)])
        if not latest_stock_data:
            continue  # 如果沒有最新數據，跳過該股票
        latest_date = latest_stock_data.get('date')
        latest_close = latest_stock_data.get('close', 0)
        
        # 如果沒有 follow_date 和 follow_price，設置為最新日期和價格
        if not follow_date:
            follow_date = latest_date
        if not follow_price:
            follow_price = latest_close
        
        # 計算價差和漲跌百分比
        price_diff = latest_close - follow_price
        if follow_price != 0:
            percent_change = (price_diff / follow_price) * 100
        else:
            percent_change = 0
        
        stocks.append({
            'name': latest_stock_data.get('name'),
            'code': code,
            'latest_date': latest_date,
            'latest_close': latest_close,
            'follow_date': follow_date,
            'follow_price': follow_price,
            'price_diff': round(price_diff, 2),
            'percent_change': round(percent_change, 2),
            'group': group
        })
    
    return render_template('followlist.html', stocks=stocks)


@app.route('/batch_update_followlist', methods=['POST'])
def batch_update_followlist():
    if 'username' not in session:
        return jsonify({'error': '未登入'}), 401

    data = request.get_json()
    updates = data.get('updates', [])
    username = session['username']

    user = db['user'].find_one({'username': username})
    if not user:
        return jsonify({'error': '使用者不存在'}), 404

    follow_code = user.get('follow_code', [])

    # 將 follow_code 轉換為以股票代碼為鍵的字典，方便操作
    code_dict = {}
    for item in follow_code:
        if isinstance(item, dict):
            code_dict[item['code']] = item
        else:
            # 如果 item 是字串，轉換為字典結構
            code_dict[item] = {
                'code': item,
                'group': 'nogroup',
                'follow_date': None,
                'follow_price': None
            }

    for update in updates:
        code = update.get('code')
        action = update.get('action')
        if not code or not action:
            continue
        if action in ['group1', 'group2', 'group3']:
            # 更新股票的群組
            if code in code_dict:
                code_dict[code]['group'] = action
            else:
                # 如果股票不在關注清單中，則添加，並需要獲取 follow_date 和 follow_price
                # 這種情況應該不會發生，除非前端傳遞了未關注的股票
                # 您可以選擇忽略或處理這種情況
                pass
        elif action == 'unfollow':
            # 取消關注
            if code in code_dict:
                del code_dict[code]
        else:
            return jsonify({'error': f'無效的操作：{action}'}), 400

    # 將字典轉回列表並更新資料庫
    new_follow_code = list(code_dict.values())
    db['user'].update_one({'username': username}, {'$set': {'follow_code': new_follow_code}})

    return jsonify({'success': True})

@app.route('/entry_judgement', methods=['GET', 'POST'])
def entry_judgement():
    if 'username' not in session:
        flash('請先登入')
        return redirect(url_for('login'))

    if request.method == 'POST':
        strategy = request.form.get('strategy')
        username = session['username']
        user = db['user'].find_one({'username': username})

        if not user:
            flash('使用者不存在')
            return redirect(url_for('login'))

        follow_code = user.get('follow_code', [])
        stock_codes = [item['code'] if isinstance(item, dict) else item for item in follow_code]

        # 根據策略進行判斷
        if strategy == 'strategy1':
            selected_stocks = apply_strategy1(stock_codes)
        elif strategy == 'strategy2':
            selected_stocks = apply_strategy2(stock_codes)
        elif strategy == 'strategy3':
            selected_stocks = apply_strategy3(stock_codes)
        else:
            flash('請選擇一個策略')
            return redirect(url_for('entry_judgement'))

        # 定義條件名稱的映射字典
        condition_names = {
            'strategy1': {
                'ma60_uptrend': '60 日均線持續向上',
                'ma5_cross_ma10': '5 日均線上穿 10 日均線',
                'volume_zscore_gt_2': '成交量 Z 分數大於 2'
            },
            'strategy2': {
                'MACD_cross_Signal': 'MACD 線上穿訊號線',
                'K_lt_30_and_K_cross_D': 'KD 小於 30 且 K 上穿 D',
                'RSI_break_25': 'RSI 突破 25'
            },
            'strategy3': {
                'MACD_gt_Signal_continuous': 'MACD 持續大於訊號線',
                'K_gt_70_and_K_gt_D': 'KD 大於 70 且 K 持續大於 D',
                'RSI_gt_75': 'RSI 大於 75'
            }
        }

        # 獲取股票詳細資訊，傳遞給模板
        stocks = []
        for stock in selected_stocks:
            code = stock['code']
            conditions_met = stock['conditions_met']
            stock_data = price_col.find_one({'code': code}, sort=[('date', -1)])
            if stock_data:
                stocks.append({
                    'code': code,
                    'name': stock_data.get('name'),
                    'date': stock_data.get('date'),
                    'close': stock_data.get('close'),
                    'conditions_met': conditions_met
                })

        return render_template(
            'entry_judgement.html',
            stocks=stocks,
            strategy=strategy,
            condition_names=condition_names[strategy]
        )
    else:
        return render_template('entry_judgement.html')

def apply_strategy1(stock_codes):
    selected_stocks = []
    for code in stock_codes:
        # 獲取最近 60 天的數據
        cursor = price_col.find({'code': code}).sort('date', -1).limit(60)
        data = list(cursor)

        if len(data) < 60:
            continue

        # 準備子條件滿足情況的字典
        conditions_met = {
            'ma60_uptrend': False,
            'ma5_cross_ma10': False,
            'volume_zscore_gt_2': False
        }

        # 檢查 60 日均線是否持續向上
        ma60_values = [doc.get('60dma') for doc in data if '60dma' in doc and doc.get('60dma') is not None]
        if len(ma60_values) < 2:
            continue

        if ma60_values[0] > ma60_values[1]:
            conditions_met['ma60_uptrend'] = True

        # 檢查 5 日均線上穿 10 日均線
        latest = data[0]
        previous = data[1]

        if all(key in latest and key in previous for key in ('5dma', '10dma')):
            if latest['5dma'] > latest['10dma'] and previous['5dma'] <= previous['10dma']:
                conditions_met['ma5_cross_ma10'] = True

        # 計算成交量的 Z 分數
        volume_values = [doc.get('volume') for doc in data if 'volume' in doc and doc.get('volume') is not None]
        if len(volume_values) >= 20:
            recent_volumes = volume_values[:20]  # 最近 20 天的成交量
            mean_volume = sum(recent_volumes) / len(recent_volumes)
            std_volume = (sum((v - mean_volume) ** 2 for v in recent_volumes) / len(recent_volumes)) ** 0.5
            if std_volume > 0:
                z_score = (latest['volume'] - mean_volume) / std_volume
                if z_score > 2:
                    conditions_met['volume_zscore_gt_2'] = True

        # 如果至少有一個子條件滿足，將股票添加到結果列表，並記錄滿足情況
        selected_stocks.append({
            'code': code,
            'conditions_met': conditions_met
        })

    return selected_stocks

def apply_strategy2(stock_codes):
    selected_stocks = []
    for code in stock_codes:
        # 獲取最近 2 天的數據
        cursor = price_col.find({'code': code}).sort('date', -1).limit(2)
        data = list(cursor)

        if len(data) < 2:
            continue

        latest = data[0]
        previous = data[1]

        conditions_met = {
            'MACD_cross_Signal': False,
            'K_lt_30_and_K_cross_D': False,
            'RSI_break_25': False
        }

        # 檢查 MACD 線上穿訊號線
        if all(key in latest and key in previous for key in ('MACD', 'Signal')):
            if latest['MACD'] > latest['Signal'] and previous['MACD'] <= previous['Signal']:
                conditions_met['MACD_cross_Signal'] = True

        # 檢查 KD 指標
        if 'K' in latest and 'D' in latest:
            if latest['K'] < 30 and latest['K'] > latest['D']:
                conditions_met['K_lt_30_and_K_cross_D'] = True

        # 檢查 RSI 指標
        if 'RSI' in latest and 'RSI' in previous:
            if latest['RSI'] > 25 and previous['RSI'] <= 25:
                conditions_met['RSI_break_25'] = True

        selected_stocks.append({
            'code': code,
            'conditions_met': conditions_met
        })


    return selected_stocks

def apply_strategy3(stock_codes):
    selected_stocks = []
    for code in stock_codes:
        # 獲取最近 2 天的數據
        cursor = price_col.find({'code': code}).sort('date', -1).limit(2)
        data = list(cursor)

        if len(data) < 2:
            continue

        latest = data[0]
        previous = data[1]

        conditions_met = {
            'MACD_gt_Signal_continuous': False,
            'K_gt_70_and_K_gt_D': False,
            'RSI_gt_75': False
        }

        # 檢查 MACD 是否持續大於訊號線
        if all(key in latest and key in previous for key in ('MACD', 'Signal')):
            if latest['MACD'] > latest['Signal'] and previous['MACD'] > previous['Signal']:
                conditions_met['MACD_gt_Signal_continuous'] = True

        # 檢查 KD 指標
        if 'K' in latest and 'D' in latest and 'K' in previous and 'D' in previous:
            if latest['K'] > 70 and latest['K'] > latest['D'] and previous['K'] > previous['D']:
                conditions_met['K_gt_70_and_K_gt_D'] = True

        # 檢查 RSI 指標
        if 'RSI' in latest:
            if latest['RSI'] > 75:
                conditions_met['RSI_gt_75'] = True

        selected_stocks.append({
            'code': code,
            'conditions_met': conditions_met
        })

    return selected_stocks

@app.route('/buy_stock', methods=['GET', 'POST'])
def buy_stock():
    if 'username' not in session:
        flash('請先登入')
        return redirect(url_for('login'))

    username = session['username']

    if request.method == 'POST':
        stock_code = request.form.get('stock_code').strip()
        buy_price = request.form.get('buy_price').strip()
        exit_strategy = request.form.get('exit_strategy')

        if not stock_code or not buy_price or not exit_strategy:
            flash('請輸入有效的股票代號、買入價格和出場策略')
            return redirect(url_for('buy_stock'))

        try:
            buy_price = float(buy_price)
        except ValueError:
            flash('買入價格必須是數字')
            return redirect(url_for('buy_stock'))

        latest_data = price_col.find_one({'code': stock_code}, sort=[('date', -1)])

        if not latest_data:
            flash('找不到該股票的數據')
            return redirect(url_for('buy_stock'))

        buy_date = datetime.now().strftime('%Y-%m-%d')

        result = user_col.update_one(
            {'username': username, 'purchase_records.stock_code': stock_code},
            {'$set': {
                'purchase_records.$.buy_price': buy_price,
                'purchase_records.$.buy_date': buy_date,
                'purchase_records.$.exit_strategy': exit_strategy
            }}
        )

        if result.matched_count == 0:
            user_col.update_one(
                {'username': username},
                {'$push': {
                    'purchase_records': {
                        'stock_code': stock_code,
                        'buy_date': buy_date,
                        'buy_price': buy_price,
                        'exit_strategy': exit_strategy
                    }
                }}
            )

        flash('買入紀錄已儲存')

    user = user_col.find_one({'username': username})
    purchase_records = user.get('purchase_records', [])
    
    records = []
    for record in purchase_records:
        stock_code = record['stock_code']
        buy_price = float(record['buy_price'])
        buy_date_str = record['buy_date']
        exit_strategy = record.get('exit_strategy', 'strategy1')
        buy_date = datetime.strptime(buy_date_str, '%Y-%m-%d')  # 將買入日期轉換為 datetime 對象

        # 獲取該股票的最新價格資料
        latest_price_data = price_col.find_one(
            {'code': stock_code},
            sort=[('date', -1)]  # 按日期降序排序，取得最新日期
        )

        if latest_price_data:
            latest_date_str = latest_price_data['date']
            latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d')  # 將最新日期轉換為 datetime 對象
        else:
            latest_date = None

        if latest_date and latest_date >= buy_date:
            # 最新日期不早於買入日期，按原邏輯處理
            price_data = list(price_col.find(
                {'code': stock_code, 'date': {'$gte': buy_date_str, '$lte': latest_date_str}},
                sort=[('date', 1)]  # 按日期升序排序
            ))
        elif latest_date:
            # 最新日期早於買入日期，使用最新的價格資料進行計算
            price_data = [latest_price_data]
            # 將價格資料按照日期升序排序
            price_data.sort(key=lambda x: x['date'])
        else:
            # 沒有任何價格資料
            price_data = []

        # 除錯輸出
        print(f"股票代號：{stock_code}，買入日期：{buy_date_str}，最新日期：{latest_price_data['date'] if latest_price_data else '無'}")
        print(f"查詢到的價格資料數量：{len(price_data)}")
        
        if price_data:
            print(f"第一筆價格資料日期：{price_data[0]['date']}")
            print(f"最後一筆價格資料日期：{price_data[-1]['date']}")
        else:
            print("未查詢到任何價格資料")

        if price_data:
            latest_data = price_data[-1]
            current_price = float(latest_data.get('close', 0))
            price_difference = round(current_price - buy_price, 2)
            if buy_price != 0:
                yield_rate = round((current_price - buy_price) / buy_price * 100, 2)
            else:
                yield_rate = 0.0
            current_date = latest_data.get('date')

            if exit_strategy == 'strategy1':
                data_highest_price = max(float(item.get('high', 0)) for item in price_data)
                highest_price = max(buy_price, data_highest_price)

                if highest_price != 0:
                    drop_percent = (highest_price - current_price) / highest_price * 100
                    exit_signal = drop_percent >= 10
                else:
                    exit_signal = False

            elif exit_strategy == 'strategy2':
                extended_price_data = list(price_col.find(
                    {'code': stock_code, 'date': {'$lte': latest_date_str}},
                    sort=[('date', 1)]
                ))
                close_prices = [float(item.get('close', 0)) for item in extended_price_data]

                if len(close_prices) >= 20:
                    ma5 = sum(close_prices[-5:]) / 5
                    ma20 = sum(close_prices[-20:]) / 20
                    exit_signal = ma5 < ma20
                else:
                    exit_signal = False

            else:
                exit_signal = False

            print(f"股票代號：{stock_code}")
            print(f"出場策略：{exit_strategy}")
            print(f"當前價格：{current_price}")
            if exit_strategy == 'strategy1':
                print(f"持有期間最高價（包含買入價格）：{highest_price}")
                print(f"下跌幅度：{drop_percent}%")
            elif exit_strategy == 'strategy2':
                print(f"5 日均線：{ma5}")
                print(f"20 日均線：{ma20}")
                print(f"5 日均線是否跌破 20 日均線：{exit_signal}")
            print(f"是否滿足出場條件（exit_signal）：{exit_signal}")

        else:
            current_price = None
            price_difference = None
            yield_rate = None
            current_date = None
            exit_signal = False

        records.append({
            'stock_code': stock_code,
            'buy_date': buy_date_str,
            'buy_price': buy_price,
            'current_date': current_date,
            'current_price': current_price,
            'price_difference': price_difference,
            'yield_rate': yield_rate,
            'exit_strategy': exit_strategy,
            'exit_signal': exit_signal
        })

    return render_template('stock_buy.html', records=records)

@app.route('/sell_stock', methods=['POST'])
def sell_stock():
    if 'username' not in session:
        flash('請先登入')
        return redirect(url_for('login'))

    username = session['username']
    stock_code = request.form.get('stock_code')

    if not stock_code:
        flash('無效的股票代號')
        return redirect(url_for('buy_stock'))

    # 從使用者的買入紀錄中刪除該股票
    user_col.update_one(
        {'username': username},
        {'$pull': {
            'purchase_records': {'stock_code': stock_code}
        }}
    )

    flash(f'已賣出股票 {stock_code}')
    return redirect(url_for('buy_stock'))

@app.route('/check_exit_signals', methods=['GET'])
def check_exit_signals():
    if 'username' not in session:
        return jsonify({'error': '請先登入'}), 401

    username = session['username']
    strategy = request.args.get('strategy', 'strategy1')
    
    # 獲取使用者的買入紀錄
    user = user_col.find_one({'username': username})
    if not user:
        return jsonify({'error': '使用者不存在'}), 404

    purchase_records = user.get('purchase_records', [])
    records = []

    for record in purchase_records:
        stock_code = record['stock_code']
        buy_price = float(record['buy_price'])
        buy_date_str = record['buy_date']
        buy_date = datetime.strptime(buy_date_str, '%Y-%m-%d')
        
        # 獲取該股票的最新價格資料
        latest_price_data = price_col.find_one(
            {'code': stock_code},
            sort=[('date', -1)]  # 按日期降序排序，取得最新日期的資料
        )

        if latest_price_data:
            latest_date_str = latest_price_data['date']
            latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d')

            # 從買入日期到最新日期的價格資料
            price_data = list(price_col.find(
                {'code': stock_code, 'date': {'$gte': buy_date_str, '$lte': latest_date_str}},
                sort=[('date', 1)]
            ))

            if price_data:
                latest_data = price_data[-1]
                current_price = float(latest_data.get('close', 0))
                price_difference = round(current_price - buy_price, 2)
                yield_rate = round((current_price - buy_price) / buy_price * 100, 2) if buy_price else 0.0
                current_date = latest_data.get('date')

                if strategy == 'strategy1':
                    data_highest_price = max(float(item.get('high', 0)) for item in price_data)
                    highest_price = max(buy_price, data_highest_price)
                    drop_percent = (highest_price - current_price) / highest_price * 100
                    exit_signal = drop_percent >= 10

                elif strategy == 'strategy2':
                    # 檢查在持有期間內，是否存在 5dma < 20dma 的情況
                    exit_signal = False
                    for item in price_data:
                        dma5 = item.get('5dma')
                        dma20 = item.get('20dma')

                        # 確保 dma5 和 dma20 都有值
                        if dma5 is None or dma20 is None:
                            continue

                        dma5 = float(dma5)
                        dma20 = float(dma20)
                        if dma5 < dma20:
                            exit_signal = True
                            break  # 一旦找到符合條件的日期，直接跳出循環

                    # 除錯輸出
                    print(f"股票代號：{stock_code}")
                    print(f"出場策略：{strategy}")
                    print(f"當前價格：{current_price}")
                    print(f"是否存在 5dma < 20dma 的情況：{exit_signal}")

                else:
                    exit_signal = False
            else:
                # 沒有價格資料
                current_price = price_difference = yield_rate = current_date = None
                exit_signal = False
        else:
            # 沒有任何價格資料
            current_price = price_difference = yield_rate = current_date = None
            exit_signal = False
            latest_date_str = None  # 無法取得最新日期

        records.append({
            'stock_code': stock_code,
            'buy_date': buy_date_str,
            'buy_price': buy_price,
            'current_date': current_date,
            'current_price': current_price,
            'price_difference': price_difference,
            'yield_rate': yield_rate,
            'exit_signal': exit_signal
        })

    return jsonify({'records': records})

@app.route('/set_investor_type', methods=['POST'])
def set_investor_type():
    if 'username' not in session:
        flash('請先登入')
        return redirect(url_for('login'))

    username = session['username']
    investor_type = request.form.get('investor_type')

    if not investor_type:
        flash('請選擇投資者類型')
        return redirect(request.referrer or url_for('index'))

    # 更新使用者的投資者類型
    user_col.update_one(
        {'username': username},
        {'$set': {'investor_type': investor_type}}
    )

    flash('您的投資者類型已更新為：{}'.format(investor_type))
    return redirect(request.referrer or url_for('index'))

@app.route('/api/data', methods=['GET'])
def code_search():
    stock_code = request.args.get('stock_code')
    if not stock_code:
        return jsonify({'error': '請提供股票代號'}), 400

    # 獲取最近10日的股票數據
    today = datetime.now()
    ten_days_ago = today - timedelta(days=100)  # 考慮到週末和假日，查詢最近30天的數據

    # 查詢價格數據
    price_data = list(price_col.find(
        {'code': stock_code, 'date': {'$gte': ten_days_ago.strftime('%Y-%m-%d')}},
        sort=[('date', 1)]  # 按日期升序排序
    ))

    if not price_data:
        return jsonify({'error': '找不到該股票的數據'}), 404

    # 構造返回的數據
    data = []
    for item in price_data[-100:]:  # 取最近10天的數據
        data.append({
            'date': item.get('date'),
            'open': float(item.get('open', 0)),
            'high': float(item.get('high', 0)),
            'low': float(item.get('low', 0)),
            'close': float(item.get('close', 0)),
            'volume': float(item.get('volume', 0)),
            '5ma': float(item.get('5dma', 0)),
            '10ma': float(item.get('10dma', 0)),
            '20ma': float(item.get('20dma', 0)),
            '60ma': float(item.get('60dma', 0)),
            'code': item.get('code'),
            'name': item.get('name')
        })
        
    pe_ratio_data = peratio_col.find_one({'stock_code': stock_code}, sort=[('date', -1)])
    pe_ratio = float(pe_ratio_data.get('pe_ratio')) if pe_ratio_data else None

    # 2. EPS
    eps_data = eps_col.find_one({'stock_code': stock_code}, sort=[('quarter', -1)])
    eps = float(eps_data.get('eps')) if eps_data else None

    # 3. 股本
    capital_data = capitalization_col.find_one({'stock_code': stock_code})
    capital = float(capital_data.get('capitalization')) if capital_data else None

    # 4. 月營收
    revenue_data = revenue_col.find_one({'stock_code': stock_code}, sort=[('month', -1)])
    monthly_revenue = float(revenue_data.get('revenue')) if revenue_data else None
    
    latest_data = price_data[-1]
    dealer = float(latest_data.get('dealer', 0))
    foreign = float(latest_data.get('foreign', 0))
    investment = float(latest_data.get('investment', 0))
    investors = float(latest_data.get('investors', 0))

    # 構造股票資訊
    stock_info = {
        'code': stock_code,
        'name': latest_data.get('name', ''),
        'pe_ratio': pe_ratio,
        'eps': eps,
        'capital': capital,
        'monthly_revenue': monthly_revenue,
        'dealer': dealer,
        'foreign': foreign,
        'investment': investment,
        'investors': investors,
    }


    return jsonify({'stock_info': stock_info, 'price_data': data})

def get_user_recommended_strategy(username, page):
    user = user_col.find_one({'username': username})
    if not user:
        return None, '無此用戶'

    investor_type = user.get('investor_type', '無')

    strategy_data = strategies_col.find_one({'investor_type': investor_type, 'page': page})
    if not strategy_data:
        return None, '未找到策略'

    recommended_strategy = strategy_data.get('strategy_content', '發生錯誤')

    return recommended_strategy, investor_type

from flask import Flask, request, jsonify, session

@app.route('/api/get_recommended_strategy', methods=['GET'])
def api_get_recommended_strategy():
    if 'username' not in session:
        return jsonify({'error': '請先登入'}), 401

    username = session['username']
    page = request.args.get('page')
    if not page:
        return jsonify({'error': '前端未傳回page參數'}), 400

    recommended_strategy, investor_type = get_user_recommended_strategy(username, page)
    if recommended_strategy is None:
        return jsonify({'error': investor_type}), 404

    return jsonify({
        'investor_type': investor_type,
        'recommended_strategy': recommended_strategy
    })

if __name__ == '__main__':
    app.run(debug=True)
