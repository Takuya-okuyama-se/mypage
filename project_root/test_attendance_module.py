#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 出席記録テーブル修正の動作確認用スクリプト
import sys
import os

try:
    # 現在のファイルの場所を表示
    print(f"現在の実行ファイル: {os.path.abspath(__file__)}")
    print(f"現在のディレクトリ: {os.getcwd()}")
    
    # インポートの動作確認
    print("1. attendance_utils モジュールのインポート確認...")
    import attendance_utils
    print(f"attendance_utils モジュールをインポートできました: {attendance_utils}")
    print(f"ensure_attendance_records_table 関数: {attendance_utils.ensure_attendance_records_table}")
    
    print("\n2. points_utils モジュールのインポート確認...")
    import points_utils
    print(f"points_utils モジュールをインポートできました: {points_utils}")
    
    print("\n正常に完了しました")
except Exception as e:
    print(f"エラーが発生しました: {e}")
    import traceback
    traceback.print_exc()
