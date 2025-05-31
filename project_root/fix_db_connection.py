#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
データベース接続の緊急修正
"""

import os
import sys

# 設定の確認と修正
print("Content-Type: text/plain; charset=utf-8")
print()

print("=== Environment Check ===")
print(f"Current directory: {os.getcwd()}")
print(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")

print("\n=== Environment Variables ===")
print(f"MYSQL_HOST: {os.getenv('MYSQL_HOST', 'NOT SET')}")
print(f"MYSQL_USER: {os.getenv('MYSQL_USER', 'NOT SET')}")
print(f"MYSQL_DB: {os.getenv('MYSQL_DB', 'NOT SET')}")

print("\n=== .env File Check ===")
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    print(f".env file exists at: {env_path}")
    with open(env_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if 'MYSQL' in line and 'PASSWORD' not in line:
                print(f"  {line.strip()}")
else:
    print(".env file NOT FOUND")

print("\n=== Config Import Test ===")
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import Config
    print("Config imported successfully")
    print(f"Config.MYSQL_HOST: {Config.MYSQL_HOST}")
    print(f"Config.MYSQL_USER: {Config.MYSQL_USER}")
    print(f"Config.MYSQL_DB: {Config.MYSQL_DB}")
except Exception as e:
    print(f"Failed to import config: {e}")

print("\n=== Direct Connection Test ===")
try:
    import pymysql
    # 直接接続情報を指定してテスト
    conn = pymysql.connect(
        host='mysql3103.db.sakura.ne.jp',
        user='seishinn',
        password='Yakyuubu8',
        database='seishinn_test',
        port=3306,
        charset='utf8mb4'
    )
    print("Direct connection successful!")
    conn.close()
except Exception as e:
    print(f"Direct connection failed: {e}")

print("\n=== Recommendations ===")
print("1. Ensure .env file exists in the project root")
print("2. Check if environment variables are being loaded")
print("3. Verify Python path includes the project directory")
print("4. Make sure config.py is accessible")