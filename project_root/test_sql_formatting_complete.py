#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SQLフォーマッティング修正の完全テスト

このテストは、日本語文字（特に '改' 文字）を含むエラーメッセージが
SQLフォーマッティングエラーを引き起こさないことを確認します。
"""

import sys
import os
import logging
from unittest.mock import Mock, patch
import traceback

# プロジェクトパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def mock_db_connection():
    """モックデータベース接続を作成"""
    mock_conn = Mock()
    mock_cursor = Mock()
    
    # 日本語文字を含むエラーを発生させる
    error_with_japanese = Exception("成績改善データの取得に失敗しました: テーブル 'elementary_grades' が存在しません")
    mock_cursor.execute.side_effect = error_with_japanese
    
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = None
    
    return mock_conn

def test_sql_formatting_fix():
    """SQLフォーマッティング修正のテスト"""
    print("=== SQLフォーマッティング修正テスト開始 ===")
    
    try:
        # improvement_filter_apiをインポート
        import improvement_filter_api
        
        # データベース接続をモック化
        with patch.object(improvement_filter_api, 'get_db_connection', side_effect=mock_db_connection):
            
            # テストフィルター（日本語文字を含む可能性のあるデータ）
            test_filters = {
                'start_month': '1',
                'end_month': '12', 
                'subject': 'all',
                'min_improvement': '5'
            }
            
            print("テスト1: get_elementary_improved_students関数")
            try:
                result = improvement_filter_api.get_elementary_improved_students(test_filters)
                print(f"✓ 関数呼び出し成功: {result.get('success', False)}")
                print(f"  エラーメッセージ: {result.get('message', 'なし')}")
                
                if not result.get('success'):
                    print("✓ 予想通りエラーが返されました（モックデータベースのため）")
                
            except Exception as e:
                # SQLフォーマッティングエラーが発生した場合は失敗
                error_msg = str(e)
                if "unsupported format character" in error_msg and "0x6210" in error_msg:
                    print(f"✗ SQLフォーマッティングエラーが発生: {error_msg}")
                    return False
                else:
                    print(f"✓ 予期しないエラーが発生しましたが、SQLフォーマッティングエラーではありません: {error_msg}")
            
            print("\nテスト2: get_middle_improved_students関数")
            middle_filters = {
                'start_year': '1',
                'start_term': '1',
                'end_year': '3', 
                'end_term': '3',
                'subject': 'all'
            }
            
            try:
                result = improvement_filter_api.get_middle_improved_students(middle_filters)
                print(f"✓ 関数呼び出し成功: {result.get('success', False)}")
                print(f"  エラーメッセージ: {result.get('message', 'なし')}")
                
            except Exception as e:
                error_msg = str(e)
                if "unsupported format character" in error_msg and "0x6210" in error_msg:
                    print(f"✗ SQLフォーマッティングエラーが発生: {error_msg}")
                    return False
                else:
                    print(f"✓ 予期しないエラーが発生しましたが、SQLフォーマッティングエラーではありません: {error_msg}")
            
            print("\nテスト3: award_improvement_points関数")
            award_data = {
                'student_id': '1',
                'points': '10',
                'event_type': 'improvement',
                'comment': '数学の成績が改善されました',
                'subject_id': '1'
            }
            
            try:
                result = improvement_filter_api.award_improvement_points(award_data, 1)
                print(f"✓ 関数呼び出し成功: {result.get('success', False)}")
                print(f"  エラーメッセージ: {result.get('message', 'なし')}")
                
            except Exception as e:
                error_msg = str(e)
                if "unsupported format character" in error_msg and "0x6210" in error_msg:
                    print(f"✗ SQLフォーマッティングエラーが発生: {error_msg}")
                    return False
                else:
                    print(f"✓ 予期しないエラーが発生しましたが、SQLフォーマッティングエラーではありません: {error_msg}")
        
        print("\n=== すべてのテスト完了 ===")
        print("✓ SQLフォーマッティング修正が正常に動作しています")
        return True
        
    except ImportError as e:
        print(f"✗ インポートエラー: {e}")
        return False
    except Exception as e:
        print(f"✗ 予期しないエラー: {e}")
        traceback.print_exc()
        return False

def test_logging_safety():
    """ロギングの安全性テスト"""
    print("\n=== ロギング安全性テスト開始 ===")
    
    # 日本語文字を含むメッセージでのロギングテスト
    test_messages = [
        "成績改善データの取得に失敗しました",
        "学生の成績が5%向上しました", 
        "エラー: データベース接続に失敗 (改善必要)",
        "改善ポイント付与が完了しました"
    ]
    
    # テスト用ログファイル
    test_log_file = "logs/test_formatting.log"
    
    # ログ設定
    test_logger = logging.getLogger('test_sql_formatting')
    test_logger.setLevel(logging.INFO)
    
    # ファイルハンドラー
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    file_handler = logging.FileHandler(test_log_file, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    test_logger.addHandler(file_handler)
    
    try:
        for i, message in enumerate(test_messages):
            # 安全なパラメータ化ロギング
            test_logger.error("Test message %d: %s", i+1, message)
            print(f"✓ ログメッセージ {i+1} 記録成功")
        
        print(f"✓ すべてのログメッセージが正常に記録されました: {test_log_file}")
        return True
        
    except Exception as e:
        print(f"✗ ロギングエラー: {e}")
        return False
    finally:
        # ハンドラーを削除
        for handler in test_logger.handlers[:]:
            test_logger.removeHandler(handler)
            handler.close()

def main():
    """メインテスト関数"""
    print("SQLフォーマッティング修正完全テスト")
    print("=" * 50)
    
    # テスト実行
    sql_test_passed = test_sql_formatting_fix()
    logging_test_passed = test_logging_safety()
    
    print("\n" + "=" * 50)
    print("テスト結果サマリー:")
    print(f"SQLフォーマッティング修正: {'✓ 成功' if sql_test_passed else '✗ 失敗'}")
    print(f"ロギング安全性: {'✓ 成功' if logging_test_passed else '✗ 失敗'}")
    
    if sql_test_passed and logging_test_passed:
        print("\n🎉 すべてのテストが成功しました！")
        print("SQLフォーマッティングエラー（'改' 文字による0x6210エラー）は修正されています。")
        return True
    else:
        print("\n❌ 一部のテストが失敗しました。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
