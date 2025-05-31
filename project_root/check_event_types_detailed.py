#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

def check_database():
    try:
        # 接続情報の表示
        host = os.getenv('DB_HOST', 'localhost')
        user = os.getenv('DB_USER', 'root')
        database = os.getenv('DB_NAME', 'juku_management')
        
        print(f'接続先: {host}, ユーザー: {user}, データベース: {database}')
        
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=os.getenv('DB_PASSWORD', ''),
            database=database,
            charset='utf8mb4'
        )
        
        cursor = conn.cursor(dictionary=True)
        
        # テーブルの存在確認
        cursor.execute("SHOW TABLES LIKE 'point_event_types'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print('point_event_typesテーブルが存在しません')
            return
        
        print('point_event_typesテーブルが存在します')
        
        # テーブル構造の確認
        cursor.execute("DESCRIBE point_event_types")
        columns = cursor.fetchall()
        print('\nテーブル構造:')
        for col in columns:
            print(f'  {col["Field"]}: {col["Type"]}')
        
        # レコード数の確認
        cursor.execute('SELECT COUNT(*) as count FROM point_event_types')
        count = cursor.fetchone()
        print(f'\nレコード数: {count["count"]}')
        
        # 全レコードの表示
        cursor.execute('SELECT * FROM point_event_types ORDER BY name')
        records = cursor.fetchall()
        
        print('\n=== 全レコード ===')
        for record in records:
            print(f'名前: {record["name"]}, 表示名: {record["display_name"]}')
        
        # grade_improvementの確認
        cursor.execute('SELECT * FROM point_event_types WHERE name = %s', ('grade_improvement',))
        grade_improvement = cursor.fetchone()
        
        if grade_improvement:
            print(f'\n=== grade_improvement イベントタイプ ===')
            for key, value in grade_improvement.items():
                print(f'{key}: {value}')
        else:
            print('\ngrade_improvementイベントタイプが見つかりません')
        
        conn.close()
        
    except Exception as e:
        print(f'エラー: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_database()
