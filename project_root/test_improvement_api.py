#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
APIエンドポイントテスト用スクリプト
新しく追加した成績向上フィルターAPIとポイント付与APIをテスト
"""

import requests
import json
import sys

# APIのベースURL
BASE_URL = "http://localhost:5000"

def test_improvement_filter_api():
    """
    成績向上フィルターAPIのテスト
    """
    print("=== 成績向上フィルターAPIテスト ===")
    
    # テスト用パラメータ
    params = {
        'month': '12',
        'subject': 'all',
        'min_improvement': '0',
        'points_status': 'all'
    }
    
    url = f"{BASE_URL}/api/improvement-filter-advanced"
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"レスポンス内容: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            # データ構造の確認
            if 'students' in data:
                print(f"学生数: {len(data['students'])}")
                if data['students']:
                    print(f"最初の学生データ: {data['students'][0]}")
            
            if 'statistics' in data:
                print(f"統計情報: {data['statistics']}")
                
        else:
            print(f"エラー: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("エラー: サーバーに接続できません。アプリケーションが起動しているか確認してください。")
    except Exception as e:
        print(f"エラー: {str(e)}")

def test_award_points_api():
    """
    ポイント付与APIのテスト
    """
    print("\n=== ポイント付与APIテスト ===")
    
    # テスト用データ
    test_data = {
        'student_ids': [1, 2],  # テスト用学生ID
        'points': 5,
        'reason': 'テスト用ポイント付与'
    }
    
    url = f"{BASE_URL}/api/award-improvement-points"
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, data=json.dumps(test_data), headers=headers, timeout=10)
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"レスポンス内容: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"エラー: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("エラー: サーバーに接続できません。アプリケーションが起動しているか確認してください。")
    except Exception as e:
        print(f"エラー: {str(e)}")

def test_endpoint_existence():
    """
    エンドポイントの存在確認
    """
    print("\n=== エンドポイント存在確認 ===")
    
    endpoints = [
        "/api/improvement-filter-advanced",
        "/api/award-improvement-points",
        "/api/teacher/improved-students",
        "/api/teacher/award-improvement-points"
    ]
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 404:
                print(f"❌ {endpoint}: 存在しません (404)")
            elif response.status_code == 405:
                print(f"✅ {endpoint}: 存在します (405 - Method Not Allowed)")
            elif response.status_code == 401:
                print(f"✅ {endpoint}: 存在します (401 - Unauthorized)")
            elif response.status_code == 200:
                print(f"✅ {endpoint}: 存在します (200 - OK)")
            else:
                print(f"? {endpoint}: ステータスコード {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"❌ 接続エラー: サーバーが起動していない可能性があります")
            break
        except Exception as e:
            print(f"❌ {endpoint}: エラー - {str(e)}")

if __name__ == "__main__":
    print("APIエンドポイントテスト開始")
    print("=" * 50)
    
    # エンドポイントの存在確認
    test_endpoint_existence()
    
    # 成績向上フィルターAPIテスト
    test_improvement_filter_api()
    
    # ポイント付与APIテスト（認証エラーが予想されますが、エンドポイントの動作確認）
    test_award_points_api()
    
    print("\n" + "=" * 50)
    print("APIエンドポイントテスト完了")
