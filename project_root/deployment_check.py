#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
デプロイ前の設定確認スクリプト
本番環境に必要な設定がすべて揃っているかをチェック
"""

import os
import sys

# 環境変数を手動で読み込み
def load_env_file():
    """手動で.envファイルを読み込む"""
    try:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
    except Exception:
        pass

# 環境変数を読み込み
load_env_file()

def check_environment():
    """環境設定をチェック"""
    checks = []
    
    # 1. 必須環境変数の確認
    required_vars = [
        'SECRET_KEY',
        'MYSQL_HOST',
        'MYSQL_USER',
        'MYSQL_PASSWORD',
        'MYSQL_DB',
        'GOOGLE_CLOUD_VISION_API_KEY'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # APIキーは一部のみ表示
            if 'API_KEY' in var or 'PASSWORD' in var:
                display_value = value[:10] + '...' if len(value) > 10 else '設定済み'
            else:
                display_value = value
            checks.append(f"✅ {var}: {display_value}")
        else:
            checks.append(f"❌ {var}: 未設定")
      # 2. ファイルの存在確認
    required_files = [
        'app.py',
        'templates/english_learning_simple.html',
        'templates/vision_api_diagnostic.html',
        '.env'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            checks.append(f"✅ ファイル存在: {file_path}")
        else:
            checks.append(f"❌ ファイル不在: {file_path}")
    
    # 3. ポート設定の確認
    port = os.getenv('PORT', '5000')
    checks.append(f"📡 ポート設定: {port}")
    
    # 4. デバッグモードの確認
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    if debug_mode:
        checks.append("⚠️ デバッグモード: 有効（本番環境では無効にしてください）")
    else:
        checks.append("✅ デバッグモード: 無効")
    
    return checks

def create_deployment_notes():
    """デプロイ時の注意事項を生成"""
    notes = [
        "🚀 **デプロイ時のチェックリスト**",
        "",
        "**必須確認項目:**",
        "□ .env ファイルがサーバーにアップロードされている",
        "□ Google Cloud Vision API キーが有効である",
        "□ データベース接続情報が正しい",
        "□ requirements.txt に必要なパッケージが含まれている",
        "",
        "**テスト用URL:**",
        "□ /api/vision/diagnostic - Vision API診断ページ",
        "□ /api/english/recognize - 手書き認識API",
        "□ /test/english-learning - 英語学習テストページ",
        "",
        "**デプロイ後の確認手順:**",
        "1. 診断ページ (/api/vision/diagnostic) にアクセス",
        "2. API接続テストを実行",
        "3. 手書き認識機能をテスト",
        "4. 英語学習ページで実際の動作を確認",
        "",
        "**トラブルシューティング:**",
        "- API接続エラー → APIキーと環境変数を確認",
        "- 認識できない → 文字をはっきり大きく描く",
        "- タイムアウト → ネットワーク接続を確認",
        "",
        "**重要な設定:**",
        f"- Vision API Key: {os.getenv('GOOGLE_CLOUD_VISION_API_KEY', '未設定')[:10]}...",
        f"- Database Host: {os.getenv('MYSQL_HOST', '未設定')}",
        f"- Debug Mode: {os.getenv('FLASK_DEBUG', 'False')}"
    ]
    
    return '\n'.join(notes)

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 デプロイ前設定確認")
    print("=" * 60)
    
    # 環境確認
    checks = check_environment()
    for check in checks:
        print(check)
    
    print("\n" + "=" * 60)
    print("📋 デプロイメントノート")
    print("=" * 60)
    
    # デプロイノート
    notes = create_deployment_notes()
    print(notes)
    
    # エラーがないかチェック
    error_count = sum(1 for check in checks if check.startswith('❌'))
    
    print("\n" + "=" * 60)
    if error_count == 0:
        print("🎉 すべての設定が完了しています！デプロイ可能です。")
    else:
        print(f"⚠️ {error_count}個の問題があります。修正してからデプロイしてください。")
    print("=" * 60)
