#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
成績向上ポイント付与システムの修正確認テストスクリプト
"""

import os
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime

try:
    from config import Config
except ImportError:
    class Config:
        MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
        MYSQL_USER = os.getenv('MYSQL_USER', 'root')
        MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
        MYSQL_DB = os.getenv('MYSQL_DB', 'test')
        MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))

def get_db_connection():
    """データベース接続を取得"""
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        port=Config.MYSQL_PORT,
        charset='utf8mb4',
        cursorclass=DictCursor
    )

def check_improvement_points_status():
    """成績向上ポイントの付与状況を確認"""
    conn = get_db_connection()
    
    print("=== 成績向上ポイント付与状況の確認 ===\n")
    
    try:
        with conn.cursor() as cur:
            # 1. grade_improvement タイプのポイント履歴を確認
            print("1. grade_improvement タイプのポイント履歴:")
            cur.execute("""
                SELECT ph.id, ph.user_id, u.name as student_name, 
                       ph.points, ph.event_type, ph.comment, ph.created_at
                FROM point_history ph
                JOIN users u ON ph.user_id = u.id
                WHERE ph.event_type LIKE 'grade_improvement%'
                AND ph.is_active = 1
                ORDER BY ph.created_at DESC
                LIMIT 10
            """)
            
            results = cur.fetchall()
            if results:
                for row in results:
                    print(f"  ID: {row['id']}, 生徒: {row['student_name']} (ID: {row['user_id']})")
                    print(f"  ポイント: {row['points']}, タイプ: {row['event_type']}")
                    print(f"  コメント: {row['comment']}")
                    print(f"  付与日時: {row['created_at']}")
                    print("  ---")
            else:
                print("  grade_improvement タイプのポイント履歴が見つかりません")
            
            print("\n2. '成績向上' タイプのポイント履歴:")
            cur.execute("""
                SELECT ph.id, ph.user_id, u.name as student_name, 
                       ph.points, ph.event_type, ph.comment, ph.created_at
                FROM point_history ph
                JOIN users u ON ph.user_id = u.id
                WHERE ph.event_type = '成績向上'
                AND ph.is_active = 1
                ORDER BY ph.created_at DESC
                LIMIT 10
            """)
            
            results = cur.fetchall()
            if results:
                for row in results:
                    print(f"  ID: {row['id']}, 生徒: {row['student_name']} (ID: {row['user_id']})")
                    print(f"  ポイント: {row['points']}, タイプ: {row['event_type']}")
                    print(f"  コメント: {row['comment']}")
                    print(f"  付与日時: {row['created_at']}")
                    print("  ---")
            else:
                print("  '成績向上' タイプのポイント履歴が見つかりません")
            
            # 3. 月情報を含むコメントのポイント履歴を確認
            print("\n3. 月情報を含むコメントのポイント履歴:")
            cur.execute("""
                SELECT ph.id, ph.user_id, u.name as student_name, 
                       ph.points, ph.event_type, ph.comment, ph.created_at
                FROM point_history ph
                JOIN users u ON ph.user_id = u.id
                WHERE ph.comment LIKE '%月%'
                AND ph.event_type IN ('grade_improvement', '成績向上')
                AND ph.is_active = 1
                ORDER BY ph.created_at DESC
                LIMIT 10
            """)
            
            results = cur.fetchall()
            if results:
                for row in results:
                    print(f"  ID: {row['id']}, 生徒: {row['student_name']} (ID: {row['user_id']})")
                    print(f"  ポイント: {row['points']}, タイプ: {row['event_type']}")
                    print(f"  コメント: {row['comment']}")
                    print(f"  付与日時: {row['created_at']}")
                    print("  ---")
            else:
                print("  月情報を含むコメントのポイント履歴が見つかりません")
            
            # 4. 最新の小学生の成績データと付与状況を確認
            print("\n4. 最新の小学生成績向上データと付与状況:")
            current_month = datetime.now().month
            previous_month = current_month - 1 if current_month > 1 else 12
            
            cur.execute("""
                SELECT 
                    g1.student_id,
                    u.name as student_name,
                    g1.month as current_month,
                    g1.score as current_score,
                    g2.score as previous_score,
                    (g1.score - g2.score) as improvement,
                    EXISTS(
                        SELECT 1 FROM point_history ph 
                        WHERE ph.user_id = g1.student_id 
                        AND ph.event_type LIKE 'grade_improvement%%'
                        AND ph.comment LIKE CONCAT('%%', %s, '月%%')
                        AND ph.is_active = 1
                    ) as points_awarded
                FROM elementary_grades g1
                JOIN elementary_grades g2 ON 
                    g1.student_id = g2.student_id AND 
                    g1.grade_year = g2.grade_year AND 
                    g1.subject = g2.subject AND
                    g1.month = %s AND 
                    g2.month = %s
                JOIN users u ON g1.student_id = u.id
                WHERE u.school_type = 'elementary'
                AND (g1.score - g2.score) >= 5
                ORDER BY (g1.score - g2.score) DESC
                LIMIT 5
            """, (current_month, current_month, previous_month))
            
            results = cur.fetchall()
            if results:
                for row in results:
                    status = "付与済み" if row['points_awarded'] else "未付与"
                    print(f"  生徒: {row['student_name']} (ID: {row['student_id']})")
                    print(f"  {row['current_month']}月: {row['previous_score']}点 → {row['current_score']}点 (+{row['improvement']}点)")
                    print(f"  ポイント付与状況: {status}")
                    print("  ---")
            else:
                print("  成績向上データが見つかりません")
                
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

def test_point_award():
    """テスト用のポイント付与を実行"""
    conn = get_db_connection()
    
    print("\n\n=== テスト用ポイント付与 ===")
    
    try:
        # テスト用の教師IDと生徒IDを設定（実際のデータに合わせて変更してください）
        teacher_id = 1  # 教師ID
        student_id = 2  # 生徒ID
        month = datetime.now().month
        
        with conn.cursor() as cur:
            # テスト用のポイント付与
            comment = f"成績向上(小幅向上) - {month}月 国語"
            
            cur.execute("""
                INSERT INTO point_history 
                (user_id, points, event_type, comment, created_by, created_at, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, 1)
            """, (student_id, 20, 'grade_improvement', comment, teacher_id, datetime.now()))
            
            conn.commit()
            print(f"テストポイントを付与しました: 生徒ID {student_id}, 20ポイント")
            print(f"コメント: {comment}")
            
    except Exception as e:
        conn.rollback()
        print(f"エラーが発生しました: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("成績向上ポイントシステム修正確認テスト")
    print("=" * 50)
    
    # 現在の状況を確認
    check_improvement_points_status()
    
    # テストポイント付与を実行するか確認
    # response = input("\n\nテスト用のポイント付与を実行しますか？ (y/n): ")
    # if response.lower() == 'y':
    #     test_point_award()
    #     print("\n再度状況を確認します:")
    #     check_improvement_points_status()