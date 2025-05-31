#!/usr/local/bin/python
# -*- coding: utf-8 -*-

# test_point_system.py - データベース駆動ポイントシステムのテストスクリプト

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection
from points_utils import (
    get_point_event_config, 
    generate_points_from_config,
    generate_login_points,
    award_attendance_points
)

def test_database_connection():
    """データベース接続のテスト"""
    print("=== データベース接続テスト ===")
    try:
        conn = get_db_connection()
        print("✓ データベース接続成功")
        return conn
    except Exception as e:
        print(f"✗ データベース接続失敗: {e}")
        return None

def test_point_event_configs(conn):
    """ポイントイベント設定の確認"""
    print("\n=== ポイントイベント設定テスト ===")
    
    # テスト対象のイベントタイプ
    test_events = [
        'login',
        'attendance_daily', 
        'birthday',
        'grade_improvement_small',
        'grade_improvement_medium',
        'grade_improvement_large',
        'attendance_bonus_10days',
        'attendance_bonus_20days'
    ]
    
    results = {}
    for event in test_events:
        config = get_point_event_config(conn, event)
        results[event] = config
        if config:
            print(f"✓ {event}: {config['min_points']}-{config['max_points']}ポイント")
        else:
            print(f"✗ {event}: 設定が見つかりません")
    
    return results

def test_point_generation(conn):
    """ポイント生成のテスト"""
    print("\n=== ポイント生成テスト ===")
    
    test_events = ['login', 'attendance_daily', 'birthday']
    
    for event in test_events:
        try:
            # 5回テストして範囲を確認
            points_list = []
            for i in range(5):
                points = generate_points_from_config(conn, event)
                points_list.append(points)
            
            config = get_point_event_config(conn, event)
            if config:
                min_p, max_p = config['min_points'], config['max_points']
                print(f"✓ {event}: 生成ポイント {points_list} (範囲: {min_p}-{max_p})")
                
                # 範囲チェック
                valid = all(min_p <= p <= max_p for p in points_list)
                if valid:
                    print(f"  ✓ 全て範囲内")
                else:
                    print(f"  ✗ 範囲外のポイントあり")
            else:
                print(f"✗ {event}: 設定なし、フォールバック値 {points_list}")
                
        except Exception as e:
            print(f"✗ {event}: ポイント生成エラー {e}")

def test_login_points(conn):
    """ログインポイント機能のテスト"""
    print("\n=== ログインポイント機能テスト ===")
    
    try:
        # テスト用ユーザーID（実際のユーザーIDに変更してください）
        test_user_id = 1
        
        points = generate_login_points(conn)
        print(f"✓ ログインポイント生成: {points}ポイント")
        
        # 設定値と比較
        config = get_point_event_config(conn, 'login')
        if config:
            min_p, max_p = config['min_points'], config['max_points']
            if min_p <= points <= max_p:
                print(f"  ✓ 設定範囲内 ({min_p}-{max_p})")
            else:
                print(f"  ✗ 設定範囲外 ({min_p}-{max_p})")
        
    except Exception as e:
        print(f"✗ ログインポイントテストエラー: {e}")

def test_attendance_points(conn):
    """出席ポイント機能のテスト"""
    print("\n=== 出席ポイント機能テスト ===")
    
    try:
        # attendance_daily の設定確認
        config = get_point_event_config(conn, 'attendance_daily')
        if config:
            print(f"✓ 出席ポイント設定: {config['min_points']}-{config['max_points']}ポイント")
        else:
            print("✗ 出席ポイント設定が見つかりません")
            
        # ポイント生成テスト
        points = generate_points_from_config(conn, 'attendance_daily')
        print(f"✓ 出席ポイント生成: {points}ポイント")
        
    except Exception as e:
        print(f"✗ 出席ポイントテストエラー: {e}")

def main():
    """メインテスト実行"""
    print("データベース駆動ポイントシステム テスト開始")
    print("=" * 50)
    
    # データベース接続テスト
    conn = test_database_connection()
    if not conn:
        print("データベース接続に失敗したため、テストを終了します")
        return
    
    try:
        # 各種テスト実行
        test_point_event_configs(conn)
        test_point_generation(conn)
        test_login_points(conn)
        test_attendance_points(conn)
        
        print("\n" + "=" * 50)
        print("テスト完了")
        
    except Exception as e:
        print(f"テスト実行中にエラーが発生しました: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
