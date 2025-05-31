#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
宿題完了イベントタイプを修正するスクリプト
"""

import pymysql
import sys
import os

# config モジュールのインポート
try:
    from config import Config
except ImportError:
    class Config:
        MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
        MYSQL_USER = os.getenv('MYSQL_USER', 'root')
        MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
        MYSQL_DB = os.getenv('MYSQL_DB', 'test')
        MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))

# MySQL 接続設定
MYSQL_CONFIG = {
    'host': Config.MYSQL_HOST,
    'user': Config.MYSQL_USER,
    'password': Config.MYSQL_PASSWORD,
    'database': Config.MYSQL_DB,
    'port': Config.MYSQL_PORT,
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    """データベース接続を取得"""
    return pymysql.connect(**MYSQL_CONFIG)

def fix_homework_completion_event_type():
    """homework_completionイベントタイプを修正"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 既存のhomework_completionイベントタイプを確認
            cur.execute("SELECT * FROM point_event_types WHERE name = 'homework_completion'")
            existing = cur.fetchone()
            
            if existing:
                print("既存のhomework_completionイベントタイプが見つかりました:")
                print(f"  ID: {existing['id']}")
                print(f"  名前: {existing['name']}")
                print(f"  表示名: {existing['display_name']}")
                print(f"  説明: {existing['description']}")
                
                # 更新
                cur.execute("""
                    UPDATE point_event_types 
                    SET display_name = '宿題完了ボーナス',
                        description = '宿題完了時に獲得',
                        min_points = 10,
                        max_points = 10,
                        teacher_can_award = 1,
                        is_active = 1
                    WHERE name = 'homework_completion'
                """)
                print("homework_completionイベントタイプを更新しました。")
            else:
                # 新規挿入
                cur.execute("""
                    INSERT INTO point_event_types 
                    (name, display_name, description, min_points, max_points, teacher_can_award, is_active)
                    VALUES ('homework_completion', '宿題完了ボーナス', '宿題完了時に獲得', 10, 10, 1, 1)
                """)
                print("homework_completionイベントタイプを新規追加しました。")
            
            # 確認のため、全てのイベントタイプを表示
            cur.execute("SELECT * FROM point_event_types ORDER BY id")
            all_types = cur.fetchall()
            
            print("\n現在のイベントタイプ一覧:")
            for event_type in all_types:
                print(f"  {event_type['name']}: {event_type['display_name']}")
            
            # コミット
            conn.commit()
            print("\nデータベースの変更をコミットしました。")
            
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

def check_point_history():
    """point_historyテーブルのhomework_completionレコードを確認"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # homework_completionイベントタイプのポイント履歴を確認
            cur.execute("""
                SELECT ph.*, pet.display_name as event_display_name
                FROM point_history ph
                LEFT JOIN point_event_types pet ON ph.event_type = pet.name
                WHERE ph.event_type = 'homework_completion'
                ORDER BY ph.created_at DESC
                LIMIT 10
            """)
            records = cur.fetchall()
            
            print("\nhomework_completionのポイント履歴（最新10件）:")
            if records:
                for record in records:
                    display_name = record['event_display_name'] or record['event_type']
                    print(f"  ID: {record['id']}, ユーザー: {record['user_id']}, "
                          f"ポイント: {record['points']}, 表示名: {display_name}, "
                          f"作成日: {record['created_at']}")
            else:
                print("  homework_completionのポイント履歴は見つかりませんでした。")
                
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("宿題完了イベントタイプ修正スクリプトを開始します...")
    fix_homework_completion_event_type()
    check_point_history()
    print("修正完了しました。")
