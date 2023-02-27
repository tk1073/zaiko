from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import datetime
import os
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from flask import make_response, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = os.urandom(24)
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True)
    password = db.Column(db.String(12))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User(username=username, password=generate_password_hash(password, method='sha256'))
        
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    else:
        return render_template('signup.html')

from werkzeug.security import check_password_hash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect('/inventory')
        else:
            return "Invalid username or password"
    else:
        return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')



@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/inventory', methods=['POST'])
@login_required
def add_inventory():
    if request.method == 'POST':
        
    # 入力フォームから商品名と入荷数を取得
        product_name = request.form['name']
        number = int(request.form['number'])
        date = request.form['date']

    # データベースに接続
        conn = sqlite3.connect('zaiko.db')
        c = conn.cursor()

    # 商品名に紐付けられた情報をproductsテーブルから取得
        c.execute("SELECT * FROM products WHERE product_name=?", (product_name, ))
        result = c.fetchone()

    # inventoryテーブルに新しいレコードを挿入
        c.execute("INSERT INTO inventory (date, store, kind, name, number, quantity, price, total) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (date, result[1], result[2], result[3], number, result[4], result[5], number * result[5]))

    # 変更を保存してデータベースを閉じる
        conn.commit()
        conn.close()

        return redirect('inventory')
    else:
        return render_template('index')

    
@app.route('/new_index')
@login_required
def new_index():
    return render_template('new_index.html')    
    
    
@app.route('/new_inventory', methods=['POST'])
@login_required
def new_inventory():
    if request.method == 'POST':
        
    # 入力フォームから商品名と入荷数を取得
        product_name = request.form['name']
        number = int(request.form['number'])

    # データベースに接続
        conn = sqlite3.connect('zaiko.db')
        c = conn.cursor()

    # 商品名に紐付けられた情報をproductsテーブルから取得
        c.execute("SELECT * FROM products WHERE product_name=?", (product_name, ))
        result = c.fetchone()

    # inventoryテーブルに新しいレコードを挿入
        c.execute("INSERT INTO inventory (store, kind, name, number, quantity, price, total) VALUES (?, ?, ?, ?, ?, ?, ?)", (result[1], result[2], result[3], number, result[4], result[5], number * result[5]))

    # 変更を保存してデータベースを閉じる
        conn.commit()
        conn.close()

        return redirect('inventory')
    else:
        return render_template('new_index')    

@app.route('/inventory')
@login_required
def inventory():
    conn = sqlite3.connect('zaiko.db')
    c = conn.cursor()
    c.execute("SELECT * FROM inventory")
    data = c.fetchall()
    conn.close()
    return render_template('inventory.html', data=data)  




from flask import request

import datetime

import datetime

@app.route('/export_inventory')
@login_required
def export_inventory():
    # 日付の範囲を取得
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    if start_date and end_date:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        date_filter = f"date BETWEEN '{start_date}' AND '{end_date}'"
    else:
        date_filter = ''

    # データベースからデータを取得
    conn = sqlite3.connect('zaiko.db')
    query = f"SELECT * FROM inventory WHERE {date_filter}"
    df = pd.read_sql_query(query, conn)
    conn.close()

    # データをエクセル形式に変換
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='inventory', index=False)
    writer.save()
    output.seek(0)

    # ダウンロードするファイル名を指定
    filename = 'inventory.xlsx'

    # ダウンロードするファイルを作成
    response = make_response(output.read())
    response.headers.set('Content-Disposition', 'attachment', filename=filename)
    response.headers.set('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    return response


@app.route('/delete_range', methods=['POST'])
@login_required
def delete_range():
    start_id = int(request.form['start_id'])
    end_id = int(request.form['end_id'])
    
    conn = sqlite3.connect('zaiko.db')
    c = conn.cursor()
    c.execute('DELETE FROM inventory WHERE id BETWEEN ? AND ?', (start_id, end_id))
    conn.commit()
    conn.close()
    return redirect(url_for('inventory'))

@app.route('/delete_product', methods=['POST'])
@login_required
def delete_product():
    start_id = int(request.form['start_id'])
    end_id = int(request.form['end_id'])
    
    conn = sqlite3.connect('zaiko.db')
    c = conn.cursor()
    c.execute('DELETE FROM products WHERE id BETWEEN ? AND ?', (start_id, end_id))
    conn.commit()
    conn.close()
    return redirect(url_for('new_product'))






@app.route('/register')
@login_required
def register():
    return render_template('register.html')

@app.route('/new_register')
@login_required
def new_register():
    return render_template('new_register.html')

@app.route('/new_product', methods=['POST'])
@login_required
def add_product():
    if request.method == 'POST':
    # POSTされたデータを取得する
        store = request.form['store']
        kind = request.form['kind']
        product_name = request.form['product_name']
        quantity = request.form['quantity']
        price = request.form['price']

    # SQLite3に接続する
        conn = sqlite3.connect('zaiko.db')
        c = conn.cursor()

    # productsテーブルにデータを挿入する
        c.execute('INSERT INTO products (store, kind, product_name, quantity, price) VALUES (?, ?, ?, ?, ?)',(store, kind, product_name, quantity, price))
        conn.commit()
        conn.close()
        
        return redirect('new_product')
    else:
        return render_template('register')


@app.route('/new_product')
@login_required
def new_product():
    # SQLite3に接続する
    conn = sqlite3.connect('zaiko.db')
    c = conn.cursor()

    # productsテーブルのデータを取得する
    c.execute('SELECT * FROM products')
    products = c.fetchall()

    # テンプレートをレンダリングする
    return render_template('new_product.html', products=products)

@app.route('/search_product', methods=['GET', 'POST'])
def search_product():
    if request.method == 'GET':
        return render_template('new_product.html')
    elif request.method == 'POST':
        search_keyword = request.form['search_keyword']
        conn = sqlite3.connect('zaiko.db')
        c = conn.cursor()
        c.execute('SELECT * FROM products WHERE store LIKE ? OR product_name LIKE ? OR kind LIKE ?', ('%'+search_keyword+'%', '%'+search_keyword+'%', '%'+search_keyword+'%'))
        results = c.fetchall()
        conn.close()
        return render_template('new_product.html', results=results)
    
    

if __name__ == '__main__':
    app.run(debug=True)
