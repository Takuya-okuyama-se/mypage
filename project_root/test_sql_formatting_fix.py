#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SQLフォーマッティングエラー修正のテストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from improvement_filter_api import get_elementary_improved_students

def test_elementary_improved_students():
    """
    get_elementary_improved_students関数のテスト
    日本語文字を含むデータでSQLフォーマッティングエラーが発生しないかテスト
    """
    print("=" * 50)
    print("SQLフォーマッティングエラー修正テスト開始")
    print("=" * 50)
    
    # テスト用フィルターパラメータ
    test_filters = {
        'start_month': '4',
        'end_month': '5', 
        'subject': 'all',
        'min_improvement': '0'
    }
    
    try:
        print(f"テストパラメータ: {test_filters}")
        print("get_elementary_improved_students関数を実行中...")
        
        result = get_elementary_improved_students(test_filters)
        
        print(f"実行結果: {result}")
        
        if result.get('success'):
            print("✅ テスト成功: SQLフォーマッティングエラーは発生しませんでした")
            print(f"取得した学生数: {len(result.get('students', []))}")
        else:
            print("❌ テスト失敗: エラーが発生しました")
            print(f"エラーメッセージ: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print("❌ テスト中に例外が発生しました")
        print(f"例外メッセージ: {str(e)}")
        print(f"例外タイプ: {type(e).__name__}")
        import traceback
        traceback.print_exc()
    
    print("=" * 50)
    print("テスト完了")
    print("=" * 50)

if __name__ == "__main__":
    test_elementary_improved_students()
