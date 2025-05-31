#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
成績向上フィルターAPIのデバッグ用スクリプト
"""

from flask import Flask, request, jsonify
import os
import sys
import traceback

# 現在のディレクトリをPythonパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

app = Flask(__name__)

@app.route('/debug/test-import')
def test_import():
    """improvement_filter_api.pyのインポートテスト"""
    result = {
        'current_dir': current_dir,
        'python_path': sys.path[:5],  # 最初の5つのパスのみ
        'import_test': {}
    }
    
    # improvement_filter_api.pyのインポートを試みる
    try:
        from improvement_filter_api import get_elementary_improved_students
        result['import_test']['improvement_filter_api'] = 'Success'
    except ImportError as e:
        result['import_test']['improvement_filter_api'] = f'Failed: {str(e)}'
    except Exception as e:
        result['import_test']['improvement_filter_api'] = f'Error: {str(e)}'
    
    # configのインポートを試みる
    try:
        from config import Config
        result['import_test']['config'] = 'Success'
        result['config_check'] = {
            'MYSQL_HOST': Config.MYSQL_HOST if hasattr(Config, 'MYSQL_HOST') else 'Not found',
            'MYSQL_USER': Config.MYSQL_USER if hasattr(Config, 'MYSQL_USER') else 'Not found'
        }
    except ImportError as e:
        result['import_test']['config'] = f'Failed: {str(e)}'
    except Exception as e:
        result['import_test']['config'] = f'Error: {str(e)}'
    
    return jsonify(result)

@app.route('/debug/test-db')
def test_db():
    """データベース接続テスト"""
    result = {'db_test': {}}
    
    try:
        import pymysql
        result['db_test']['pymysql'] = 'Imported successfully'
        
        # 環境変数から接続情報を取得
        from config import Config
        
        conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            port=Config.MYSQL_PORT,
            charset='utf8mb4'
        )
        
        with conn.cursor() as cur:
            # テーブル確認
            cur.execute("SHOW TABLES LIKE '%grade%'")
            tables = cur.fetchall()
            result['db_test']['grade_tables'] = [t[0] for t in tables]
            
            cur.execute("SHOW TABLES LIKE '%point%'")
            tables = cur.fetchall()
            result['db_test']['point_tables'] = [t[0] for t in tables]
            
        conn.close()
        result['db_test']['connection'] = 'Success'
        
    except Exception as e:
        result['db_test']['error'] = str(e)
        result['db_test']['traceback'] = traceback.format_exc()
    
    return jsonify(result)

@app.route('/debug/test-api-simple')
def test_api_simple():
    """シンプルなAPIテスト"""
    try:
        # 最小限のデータを返す
        return jsonify({
            'success': True,
            'students': [],
            'stats': {
                'total': 0,
                'average': 0,
                'pending_points': 0,
                'awarded_points': 0
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # CGIとして実行
    print("Content-Type: application/json")
    print()
    
    path_info = os.environ.get('PATH_INFO', '')
    
    if '/test-import' in path_info:
        print(test_import().get_data(as_text=True))
    elif '/test-db' in path_info:
        print(test_db().get_data(as_text=True))
    else:
        print(test_api_simple().get_data(as_text=True))