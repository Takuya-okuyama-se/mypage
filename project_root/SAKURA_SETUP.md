# さくらのレンタルサーバー セットアップガイド

## Python パッケージのインストール

さくらのレンタルサーバーでは、以下の方法でパッケージをインストールしてください：

### 1. ユーザーディレクトリにインストール
```bash
pip install --user python-dotenv==0.19.0
pip install --user bcrypt==3.2.0
pip install --user flask==2.0.1
pip install --user pymysql==1.0.2
pip install --user requests==2.26.0
```

### 2. 環境変数の設定
`.env`ファイルが正しく配置されていることを確認してください：
- パス: `/home/[ユーザー名]/www/project_root/.env`

### 3. パーミッションの設定
```bash
chmod 755 index.cgi
chmod 644 .env
chmod 644 app.py
```

### 4. トラブルシューティング

#### "No module named 'dotenv'" エラーの場合：
1. python-dotenvを手動インストール
2. .envファイルの手動読み込み機能を使用（app.pyに実装済み）

#### データベース接続エラーの場合：
1. さくらのコントロールパネルでMySQLサービスが有効になっているか確認
2. データベース接続情報が正しいか確認

### 5. テスト方法
```bash
python app.py
```
または
```
https://[ドメイン]/myapp/index.cgi/
```
でアクセステスト
