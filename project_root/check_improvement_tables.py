#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import os
import pymysql
from pymysql.cursors import DictCursor

# 設定をインポート
try:
    from config import Config
except ImportError:
    class Config:
        MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
        MYSQL_USER = os.getenv('MYSQL_USER', 'root')
        MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
        MYSQL_DB = os.getenv('MYSQL_DB', 'test')
        MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))

def check_tables():
    """データベーステーブルの存在を確認"""
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        port=Config.MYSQL_PORT,
        charset='utf8mb4',
        cursorclass=DictCursor
    )
    
    try:
        with conn.cursor() as cur:
            # テーブル一覧を取得
            print("=== 全テーブル一覧 ===")
            cur.execute("SHOW TABLES")
            tables = cur.fetchall()
            for table in tables:
                table_name = list(table.values())[0]
                print(f"- {table_name}")
            
            # 成績関連テーブルの詳細を確認
            print("\n=== 成績関連テーブルの構造 ===")
            
            # elementary_grades
            print("\n1. elementary_grades テーブル:")
            try:
                cur.execute("DESCRIBE elementary_grades")
                columns = cur.fetchall()
                for col in columns:
                    print(f"  - {col['Field']} ({col['Type']})")
            except:
                print("  テーブルが存在しません")
            
            # internal_points (中学生内申点)
            print("\n2. internal_points テーブル:")
            try:
                cur.execute("DESCRIBE internal_points")
                columns = cur.fetchall()
                for col in columns:
                    print(f"  - {col['Field']} ({col['Type']})")
            except:
                print("  テーブルが存在しません")
            
            # exam_scores (定期テスト)
            print("\n3. exam_scores テーブル:")
            try:
                cur.execute("DESCRIBE exam_scores")
                columns = cur.fetchall()
                for col in columns:
                    print(f"  - {col['Field']} ({col['Type']})")
            except:
                print("  テーブルが存在しません")
            
            # subjects
            print("\n4. subjects テーブル:")
            try:
                cur.execute("DESCRIBE subjects")
                columns = cur.fetchall()
                for col in columns:
                    print(f"  - {col['Field']} ({col['Type']})")
                    
                # 科目データも確認
                cur.execute("SELECT * FROM subjects")
                subjects = cur.fetchall()
                print("\n  科目データ:")
                for subject in subjects:
                    print(f"    ID: {subject['id']}, Name: {subject['name']}")
            except:
                print("  テーブルが存在しません")
            
            # point_history
            print("\n5. point_history テーブル:")
            try:
                cur.execute("DESCRIBE point_history")
                columns = cur.fetchall()
                for col in columns:
                    print(f"  - {col['Field']} ({col['Type']})")
            except:
                print("  テーブルが存在しません")
                
    finally:
        conn.close()

if __name__ == "__main__":
    check_tables()