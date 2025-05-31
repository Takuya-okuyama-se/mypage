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
    
    print('=== grade_improvementイベントタイプのポイント履歴レコード ===')
    cursor.execute('''
        SELECT ph.*, s.student_name 
        FROM point_history ph 
        LEFT JOIN students s ON ph.student_id = s.student_id
        WHERE ph.event_type = "grade_improvement"
        ORDER BY ph.created_at DESC
    ''')
    records = cursor.fetchall()
    
    if records:
        print(f'見つかったレコード数: {len(records)}')
        for record in records:
            print(f'ID: {record["id"]}, 生徒: {record["student_name"]}, ポイント: {record["points"]}, 作成日: {record["created_at"]}')
    else:
        print('grade_improvementイベントタイプのレコードは見つかりませんでした')
    
    print('\n=== 存在しないイベントタイプのレコード確認 ===')
    cursor.execute('''
        SELECT ph.event_type, COUNT(*) as count
        FROM point_history ph
        LEFT JOIN point_event_types pet ON ph.event_type = pet.name
        WHERE pet.name IS NULL
        GROUP BY ph.event_type
        ORDER BY count DESC
    ''')
    missing_types = cursor.fetchall()
    
    if missing_types:
        print('存在しないイベントタイプが見つかりました:')
        for mt in missing_types:
            print(f'イベントタイプ: {mt["event_type"]}, レコード数: {mt["count"]}')
    else:
        print('すべてのイベントタイプが正常に登録されています')
    
    conn.close()
    
except Exception as e:
    print(f'エラー: {e}')
