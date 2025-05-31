#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
HOPE ROOMのログイン情報を管理するためのユーティリティ関数
"""

import logging

def get_hope_room_credentials(conn, user_id):
    """
    ユーザーのHOPE ROOMログイン情報を取得する
    
    Args:
        conn: データベース接続
        user_id: ユーザーID
        
    Returns:
        dict: ログイン情報（login_id, password）
    """
    try:
        cursor = conn.cursor()
        
        # 外部サービスログイン情報テーブルがなければ作成
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS external_service_credentials (
                user_id INT NOT NULL,
                service_name VARCHAR(50) NOT NULL,
                login_id VARCHAR(100),
                password VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, service_name)
            )
        """)
        conn.commit()
        
        # ユーザーのHOPE ROOM情報を取得
        cursor.execute("""
            SELECT login_id, password 
            FROM external_service_credentials 
            WHERE user_id = %s AND service_name = 'hope_room'
        """, (user_id,))
        
        result = cursor.fetchone()
        if result:
            return {'login_id': result[0], 'password': result[1]}
        else:
            return {'login_id': '', 'password': ''}
            
    except Exception as e:
        logging.error(f"HOPE ROOMログイン情報取得エラー: {str(e)}")
        return {'login_id': '', 'password': ''}
        
def save_hope_room_credentials(conn, user_id, login_id, password):
    """
    ユーザーのHOPE ROOMログイン情報を保存する
    
    Args:
        conn: データベース接続
        user_id: ユーザーID
        login_id: HOPE ROOMログインID
        password: HOPE ROOMパスワード
        
    Returns:
        bool: 保存成功したかどうか
    """
    try:
        cursor = conn.cursor()
        
        # 外部サービスログイン情報テーブルがなければ作成
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS external_service_credentials (
                user_id INT NOT NULL,
                service_name VARCHAR(50) NOT NULL,
                login_id VARCHAR(100),
                password VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, service_name)
            )
        """)
        
        # データを挿入または更新
        cursor.execute("""
            INSERT INTO external_service_credentials 
            (user_id, service_name, login_id, password) 
            VALUES (%s, 'hope_room', %s, %s)
            ON DUPLICATE KEY UPDATE login_id = %s, password = %s
        """, (user_id, login_id, password, login_id, password))
        
        conn.commit()
        return True
        
    except Exception as e:
        logging.error(f"HOPE ROOMログイン情報保存エラー: {str(e)}")
        try:
            conn.rollback()
        except:
            pass
        return False

def ensure_external_service_credentials_table(conn):
    """
    外部サービス認証情報テーブルの存在確認と作成
    
    Args:
        conn: データベース接続
        
    Returns:
        bool: テーブル作成が成功したかどうか
    """
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS external_service_credentials (
                user_id INT NOT NULL,
                service_name VARCHAR(50) NOT NULL,
                login_id VARCHAR(100),
                password VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, service_name)
            )
        """)
        
        conn.commit()
        return True
        
    except Exception as e:
        logging.error(f"外部サービスログインテーブル作成エラー: {str(e)}")
        try:
            conn.rollback()
        except:
            pass
        return False
