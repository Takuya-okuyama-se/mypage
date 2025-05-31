#!/usr/local/bin/python
# -*- coding: utf-8 -*-

# 直接実行用のシンプルなデータベーステーブル確認スクリプト

print("Content-Type: text/plain; charset=utf-8")
print()

try:
    import pymysql
    from pymysql.cursors import DictCursor
    
    # データベース接続
    conn = pymysql.connect(
        host='mysql3103.db.sakura.ne.jp',
        user='seishinn',
        password='Yakyuubu8',
        database='seishinn_test',
        port=3306,
        charset='utf8mb4',
        cursorclass=DictCursor
    )
    
    with conn.cursor() as cur:
        # テーブル一覧
        print("=== Tables ===")
        cur.execute("SHOW TABLES")
        for table in cur.fetchall():
            table_name = list(table.values())[0]
            if 'grade' in table_name or 'point' in table_name or 'exam' in table_name:
                print(table_name)
        
        print("\n=== Elementary Grades Table ===")
        try:
            cur.execute("DESCRIBE elementary_grades")
            for col in cur.fetchall():
                print(f"{col['Field']} - {col['Type']}")
        except:
            print("Table not found")
            
        print("\n=== Internal Points Table ===")
        try:
            cur.execute("DESCRIBE internal_points")
            for col in cur.fetchall():
                print(f"{col['Field']} - {col['Type']}")
        except:
            print("Table not found")
            
        print("\n=== Exam Scores Table ===")
        try:
            cur.execute("DESCRIBE exam_scores")
            for col in cur.fetchall():
                print(f"{col['Field']} - {col['Type']}")
        except:
            print("Table not found")
    
    conn.close()
    print("\nDone")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()