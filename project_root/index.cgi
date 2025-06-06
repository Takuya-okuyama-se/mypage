#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import traceback

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
            if script_name.endswith('index.cgi'):
                environ['SCRIPT_NAME'] = script_name
                environ['PATH_INFO'] = path_info
            else:
                environ['SCRIPT_NAME'] = ''
            
            # デバッグ情報をログに記録
            import logging
            logging.basicConfig(filename='/tmp/cgi_debug.log', level=logging.DEBUG)
            logging.debug(f"SCRIPT_NAME: {script_name}")
            logging.debug(f"PATH_INFO: {path_info}")
            
            return self.app(environ, start_response)
    
    # ミドルウェアを適用
    app_with_middleware = ScriptNameMiddleware(app)
    
    # CGIHandler をカスタマイズしてヘッダー出力を制御
    class CustomCGIHandler(CGIHandler):
        def __init__(self):
            # 親クラスの初期化
            super().__init__()
            # CGIHandlerがデフォルトでヘッダーを出力しないように設定
            self.os_environ = os.environ.copy()
    
    # CGIハンドラーでアプリを実行
    handler = CustomCGIHandler()
    handler.run(app_with_middleware)
    
except Exception as e:
    # エラー時の処理
    path_info = os.environ.get('PATH_INFO', '')
    is_api_request = '/api/' in path_info
    
    if is_api_request:
        import json
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({
            'success': False,
            'error': str(e),
            'message': 'Internal server error'
        }))
    else:
        print("Content-Type: text/html; charset=utf-8")
        print()
        print("<h1>エラーが発生しました:</h1>")
        print(f"<p>{str(e)}</p>")
        print("<pre>")
        traceback.print_exc()
        print("</pre>")