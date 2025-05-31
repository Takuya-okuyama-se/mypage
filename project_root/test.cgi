#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import pymysql
from pymysql.cursors import DictCursor

print("Content-Type: text/html\n")
print("<html><body>")
print("<h1>CGIテスト</h1>")

# 環境変数表示
print("<h2>環境変数</h2>")
print("<ul>")
for key in sorted(os.environ.keys()):
    print(f"<li><strong>{key}</strong>: {os.environ[key]}</li>")
print("</ul>")

# データベース接続テスト
try:
    print("<h2>データベース接続テスト</h2>")
    
    # 設定をインポート
    try:
        from config import Config
    except ImportError:
        # config.pyがない場合の環境変数からの直接読み込み
        class Config:
            MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
            MYSQL_USER = os.getenv('MYSQL_USER', 'root')
            MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
            MYSQL_DB = os.getenv('MYSQL_DB', 'test')
            MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    
    # 接続情報を設定から取得
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        port=Config.MYSQL_PORT,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=10
    )
    
    print("<p style='color:green;'>データベース接続成功！</p>")
    
    # 現在時刻を取得
    with conn.cursor() as cur:
        cur.execute("SELECT NOW() as time")
        result = cur.fetchone()
        print(f"<p>サーバー時刻: {result['time']}</p>")
    
    # ユーザー一覧を表示
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, email, role FROM users LIMIT 10")
        users = cur.fetchall()
        
        print("<h3>ユーザー一覧</h3>")
        print("<table border='1'>")
        print("<tr><th>ID</th><th>名前</th><th>メール</th><th>権限</th></tr>")
        
        for user in users:
            print("<tr>")
            print(f"<td>{user['id']}</td>")
            print(f"<td>{user['name']}</td>")
            print(f"<td>{user['email']}</td>")
            print(f"<td>{user['role']}</td>")
            print("</tr>")
        
        print("</table>")
    
    conn.close()
    
except Exception as e:
    print(f"<p style='color:red;'>データベース接続エラー: {e}</p>")

print("<hr/>")
print("<p><a href='/myapp/index.cgi/login'>ログインページへ</a></p>")
print("</body></html>")