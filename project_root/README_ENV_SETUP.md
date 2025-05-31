# 環境変数設定ガイド

## セットアップ手順

1. **環境変数ファイルの作成**
   ```bash
   cp .env.example .env
   ```

2. **.envファイルの編集**
   `.env`ファイルを開き、以下の値を設定してください：

   - `SECRET_KEY`: Flaskのセキュリティキー（ランダムな文字列を生成）
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```

   - `MYSQL_*`: データベース接続情報
   - `GOOGLE_CALENDAR_API_KEY`: Google Calendar APIキー
   - `GOOGLE_CLOUD_VISION_API_KEY`: Google Cloud Vision APIキー

3. **依存関係のインストール**
   ```bash
   pip install -r requirements.txt
   ```

## 環境変数一覧

| 環境変数名 | 説明 | 必須 |
|-----------|------|------|
| `SECRET_KEY` | Flaskセッション暗号化キー | ✓ |
| `MYSQL_HOST` | MySQLホスト名 | ✓ |
| `MYSQL_USER` | MySQLユーザー名 | ✓ |
| `MYSQL_PASSWORD` | MySQLパスワード | ✓ |
| `MYSQL_DB` | データベース名 | ✓ |
| `MYSQL_PORT` | MySQLポート番号（デフォルト: 3306） | |
| `GOOGLE_CALENDAR_API_KEY` | Google Calendar APIキー | |
| `GOOGLE_CALENDAR_ID` | カレンダーID | |
| `GOOGLE_CLOUD_VISION_API_KEY` | Google Cloud Vision APIキー | |

## セキュリティ上の注意

- **絶対に`.env`ファイルをGitにコミットしないでください**
- 本番環境では強力なランダムキーを使用してください
- 定期的にパスワードとAPIキーを更新してください
- 異なる環境（開発/本番）では異なる認証情報を使用してください

## トラブルシューティング

1. **ModuleNotFoundError: No module named 'dotenv'**
   ```bash
   pip install python-dotenv
   ```

2. **データベース接続エラー**
   - `.env`ファイルのデータベース設定を確認
   - ファイアウォール設定を確認
   - データベースサーバーが稼働していることを確認

3. **設定の検証**
   ```bash
   python config.py
   ```
   このコマンドで設定の妥当性をチェックできます。