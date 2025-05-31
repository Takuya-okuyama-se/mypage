#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
テスト用データベース接続設定
MySQLに接続できない場合、SQLiteにフォールバックします
"""

import sqlite3
import os
from datetime import datetime

def setup_sqlite_database():
    """SQLiteテスト用データベースを設定"""
    db_path = os.path.join(os.path.dirname(__file__), 'test.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能にする
    
    cursor = conn.cursor()
    
    # テスト用のテーブルを作成
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            grade_level INTEGER DEFAULT 1,
            school_type TEXT DEFAULT 'elementary',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS elementary_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            grade_year INTEGER,
            subject INTEGER,
            month INTEGER,
            score INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id),
            FOREIGN KEY (subject) REFERENCES subjects(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS point_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            points INTEGER,
            event_type TEXT,
            comment TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # テスト用の科目データを挿入
    subjects = ['国語', '算数', '英語', '理科', '社会']
    for i, subject in enumerate(subjects, 1):
        cursor.execute('INSERT OR IGNORE INTO subjects (id, name) VALUES (?, ?)', (i, subject))
    
    # テスト用の講師ユーザーを作成
    cursor.execute('''
        INSERT OR IGNORE INTO users (id, name, role, grade_level, school_type) 
        VALUES (1, 'テスト講師', 'teacher', 0, 'staff')
    ''')
    
    # テスト用の生徒データを挿入
    test_students = [
        (7, 'テスト生徒A', 'student', 5, 'elementary'),
        (8, 'テスト生徒B', 'student', 6, 'elementary'),
        (9, 'テスト生徒C', 'student', 5, 'elementary'),
    ]
    
    for student in test_students:
        cursor.execute('''
            INSERT OR IGNORE INTO users (id, name, role, grade_level, school_type) 
            VALUES (?, ?, ?, ?, ?)
        ''', student)
    
    # テスト用の成績データを挿入（成績向上パターン）
    test_grades = [
        # テスト生徒A - 算数で向上
        (7, 5, 2, 10, 75),  # 10月
        (7, 5, 2, 11, 90),  # 11月（15点向上）
        # テスト生徒B - 国語で向上
        (8, 6, 1, 10, 65),  # 10月
        (8, 6, 1, 11, 80),  # 11月（15点向上）
        # テスト生徒C - 英語で向上
        (9, 5, 3, 10, 70),  # 10月
        (9, 5, 3, 11, 82),  # 11月（12点向上）
    ]
    
    for grade in test_grades:
        cursor.execute('''
            INSERT OR IGNORE INTO elementary_grades (student_id, grade_year, subject, month, score) 
            VALUES (?, ?, ?, ?, ?)
        ''', grade)
    
    conn.commit()
    conn.close()
    
    print(f"SQLiteテストデータベースを作成しました: {db_path}")
    return db_path

if __name__ == '__main__':
    setup_sqlite_database()
