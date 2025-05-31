#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
config.py - アプリケーション設定を管理するモジュール
環境変数から設定を読み込み、デフォルト値を提供します。
"""

import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

class Config:
    """アプリケーション設定クラス"""
    
    # Flask設定
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-please-change-in-production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # データベース設定
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'test')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_CHARSET = 'utf8mb4'
    
    # Google APIs
    GOOGLE_CALENDAR_API_KEY = os.getenv('GOOGLE_CALENDAR_API_KEY', '')
    GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', '')
    GOOGLE_CLOUD_VISION_API_KEY = os.getenv('GOOGLE_CLOUD_VISION_API_KEY', '')
    
    # 追加のGoogle Vision API Key（index.cgi用）
    GOOGLE_VISION_API_KEY_2 = os.getenv('GOOGLE_VISION_API_KEY_2', '')
    
    # アプリケーション設定
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = 86400  # 24時間
    
    # ファイルアップロード設定
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    
    # ログ設定
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')
    
    @classmethod
    def get_db_config(cls):
        """データベース接続設定を辞書形式で返す"""
        return {
            'host': cls.MYSQL_HOST,
            'user': cls.MYSQL_USER,
            'password': cls.MYSQL_PASSWORD,
            'database': cls.MYSQL_DB,
            'port': cls.MYSQL_PORT,
            'charset': cls.MYSQL_CHARSET,
            'cursorclass': None  # 必要に応じて設定
        }
    
    @classmethod
    def validate_config(cls):
        """設定の妥当性をチェック"""
        errors = []
        
        # 必須設定のチェック
        if not cls.MYSQL_HOST:
            errors.append("MYSQL_HOST is not set")
        if not cls.MYSQL_USER:
            errors.append("MYSQL_USER is not set")
        if not cls.MYSQL_DB:
            errors.append("MYSQL_DB is not set")
        if cls.SECRET_KEY == 'dev-secret-key-please-change-in-production':
            errors.append("SECRET_KEY is using default value - please set a secure key")
        
        # APIキーの警告（必須ではないが推奨）
        if not cls.GOOGLE_CALENDAR_API_KEY:
            errors.append("Warning: GOOGLE_CALENDAR_API_KEY is not set")
        if not cls.GOOGLE_CLOUD_VISION_API_KEY:
            errors.append("Warning: GOOGLE_CLOUD_VISION_API_KEY is not set")
        
        return errors

# 設定の検証（開発時のみ）
if __name__ == "__main__":
    errors = Config.validate_config()
    if errors:
        print("Configuration errors/warnings:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration is valid.")