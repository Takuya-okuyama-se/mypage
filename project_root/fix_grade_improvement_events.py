#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
成績向上イベントタイプの確認と修正スクリプト
"""

import mysql.connector
from dotenv import load_dotenv
import os

# .envファイルから環境変数を読み込み
load_dotenv()

def get_db_connection():
    """データベース接続を取得"""
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'juku_management'),
        charset='utf8mb4'
    )

def check_and_fix_grade_improvement():
    """grade_improvementイベントタイプの確認と修正"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        print("=== point_event_types テーブルの確認 ===")
        
        # テーブルの存在確認
        cursor.execute("SHOW TABLES LIKE 'point_event_types'")
        if not cursor.fetchone():
            print("ERROR: point_event_typesテーブルが存在しません")
            return
        
        # 全レコードの表示
        cursor.execute("SELECT * FROM point_event_types ORDER BY name")
        all_records = cursor.fetchall()
        
        print(f"\n現在のレコード数: {len(all_records)}")
        for record in all_records:
            print(f"  名前: {record['name']}, 表示名: {record['display_name']}")
        
        # grade_improvementの有無を確認
        grade_improvement_records = []
        for pattern in ['grade_improvement', 'grade_improvement_small', 'grade_improvement_medium', 'grade_improvement_large']:
            cursor.execute("SELECT * FROM point_event_types WHERE name = %s", (pattern,))
            result = cursor.fetchone()
            if result:
                grade_improvement_records.append(result)
        
        print(f"\n=== 成績向上関連イベントタイプの確認 ===")
        if grade_improvement_records:
            print("以下の成績向上関連イベントタイプが見つかりました:")
            for record in grade_improvement_records:
                print(f"  名前: {record['name']}")
                print(f"  表示名: {record['display_name']}")
                print(f"  最小ポイント: {record['min_points']}")
                print(f"  最大ポイント: {record['max_points']}")
                print(f"  アクティブ: {record.get('is_active', '不明')}")
                print("  ---")
        else:
            print("成績向上関連のイベントタイプが見つかりません")
            print("\n成績向上関連のイベントタイプを作成します...")
            
            # 成績向上イベントタイプを追加
            improvement_types = [
                {
                    'name': 'grade_improvement_small',
                    'display_name': '成績向上ボーナス(小)',
                    'description': '前回より5点以上成績向上',
                    'min_points': 20,
                    'max_points': 20,
                    'teacher_can_award': 1,
                    'is_active': 1
                },
                {
                    'name': 'grade_improvement_medium',
                    'display_name': '成績向上ボーナス(中)',
                    'description': '前回より10点以上成績向上',
                    'min_points': 30,
                    'max_points': 30,
                    'teacher_can_award': 1,
                    'is_active': 1
                },
                {
                    'name': 'grade_improvement_large',
                    'display_name': '成績向上ボーナス(大)',
                    'description': '前回より15点以上成績向上',
                    'min_points': 50,
                    'max_points': 50,
                    'teacher_can_award': 1,
                    'is_active': 1
                },
                {
                    'name': 'grade_improvement',
                    'display_name': '成績向上',
                    'description': '一般的な成績向上ボーナス',
                    'min_points': 20,
                    'max_points': 50,
                    'teacher_can_award': 1,
                    'is_active': 1
                }
            ]
            
            for event_type in improvement_types:
                cursor.execute("""
                    INSERT INTO point_event_types 
                    (name, display_name, description, min_points, max_points, teacher_can_award, is_active)
                    VALUES (%(name)s, %(display_name)s, %(description)s, %(min_points)s, %(max_points)s, %(teacher_can_award)s, %(is_active)s)
                    ON DUPLICATE KEY UPDATE
                    display_name = VALUES(display_name),
                    description = VALUES(description),
                    min_points = VALUES(min_points),
                    max_points = VALUES(max_points),
                    teacher_can_award = VALUES(teacher_can_award),
                    is_active = VALUES(is_active)
                """, event_type)
                print(f"  作成/更新: {event_type['name']} -> {event_type['display_name']}")
            
            conn.commit()
            print("\n成績向上イベントタイプを作成/更新しました")
        
        # point_historyでgrade_improvementを使用しているレコードの確認
        print(f"\n=== point_historyでの使用状況 ===")
        cursor.execute("""
            SELECT ph.event_type, COUNT(*) as count,
                   pe.display_name
            FROM point_history ph
            LEFT JOIN point_event_types pe ON ph.event_type = pe.name
            WHERE ph.event_type LIKE '%grade_improvement%'
            GROUP BY ph.event_type, pe.display_name
            ORDER BY count DESC
        """)
        usage_records = cursor.fetchall()
        
        if usage_records:
            print("grade_improvement関連のポイント履歴:")
            for record in usage_records:
                display_name = record['display_name'] or "表示名未設定"
                print(f"  {record['event_type']}: {record['count']}件 (表示名: {display_name})")
        else:
            print("grade_improvement関連のポイント履歴は見つかりませんでした")
        
        # 表示名が設定されていないレコードの確認
        print(f"\n=== 表示名未設定のポイント履歴 ===")
        cursor.execute("""
            SELECT ph.event_type, COUNT(*) as count
            FROM point_history ph
            LEFT JOIN point_event_types pe ON ph.event_type = pe.name
            WHERE pe.display_name IS NULL AND ph.is_active = 1
            GROUP BY ph.event_type
            ORDER BY count DESC
            LIMIT 10
        """)
        missing_display_records = cursor.fetchall()
        
        if missing_display_records:
            print("表示名が設定されていないイベントタイプ:")
            for record in missing_display_records:
                print(f"  {record['event_type']}: {record['count']}件")
        else:
            print("すべてのイベントタイプに表示名が設定されています")
        
        conn.close()
        print("\n処理が完了しました")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_and_fix_grade_improvement()
