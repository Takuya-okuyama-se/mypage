#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import traceback
import cgitb
cgitb.enable(logdir='/tmp')

# パスを設定 - 現在のディレクトリを明示的に追加
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 環境変数の設定（CGI用）
# 設定をインポート
try:
    from config import Config
    os.environ.setdefault('GOOGLE_CLOUD_VISION_API_KEY', Config.GOOGLE_VISION_API_KEY_2 or Config.GOOGLE_CLOUD_VISION_API_KEY)
except ImportError:
    # config.pyがない場合は環境変数から直接読み込み
    os.environ.setdefault('GOOGLE_CLOUD_VISION_API_KEY', os.getenv('GOOGLE_VISION_API_KEY_2', ''))

print("Content-Type: text/html; charset=utf-8")
print()  # ヘッダーと本文の区切り

try:
    # app.pyからアプリをインポート
    from app import app
    
    # Flaskアプリケーションを実行
    from wsgiref.handlers import CGIHandler
      # スクリプト名を修正するためのWSGIミドルウェア
    class ScriptNameMiddleware(object):
        def __init__(self, app):
            self.app = app
        
        def __call__(self, environ, start_response):
            # CGI環境でのパス処理を改善
            script_name = environ.get('SCRIPT_NAME', '')
            path_info = environ.get('PATH_INFO', '')
            
            # /myapp/index.cgi/api/... のような形式のリクエストを処理
            if script_name.endswith('index.cgi') and path_info.startswith('/api/'):
                environ['SCRIPT_NAME'] = script_name
                environ['PATH_INFO'] = path_info
            else:
                environ['SCRIPT_NAME'] = ''
            
            return self.app(environ, start_response)
    
    # ミドルウェアを適用
    app_with_middleware = ScriptNameMiddleware(app)
    
    # CGIハンドラーでアプリを実行
    CGIHandler().run(app_with_middleware)
    
except Exception as e:
    print("Content-Type: text/html\n")
    print("<h1>エラーが発生しました:</h1>")
    print(f"<p>{str(e)}</p>")
    print("<pre>")
    traceback.print_exc()
    print("</pre>")