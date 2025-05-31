#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
JSONエラーデバッグ用スクリプト
"""

import json
import sys
import os

print("Content-Type: text/plain; charset=utf-8")
print()

# 現在のディレクトリをPythonパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    # アプリケーションをインポート
    from app import app, get_db_connection
    
    print("=== Database Connection Test ===")
    
    # データベース接続テスト
    try:
        conn = get_db_connection()
        print("Database connection: SUCCESS")
        
        with conn.cursor() as cur:
            # 生徒数を確認
            cur.execute("SELECT COUNT(*) as count FROM users WHERE role = 'student'")
            result = cur.fetchone()
            print(f"Student count: {result['count']}")
            
            # 最初の5人の生徒データを取得
            cur.execute("""
                SELECT id, name, grade_level, school_type 
                FROM users 
                WHERE role = 'student' 
                LIMIT 5
            """)
            students = cur.fetchall()
            
            print("\n=== Sample Student Data ===")
            for student in students:
                print(f"ID: {student['id']}, Name: {student['name']}, Grade: {student['grade_level']}, Type: {student['school_type']}")
            
            # JSONエンコードテスト
            print("\n=== JSON Encoding Test ===")
            try:
                json_str = json.dumps(students, ensure_ascii=False, indent=2)
                print("JSON encoding: SUCCESS")
                print(f"JSON length: {len(json_str)} characters")
                
                # 最初の200文字を表示
                print("\nFirst 200 characters of JSON:")
                print(json_str[:200])
                
            except Exception as e:
                print(f"JSON encoding error: {e}")
                
        conn.close()
        
    except Exception as e:
        print(f"Database error: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n=== API Endpoint Test ===")
    
    # APIエンドポイントを直接呼び出してみる
    with app.test_client() as client:
        # セッションデータを設定
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'teacher'
        
        # APIを呼び出し
        response = client.get('/api/students/elementary')
        
        print(f"Status code: {response.status_code}")
        print(f"Content-Type: {response.content_type}")
        print(f"Response length: {len(response.data)} bytes")
        
        # レスポンスの最初と最後を確認
        data = response.data.decode('utf-8')
        print(f"\nFirst 200 characters:")
        print(repr(data[:200]))
        
        print(f"\nLast 200 characters:")
        print(repr(data[-200:]))
        
        # 5695バイト目周辺を確認（エラーが発生した位置）
        if len(data) > 5695:
            print(f"\nAround position 5695:")
            start = max(0, 5695 - 100)
            end = min(len(data), 5695 + 100)
            print(repr(data[start:end]))
            
            # 改行やタブなどの特殊文字を可視化
            print("\nSpecial characters around position 5695:")
            for i in range(start, end):
                char = data[i]
                if ord(char) < 32 or ord(char) > 126:
                    print(f"Position {i}: {repr(char)} (code: {ord(char)})")
        
except Exception as e:
    print(f"Error importing app: {e}")
    import traceback
    traceback.print_exc()