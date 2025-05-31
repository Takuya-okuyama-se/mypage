# GitHub Actions デプロイ設定

## セットアップ手順

### 1. GitHub Secretsの設定

GitHubリポジトリの設定画面で以下のSecretsを追加してください：

1. リポジトリの **Settings** タブを開く
2. 左側メニューの **Secrets and variables** → **Actions** を選択
3. **New repository secret** をクリック
4. 以下の2つのSecretを追加：

| Secret名 | 説明 |
|----------|------|
| `FTP_USERNAME` | さくらサーバーのFTPユーザー名 |
| `FTP_PASSWORD` | さくらサーバーのFTPパスワード |

### 2. デプロイの実行

- `main`または`master`ブランチにプッシュすると自動的にデプロイが実行されます
- 手動でデプロイを実行する場合は、GitHubの **Actions** タブから **Deploy to Sakura Server** を選択し、**Run workflow** をクリック

### 3. デプロイ設定のカスタマイズ

#### 除外ファイルの追加

`deploy.yml`の`exclude`セクションに追加したいパターンを記載：

```yaml
exclude: |
  **/新しい除外パターン/**
```

#### デプロイ先ディレクトリの変更

`server-dir`を変更：

```yaml
server-dir: /home/seishinn/www/新しいディレクトリ/
```

### 4. トラブルシューティング

#### FTP接続エラー

- FTPユーザー名とパスワードが正しいか確認
- さくらサーバーのFTPアクセス制限を確認
- パッシブモードの設定が必要な場合があります

#### タイムアウトエラー

`timeout`値を増やす：

```yaml
timeout: 1200000  # 20分
```

#### 特定のファイルがアップロードされない

- `.gitignore`に含まれていないか確認
- `exclude`パターンに含まれていないか確認

### 5. セキュリティ上の注意

- FTPパスワードは必ずGitHub Secretsを使用し、直接コードに記載しない
- `.env`ファイルなどの機密情報は自動的に除外されます
- 本番環境では`dry-run: false`に設定されていることを確認

### 6. デプロイログの確認

1. GitHubの **Actions** タブを開く
2. 実行されたワークフローをクリック
3. **Deploy** ジョブをクリック
4. 各ステップの詳細ログを確認

エラーが発生した場合は、ログに詳細情報が記載されています。