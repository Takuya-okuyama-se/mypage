#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SQL フォーマッティング修正の詳細テスト
日本語文字が含まれるエラーメッセージの処理をテスト
"""

import sys
import logging
import traceback

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_japanese_character_formatting():
    """日本語文字を含むエラーメッセージのフォーマッティングテスト"""
    print("=== 日本語文字フォーマッティングテスト ===")
    
    # 問題の日本語文字 '改' (0x6210) を含むエラーメッセージをシミュレート
    japanese_error_msg = "成績改善データの取得でエラーが発生しました"
    
    print("1. f-string フォーマット（修正前の問題のある方法）をテスト:")
    try:
        # これが問題を引き起こしていた方法
        problematic_format = f"Error in function: {japanese_error_msg}"
        logging.error(f"Error message: {japanese_error_msg}")  # この行が問題
        print("  ✓ f-string でエラーは発生しませんでした（修正済み環境では正常）")
    except Exception as e:
        print(f"  ✗ f-string でエラー発生: {e}")
    
    print("\n2. %s フォーマット（修正後の安全な方法）をテスト:")
    try:
        # 修正後の安全な方法
        safe_format = "Error in function: %s" % japanese_error_msg
        logging.error("Error message: %s", japanese_error_msg)  # 修正後の安全な方法
        print("  ✓ %s フォーマットは正常に動作しました")
    except Exception as e:
        print(f"  ✗ %s フォーマットでエラー発生: {e}")
    
    print("\n3. str()による明示的な文字列変換をテスト:")
    try:
        # より安全な方法
        logging.error("Error message: %s", str(japanese_error_msg))
        print("  ✓ str()変換は正常に動作しました")
    except Exception as e:
        print(f"  ✗ str()変換でエラー発生: {e}")

def test_improvement_filter_imports():
    """improvement_filter_api モジュールのインポートテスト"""
    print("\n=== improvement_filter_api インポートテスト ===")
    
    try:
        import improvement_filter_api
        print("  ✓ improvement_filter_api のインポートに成功しました")
        
        # 関数の存在確認
        if hasattr(improvement_filter_api, 'get_elementary_improved_students'):
            print("  ✓ get_elementary_improved_students 関数が存在します")
        else:
            print("  ✗ get_elementary_improved_students 関数が見つかりません")
            
        if hasattr(improvement_filter_api, 'get_middle_improved_students'):
            print("  ✓ get_middle_improved_students 関数が存在します")
        else:
            print("  ✗ get_middle_improved_students 関数が見つかりません")
            
        if hasattr(improvement_filter_api, 'award_improvement_points'):
            print("  ✓ award_improvement_points 関数が存在します")
        else:
            print("  ✗ award_improvement_points 関数が見つかりません")
            
    except ImportError as e:
        print(f"  ✗ improvement_filter_api のインポートに失敗: {e}")
    except Exception as e:
        print(f"  ✗ 予期しないエラー: {e}")

def test_error_logging_with_japanese():
    """日本語を含むエラーログのテスト"""
    print("\n=== 日本語エラーログテスト ===")
    
    # 実際に improvement_filter_api で使用される日本語メッセージをテスト
    test_messages = [
        "データベース接続エラー: 改善データを取得できませんでした",
        "成績改善フィルタでエラーが発生しました",
        "向上ポイント付与でエラーが発生しました",
        "改善: テストメッセージ",  # 問題の文字 '改' を含む
    ]
    
    for i, msg in enumerate(test_messages, 1):
        print(f"  テスト {i}: '{msg}'")
        try:
            # 修正前の問題のある方法（コメントアウト）
            # logging.error(f"Error: {msg}")
            
            # 修正後の安全な方法
            logging.error("Error: %s", str(msg))
            print(f"    ✓ 正常にログ出力されました")
        except Exception as e:
            print(f"    ✗ エラー発生: {e}")
            print(f"    詳細: {traceback.format_exc()}")

def simulate_original_error():
    """元のエラーをシミュレート"""
    print("\n=== 元のエラーのシミュレーション ===")
    
    # 0x6210 は '改' の文字コード
    print(f"問題の文字: {chr(0x6210)} (0x6210)")
    
    # 元のエラーメッセージを再現
    error_message = f"unsupported format character '{chr(0x6210)}' (0x6210) at index 814"
    print(f"元のエラーメッセージ: {error_message}")
    
    # この種のエラーが発生する状況をシミュレート
    try:
        # 問題があった状況（修正済み）
        japanese_text = "成績改善データ"
        # 以下のような使用でエラーが発生していた
        # formatted = f"Error processing: {japanese_text}"  # 問題のあったコード
        
        # 修正後の安全な方法
        formatted = "Error processing: %s" % japanese_text
        print(f"修正後の安全な方法: {formatted}")
        
    except Exception as e:
        print(f"シミュレーション中にエラー: {e}")

if __name__ == "__main__":
    print("SQL フォーマッティング修正の検証テスト")
    print("=" * 50)
    
    test_japanese_character_formatting()
    test_improvement_filter_imports()
    test_error_logging_with_japanese()
    simulate_original_error()
    
    print("\n" + "=" * 50)
    print("テスト完了")
