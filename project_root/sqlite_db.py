#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import os
from datetime import datetime

# SQLiteデータベースのパス
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_database.db')

def get_sqlite_connection():
    """SQLite接続を取得する関数"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 辞書形式でアクセス
    return conn

def init_sqlite_database():
    """SQLiteデータベースを初期化する関数"""
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    
    # usersテーブル作成
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        school_type TEXT NOT NULL,
        grade_level INTEGER NOT NULL,
        attendance_days TEXT,
        last_login_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # attendance_recordsテーブル作成
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        teacher_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # point_historyテーブル作成
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS point_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        points INTEGER NOT NULL,
        comment TEXT,
        awarded_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # point_event_typesテーブル作成
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS point_event_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        min_points INTEGER DEFAULT 0,
        max_points INTEGER DEFAULT 100,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # テストデータ挿入
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        # 生徒データ挿入
        test_users = [
            (1, '田中太郎', 'elementary', 5, '1,3,5', '2025-05-28'),
            (2, '佐藤花子', 'elementary', 6, '2,4', '2025-05-27'),
            (3, '山田次郎', 'middle', 7, '1,3,5', '2025-05-29'),
            (1001, '鈴木一郎', 'elementary', 5, '1,3', '2025-05-26'),
            (1002, '加藤結愛', 'elementary', 4, '1,4', '2025-05-25'),
            (2001, '高田健', 'middle', 8, '2,5', '2025-05-28'),
            (2002, '松本さくら', 'middle', 9, '1,3,5', '2025-05-27'),
            (3001, '高橋美咲', 'high', 10, '1,3', '2025-05-29'),
            (3002, '山田大輝', 'high', 12, '2,4', '2025-05-26')
        ]
        
        for user_data in test_users:
            cursor.execute('''
            INSERT OR REPLACE INTO users (id, name, school_type, grade_level, attendance_days, last_login_date)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', user_data)
    
    # ポイントイベントタイプ挿入
    cursor.execute('SELECT COUNT(*) FROM point_event_types')
    if cursor.fetchone()[0] == 0:
        event_types = [
            ('attendance_daily', '出席（1日）', 10, 10),
            ('homework_completion', '宿題完了', 5, 15),
            ('test_improvement', '成績向上', 20, 100),
            ('behavior_good', '良い行動', 5, 20)
        ]
        
        for event_type in event_types:
            cursor.execute('''
            INSERT INTO point_event_types (name, description, min_points, max_points)
            VALUES (?, ?, ?, ?)
            ''', event_type)
    
    conn.commit()
    conn.close()
    print(f"SQLiteデータベースを初期化しました: {DB_PATH}")

def award_attendance_points_sqlite(user_id, date=None, teacher_id=None):
    """SQLite版の出席ポイント付与関数"""
    try:
        if date is None:
            date = datetime.now().date()
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        # ユーザー情報取得
        cursor.execute("SELECT grade_level, school_type, attendance_days FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return False, "ユーザーが見つかりません"
        
        # 授業日かチェック
        today = datetime.now()
        js_day_of_week = today.weekday() + 1 if today.weekday() < 6 else 0  # 変換: 1=月曜, 0=日曜
        
        attendance_days = []
        if user['attendance_days']:
            attendance_days = [int(day.strip()) for day in user['attendance_days'].split(',')]
        
        if js_day_of_week not in attendance_days:
            return False, "今日は授業日ではありません"
        
        # 重複チェック
        cursor.execute('''
        SELECT id FROM point_history 
        WHERE user_id = ? AND event_type = 'attendance_daily' AND DATE(created_at) = DATE(?)
        ''', (user_id, date))
        
        if cursor.fetchone():
            return False, "本日分の出席ポイントは既に付与済みです"
        
        # ポイント付与
        points = 10  # 出席ポイントは固定10ポイント
        cursor.execute('''
        INSERT INTO point_history (user_id, event_type, points, comment, awarded_by)
        VALUES (?, 'attendance_daily', ?, '出席ポイント', ?)
        ''', (user_id, points, teacher_id))
        
        conn.commit()
        conn.close()
        
        return True, f"{points}ポイントを付与しました"
        
    except Exception as e:
        return False, f"ポイント付与エラー: {str(e)}"

def save_attendance_record_sqlite(user_id, date, status, teacher_id=None):
    """SQLite版の出席記録保存関数"""
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        # 既存レコードチェック
        cursor.execute('''
        SELECT id FROM attendance_records WHERE user_id = ? AND date = ?
        ''', (user_id, date))
        
        existing = cursor.fetchone()
        
        if existing:
            # 更新
            cursor.execute('''
            UPDATE attendance_records SET status = ?, teacher_id = ?
            WHERE user_id = ? AND date = ?
            ''', (status, teacher_id, user_id, date))
        else:
            # 新規挿入
            cursor.execute('''
            INSERT INTO attendance_records (user_id, date, status, teacher_id)
            VALUES (?, ?, ?, ?)
            ''', (user_id, date, status, teacher_id))
        
        conn.commit()
        conn.close()
        
        return True, "出席記録を保存しました"
        
    except Exception as e:
        return False, f"出席記録保存エラー: {str(e)}"

def get_students_sqlite():
    """SQLite版の生徒データ取得関数"""
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, name, school_type, grade_level, attendance_days, last_login_date
        FROM users
        ORDER BY school_type, grade_level, name
        ''')
        
        students = []
        for row in cursor.fetchall():
            # 辞書形式に変換
            student = {
                'id': row['id'],
                'name': row['name'],
                'school_type': row['school_type'],
                'grade_level': row['grade_level'],
                'attendance_days': row['attendance_days'],
                'last_login_date': row['last_login_date'],
                'hasLoggedInToday': False  # 簡易実装
            }
            
            # attendance_daysを配列に変換
            if student['attendance_days']:
                student['attendance_days'] = [int(day.strip()) for day in student['attendance_days'].split(',')]
            else:
                student['attendance_days'] = []
            
            students.append(student)
        
        conn.close()
        return students
        
    except Exception as e:
        print(f"生徒データ取得エラー: {e}")
        return []

if __name__ == "__main__":
    # データベース初期化
    init_sqlite_database()
