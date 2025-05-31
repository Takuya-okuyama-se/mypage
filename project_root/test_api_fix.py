#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API修正のテストスクリプト
"""

import requests
import json

# テスト用のベースURL
BASE_URL = "https://seishin-school.com/myapp/index.cgi"

def test_students_filter():
    """学年フィルタリング機能のテスト"""
    
    # テストケース1: 単一学年
    print("=== テストケース1: 単一学年 ===")
    url = f"{BASE_URL}/api/test/students-filter"
    params = {
        'grade_level': '5',
        'school_type': 'elementary'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {response.text}")
    except Exception as e:
        print(f"エラー: {e}")
    
    print("\n")
    
    # テストケース2: 複数学年（問題となっていたケース）
    print("=== テストケース2: 複数学年（カンマ区切り） ===")
    params = {
        'grade_level': '5,6',
        'school_type': 'elementary'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {response.text}")
    except Exception as e:
        print(f"エラー: {e}")
    
    print("\n")
    
    # テストケース3: 無効な学年
    print("=== テストケース3: 無効な学年 ===")
    params = {
        'grade_level': 'invalid,test',
        'school_type': 'elementary'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {response.text}")
    except Exception as e:
        print(f"エラー: {e}")

def test_original_api():
    """元のAPIエンドポイントのテスト"""
    print("=== 元のAPIエンドポイントテスト ===")
    url = f"{BASE_URL}/api/teacher/students"
    params = {
        'grade_level': '5,6',
        'school_type': 'elementary'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {response.text}")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    print("API修正テストを開始します...\n")
    
    # テスト用エンドポイントのテスト
    test_students_filter()
    
    print("\n" + "="*50 + "\n")
    
    # 元のAPIエンドポイントのテスト
    test_original_api()
    
    print("\nテスト完了")
