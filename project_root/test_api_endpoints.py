#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
新しく追加したAPIエンドポイントのテストスクリプト
"""

import requests
import json

# テスト用のベースURL
BASE_URL = "http://127.0.0.1:5000"

def test_improvement_filter_advanced():
    """成績向上フィルター高度版APIのテスト"""
    print("=== /api/improvement-filter-advanced テスト ===")
    
    # テスト用のパラメータ
    test_params = [
        {},  # パラメータなし
        {'month': 5},  # 5月のデータ
        {'subject': '1'},  # 国語のデータ
        {'min_improvement': 10},  # 10点以上の向上
        {'points_status': 'not_awarded'},  # 未付与のみ
    ]
    
    for i, params in enumerate(test_params):
        print(f"\nテスト {i+1}: パラメータ {params}")
        
        try:
            response = requests.get(f"{BASE_URL}/api/improvement-filter-advanced", params=params)
            print(f"ステータスコード: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    students_count = len(data.get('students', []))
                    stats = data.get('statistics', {})
                    print(f"成功: {students_count}人の生徒データを取得")
                    print(f"統計: 総数={stats.get('total', 0)}, 付与済み={stats.get('awarded', 0)}, 未付与={stats.get('not_awarded', 0)}")
                else:
                    print(f"API エラー: {data.get('message', 'Unknown error')}")
            else:
                print(f"HTTP エラー: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("エラー: サーバーに接続できません。アプリケーションが起動しているか確認してください。")
        except Exception as e:
            print(f"エラー: {e}")

def test_award_improvement_points():
    """成績向上ポイント付与APIのテスト"""
    print("\n=== /api/award-improvement-points テスト ===")
    
    # テスト用のデータ
    test_data = {
        'student_ids': [1, 2, 3],  # テスト用の生徒ID
        'points': 30,
        'reason': 'テスト用成績向上ポイント'
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/award-improvement-points",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"成功: {data.get('success_count', 0)}人にポイントを付与")
                if data.get('error_count', 0) > 0:
                    print(f"エラー: {data.get('error_count', 0)}人でエラー発生")
                    for error in data.get('errors', []):
                        print(f"  生徒ID {error.get('student_id')}: {error.get('error')}")
            else:
                print(f"API エラー: {data.get('message', 'Unknown error')}")
        else:
            print(f"HTTP エラー: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("エラー: サーバーに接続できません。アプリケーションが起動しているか確認してください。")
    except Exception as e:
        print(f"エラー: {e}")

def check_endpoints_exist():
    """エンドポイントが存在するかチェック"""
    print("=== エンドポイント存在確認 ===")
    
    endpoints = [
        "/api/improvement-filter-advanced",
        "/api/award-improvement-points"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 401:
                print(f"✓ {endpoint} - エンドポイント存在（認証エラー）")
            elif response.status_code == 404:
                print(f"✗ {endpoint} - エンドポイント未発見")
            else:
                print(f"✓ {endpoint} - エンドポイント存在（ステータス: {response.status_code}）")
                
        except requests.exceptions.ConnectionError:
            print(f"✗ サーバーに接続できません")
            break
        except Exception as e:
            print(f"✗ {endpoint} - エラー: {e}")

if __name__ == "__main__":
    print("APIエンドポイントテスト開始")
    print("注意: 認証が必要なため、401エラーが返されるのは正常です")
    
    # まずエンドポイントの存在確認
    check_endpoints_exist()
    
    # 詳細テスト（認証なしなので401エラーが予想される）
    test_improvement_filter_advanced()
    test_award_improvement_points()
    
    print("\nテスト完了")
