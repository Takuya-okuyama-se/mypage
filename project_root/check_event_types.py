#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'juku_management'),
        charset='utf8mb4'
    )
    
    cursor = conn.cursor(dictionary=True)
    
    print('=== point_event_types テーブルの内容 ===')
    cursor.execute('SELECT * FROM point_event_types ORDER BY name')
    records = cursor.fetchall()
    
    for record in records:
        print(f'名前: {record["name"]}, 表示名: {record["display_name"]}, アクティブ: {record.get("is_active", "不明")}')
    
    print(f'\n合計レコード数: {len(records)}')
    
    # grade_improvementの有無を確認
    cursor.execute('SELECT * FROM point_event_types WHERE name = "grade_improvement"')
    grade_improvement = cursor.fetchone()
    
    if grade_improvement:
        print(f'\n=== grade_improvement イベントタイプ ===')
        print(f'表示名: {grade_improvement["display_name"]}')
        print(f'最小ポイント: {grade_improvement["min_points"]}')
        print(f'最大ポイント: {grade_improvement["max_points"]}')
        print(f'アクティブ: {grade_improvement.get("is_active", "不明")}')
    else:
        print('\ngrade_improvementイベントタイプが見つかりません')
    
    conn.close()
    
except Exception as e:
    print(f'エラー: {e}')
