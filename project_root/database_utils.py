# -*- coding: utf-8 -*-
"""
データベース接続ユーティリティ
宿題管理システムの安定性向上のための共通モジュール
"""

import os
import pymysql
import logging
from contextlib import contextmanager
from pymysql.cursors import DictCursor

# 設定をインポート
try:
    from config import Config
except ImportError:
    # config.pyがない場合の環境変数からの直接読み込み
    class Config:
        MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
        MYSQL_USER = os.getenv('MYSQL_USER', 'root')
        MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
        MYSQL_DB = os.getenv('MYSQL_DB', 'test')
        MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))

# データベース設定
DB_CONFIG = {
    'host': Config.MYSQL_HOST,
    'user': Config.MYSQL_USER,
    'password': Config.MYSQL_PASSWORD,
    'database': Config.MYSQL_DB,
    'port': Config.MYSQL_PORT,
    'charset': 'utf8mb4',
    'cursorclass': DictCursor,
    'autocommit': False,  # トランザクション管理のため
    'connect_timeout': 10,
    'read_timeout': 30,
    'write_timeout': 30
}

def get_db_connection():
    """
    データベース接続を取得する関数（改良版）
    エラーハンドリングと接続プールの概念を追加
    """
    try:
        connection = pymysql.connect(**DB_CONFIG)
        connection.ping(reconnect=True)  # 接続確認と自動再接続
        return connection
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        raise

@contextmanager
def get_db_cursor(commit=False):
    """
    データベースカーソルのコンテキストマネージャー
    自動的にコミット・ロールバック・クローズを管理
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Database operation failed: {e}")
        raise
    finally:
        if conn:
            conn.close()

def ensure_homework_tables():
    """
    宿題管理に必要なテーブルを確実に作成する
    """
    with get_db_cursor(commit=True) as cursor:
        # 宿題課題テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS homework_assignments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                created_by INT NOT NULL,
                assigned_date DATE NOT NULL,
                subject VARCHAR(100) NOT NULL,
                textbook VARCHAR(200) NOT NULL,
                topic VARCHAR(300) NOT NULL,
                pages VARCHAR(100),
                completed BOOLEAN DEFAULT FALSE,
                completed_date DATE NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_student_date (student_id, assigned_date),
                INDEX idx_created_by (created_by),
                FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 宿題完了記録テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS homework_completions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                assignment_id INT NOT NULL UNIQUE,
                student_id INT NOT NULL,
                completed_date DATE NOT NULL,
                points_awarded INT DEFAULT 0,
                checked_by INT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_student_date (student_id, completed_date),
                INDEX idx_assignment (assignment_id),
                FOREIGN KEY (assignment_id) REFERENCES homework_assignments(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (checked_by) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 宿題テンプレートテーブル（よく使う宿題パターンを保存）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS homework_templates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                created_by INT NOT NULL,
                subject VARCHAR(100) NOT NULL,
                textbook VARCHAR(200) NOT NULL,
                topic VARCHAR(300) NOT NULL,
                pages VARCHAR(100),
                usage_count INT DEFAULT 1,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_created_by (created_by),
                INDEX idx_usage (usage_count DESC, last_used DESC),
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

def validate_elementary_student(cursor, student_id):
    """
    小学5・6年生かどうかを検証する
    """
    cursor.execute("""
        SELECT id, name, grade_level, school_type 
        FROM users 
        WHERE id = %s AND role = 'student' 
        AND school_type = 'elementary' 
        AND grade_level IN (5, 6)
    """, (student_id,))
    
    student = cursor.fetchone()
    if not student:
        raise ValueError("対象は小学5・6年生のみです")
    
    return student

def get_homework_calendar_data(teacher_id, student_id, year, month):
    """
    カレンダー用の宿題データを取得する（最適化版）
    """
    with get_db_cursor() as cursor:
        # 生徒の検証
        student = validate_elementary_student(cursor, student_id)
        
        # 月の範囲を計算
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{month+1:02d}-01"
        
        # 宿題データを取得
        cursor.execute("""
            SELECT 
                h.id,
                h.assigned_date,
                h.subject,
                h.textbook,
                h.topic,
                h.pages,
                CASE WHEN hc.id IS NOT NULL THEN 1 ELSE 0 END as completed,
                hc.completed_date,
                hc.points_awarded
            FROM homework_assignments h
            LEFT JOIN homework_completions hc ON h.id = hc.assignment_id
            WHERE h.student_id = %s 
            AND h.created_by = %s
            AND h.assigned_date >= %s 
            AND h.assigned_date < %s
            ORDER BY h.assigned_date, h.id
        """, (student_id, teacher_id, start_date, end_date))
        
        homework_list = cursor.fetchall()
        
        # 日付別にグループ化
        homework_by_date = {}
        for hw in homework_list:
            date_str = hw['assigned_date'].strftime('%Y-%m-%d')
            if date_str not in homework_by_date:
                homework_by_date[date_str] = []
            homework_by_date[date_str].append(hw)
        
        return {
            'student': student,
            'homework_by_date': homework_by_date,
            'year': year,
            'month': month
        }

def save_homework_template(teacher_id, subject, textbook, topic, pages):
    """
    宿題テンプレートを保存または更新する
    """
    with get_db_cursor(commit=True) as cursor:
        # 既存のテンプレートを確認
        cursor.execute("""
            SELECT id, usage_count FROM homework_templates
            WHERE created_by = %s AND subject = %s 
            AND textbook = %s AND topic = %s
        """, (teacher_id, subject, textbook, topic))
        
        existing = cursor.fetchone()
        
        if existing:
            # 使用回数を増やす
            cursor.execute("""
                UPDATE homework_templates
                SET usage_count = usage_count + 1,
                    pages = %s,
                    last_used = NOW()
                WHERE id = %s
            """, (pages, existing['id']))
        else:
            # 新規作成
            cursor.execute("""
                INSERT INTO homework_templates 
                (created_by, subject, textbook, topic, pages)
                VALUES (%s, %s, %s, %s, %s)
            """, (teacher_id, subject, textbook, topic, pages))

def get_homework_templates(teacher_id, limit=10):
    """
    よく使う宿題テンプレートを取得する
    """
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT subject, textbook, topic, pages, usage_count, last_used
            FROM homework_templates
            WHERE created_by = %s
            ORDER BY usage_count DESC, last_used DESC
            LIMIT %s
        """, (teacher_id, limit))
        
        return cursor.fetchall()
