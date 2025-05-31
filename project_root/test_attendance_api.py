#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
出席記録APIの直接テスト
"""

import requests
import json

def test_attendance_api():
    # テストデータ
    test_data = {
        'attendance_data': {
            '1': 'present',  # 生徒ID 1 を出席に
            '2': 'absent'    # 生徒ID 2 を欠席に
        },
        'date': '2025-05-29',
        'award_points': True
    }
    
    # セッションを作成してログインをシミュレート
    session = requests.Session()
    
    try:
        # まず教師としてログインを試行（実際のログイン機能があれば）
        print("=== 出席記録API テスト開始 ===")
        print(f"送信データ: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
        
        # 直接APIを呼び出し
        url = 'http://localhost:5000/api/teacher/attendance'
        
        response = session.post(
            url,
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"成功: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"エラー: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"テスト中にエラーが発生: {e}")

if __name__ == '__main__':
    test_attendance_api()
