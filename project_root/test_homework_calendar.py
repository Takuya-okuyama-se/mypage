#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宿題カレンダー機能のテストスクリプト
"""

import pymysql
import json
from datetime import datetime, timedelta

def get_db_connection():
    """データベース接続を取得"""
    return pymysql.connect(
        host='localhost',
        user='takuyama-yutaka',
        password='Shinku@1207',
        database='yutaka',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def test_homework_calendar():
    """宿題カレンダー機能をテスト"""
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cur:
            print("=== 宿題カレンダーテスト開始 ===")
            
            # 1. 小学5・6年生の生徒を取得
            print("\n1. 小学5・6年生の生徒を確認...")
            cur.execute("""
                SELECT id, name, grade_level, school_type 
                FROM users 
                WHERE role = 'student' AND school_type = 'elementary' 
                AND grade_level IN (5, 6)
                ORDER BY grade_level, name
            """)
            students = cur.fetchall()
            
            if not students:
                print("❌ 小学5・6年生の生徒が見つかりません")
                return
            
            print(f"✅ 小学5・6年生の生徒: {len(students)}人")
            for student in students:
                print(f"   - ID:{student['id']} {student['name']} (小{student['grade_level']}年生)")
            
            # テスト用の生徒IDを設定（実際のIDに変更してください）
            test_student_id = students[0]['id']
            print(f"\n📚 テスト対象生徒: ID={test_student_id}, {students[0]['name']}")
            
            # 2. 宿題データを確認
            print("\n2. 宿題データを確認...")
            cur.execute("""
                SELECT h.*, 
                       CASE WHEN hc.id IS NOT NULL THEN 1 ELSE 0 END as completed,
                       hc.completed_date, hc.points_awarded
                FROM homework_assignments h
                LEFT JOIN homework_completions hc ON h.id = hc.assignment_id
                WHERE h.student_id = %s
                ORDER BY h.assigned_date DESC
                LIMIT 10
            """, (test_student_id,))
            
            homework_list = cur.fetchall()
            
            if not homework_list:
                print("❌ 宿題データが見つかりません")
                # テストデータを作成
                print("\n📝 テストデータを作成します...")
                
                # 今月のテストデータを作成
                today = datetime.now()
                test_dates = [
                    today.replace(day=1),
                    today.replace(day=5),
                    today.replace(day=10),
                    today.replace(day=15),
                    today.replace(day=20)
                ]
                
                for i, test_date in enumerate(test_dates):
                    if test_date <= today:  # 未来の日付は避ける
                        cur.execute("""
                            INSERT INTO homework_assignments 
                            (student_id, assigned_date, subject, textbook, topic, pages, created_by, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            test_student_id,
                            test_date.strftime('%Y-%m-%d'),
                            ['国語', '算数', '英語', '理科', '社会'][i % 5],
                            f'テキスト{i+1}',
                            f'テスト項目{i+1}',
                            f'{(i+1)*5}-{(i+1)*5+5}',
                            1  # teacher_id (要調整)
                        ))
                
                conn.commit()
                print("✅ テストデータを作成しました")
                
                # 再度データを取得
                cur.execute("""
                    SELECT h.*, 
                           CASE WHEN hc.id IS NOT NULL THEN 1 ELSE 0 END as completed,
                           hc.completed_date, hc.points_awarded
                    FROM homework_assignments h
                    LEFT JOIN homework_completions hc ON h.id = hc.assignment_id
                    WHERE h.student_id = %s
                    ORDER BY h.assigned_date DESC
                    LIMIT 10
                """, (test_student_id,))
                
                homework_list = cur.fetchall()
            
            print(f"✅ 宿題データ: {len(homework_list)}件")
            for hw in homework_list:
                assigned_date = hw['assigned_date']
                if hasattr(assigned_date, 'strftime'):
                    assigned_date = assigned_date.strftime('%Y-%m-%d')
                print(f"   - ID:{hw['id']} {assigned_date} {hw['subject']} (完了:{hw['completed']})")
            
            # 3. 今月のデータを取得（APIと同じロジック）
            print("\n3. 今月のカレンダーデータを取得...")
            today = datetime.now()
            year = today.year
            month = today.month
            
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year+1}-01-01"
            else:
                end_date = f"{year}-{month+1:02d}-01"
            
            print(f"   検索範囲: {start_date} から {end_date}")
            
            cur.execute("""
                SELECT h.id, h.student_id, h.assigned_date, h.subject, h.textbook, h.topic, h.pages,
                       CASE WHEN hc.id IS NOT NULL THEN 1 ELSE 0 END as completed,
                       hc.completed_date, hc.points_awarded, h.created_by
                FROM homework_assignments h
                LEFT JOIN homework_completions hc ON h.id = hc.assignment_id
                WHERE h.student_id = %s
                AND h.assigned_date >= %s AND h.assigned_date < %s
                ORDER BY h.assigned_date
            """, (test_student_id, start_date, end_date))
            
            calendar_data = cur.fetchall()
            
            print(f"✅ 今月のカレンダーデータ: {len(calendar_data)}件")
            
            # 日付ごとにグループ化
            by_date = {}
            for hw in calendar_data:
                assigned_date = hw['assigned_date']
                if hasattr(assigned_date, 'strftime'):
                    assigned_date = assigned_date.strftime('%Y-%m-%d')
                
                if assigned_date not in by_date:
                    by_date[assigned_date] = []
                by_date[assigned_date].append(hw)
                
                print(f"   - {assigned_date}: {hw['subject']} (完了:{hw['completed']})")
            
            # 4. JSON形式での出力テスト
            print(f"\n4. JSON形式でのAPI応答シミュレーション...")
            
            # 日付フォーマットを統一
            for hw in calendar_data:
                if 'assigned_date' in hw and hw['assigned_date']:
                    if hasattr(hw['assigned_date'], 'strftime'):
                        hw['assigned_date'] = hw['assigned_date'].strftime('%Y-%m-%d')
            
            api_response = {
                'success': True,
                'homework': calendar_data
            }
            
            print("API応答:")
            print(json.dumps(api_response, indent=2, ensure_ascii=False, default=str))
            
            print(f"\n✅ テスト完了: {len(calendar_data)}件の宿題データが正常に取得できました")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    test_homework_calendar()
