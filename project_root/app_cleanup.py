#!/usr/local/bin/python
# -*- coding: utf-8 -*-

# 基本的なインポート
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
import os
import sys
import logging
import json
import pymysql
import io
import csv

# Flaskとデータベース関連のインポート
from flask import Flask, redirect, request, session, render_template, jsonify, url_for
from pymysql.cursors import DictCursor

# ロギング設定
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except Exception as e:
        print(f"Failed to create log directory: {e}", file=sys.stderr)

# Flaskアプリケーション設定
template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_folder)
app.secret_key = 'test_key'  # テスト用のシークレットキー

# app.py またはメインルーティングファイルに以下を追加
try:
    from improvement_notifications import improvement_notifications
    app.register_blueprint(improvement_notifications)
except ImportError:
    # モジュールがない場合はスキップ
    pass

# ロガーの設定
try:
    handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=1024 * 1024,        backupCount=3
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('アプリケーション起動')
except Exception as e:
    # ロギング設定に失敗した場合も続行
    pass

# config モジュールのインポート
try:
    from config import Config
except ImportError:
    class Config:
        MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
        MYSQL_USER = os.getenv('MYSQL_USER', 'root')
        MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
        MYSQL_DB = os.getenv('MYSQL_DB', 'test')
        MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
        GOOGLE_CALENDAR_API_KEY = os.getenv('GOOGLE_CALENDAR_API_KEY', '')
        GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', '')

# MySQL 接続設定
app.config.update(
    MYSQL_HOST=Config.MYSQL_HOST,
    MYSQL_USER=Config.MYSQL_USER,
    MYSQL_PASSWORD=Config.MYSQL_PASSWORD,
    MYSQL_DB=Config.MYSQL_DB,
    MYSQL_PORT=Config.MYSQL_PORT,
)

# Google Calendar API の設定
app.config.update(
    GOOGLE_CALENDAR_API_KEY=Config.GOOGLE_CALENDAR_API_KEY,
    GOOGLE_CALENDAR_ID=Config.GOOGLE_CALENDAR_ID
)

# ポイント管理ユーティリティをインポート
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
try:
    from points_utils import (
        get_user_total_points, award_points, consume_points, get_point_history,
        cancel_point_history, process_login_and_award_points, update_login_streak,
        check_and_award_streak_bonus, calculate_monthly_attendance_rate,
        check_and_award_attendance_bonus, check_and_award_birthday_bonus,
        check_grade_improvement_bonus, get_crane_game_prizes,
        redeem_crane_game_prize, update_user_birthday, teacher_award_points
    )
except ImportError:
    # モジュールがない場合はダミー関数を定義
    def get_user_total_points(conn, user_id): return 0
    def award_points(*args, **kwargs): return (False, "Not implemented")
    def consume_points(*args, **kwargs): return (False, "Not implemented")
    def get_point_history(*args, **kwargs): return []
    def cancel_point_history(*args, **kwargs): return (False, "Not implemented")
    def process_login_and_award_points(*args, **kwargs): return None
    def update_login_streak(*args, **kwargs): return 0
    def check_and_award_streak_bonus(*args, **kwargs): return (0, "")
    def calculate_monthly_attendance_rate(*args, **kwargs): return 0
    def check_and_award_attendance_bonus(*args, **kwargs): return (0, "")
    def check_and_award_birthday_bonus(*args, **kwargs): return (0, "")
    def check_grade_improvement_bonus(*args, **kwargs): return (0, "")
    def get_crane_game_prizes(*args, **kwargs): return []
    def redeem_crane_game_prize(*args, **kwargs): return (False, "Not implemented")
    def update_user_birthday(*args, **kwargs): return (False, "Not implemented")
    def teacher_award_points(*args, **kwargs): return (False, "Not implemented")

# 模試管理ユーティリティをインポート
try:
    from mock_exam_utils import (
        save_mock_exam_score, get_mock_exam_scores, delete_mock_exam_score
    )
except ImportError:
    # モジュールがない場合はダミー関数を定義
    def save_mock_exam_score(*args, **kwargs): return (False, "Not implemented")
    def get_mock_exam_scores(*args, **kwargs): return []
    def delete_mock_exam_score(*args, **kwargs): return (False, "Not implemented")

# 成績・内申点向上通知管理ユーティリティをインポート
try:
    from improvement_notification_manager import (
        get_all_improvement_notifications, get_notification_counts, process_notification, ensure_notification_tables
    )
except ImportError:
    # モジュールがない場合はダミー関数を定義
    def get_all_improvement_notifications(*args, **kwargs): return []
    def get_notification_counts(*args, **kwargs): return {"total": 0, "unprocessed": 0}
    def process_notification(*args, **kwargs): return (False, "Not implemented")
    def ensure_notification_tables(*args, **kwargs): pass

# HOPE ROOM関連ユーティリティをインポート
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)  # 現在のディレクトリをPythonパスに追加
try:
    from hope_room_utils import get_hope_room_credentials, save_hope_room_credentials, ensure_external_service_credentials_table
except ImportError:
    # モジュールがない場合はダミー関数を定義
    def get_hope_room_credentials(*args, **kwargs): return None
    def save_hope_room_credentials(*args, **kwargs): return (False, "Not implemented")
    def ensure_external_service_credentials_table(*args, **kwargs): pass

# Global variables
_is_initialized = False

# データベース接続関数
def get_db_connection():
    """データベース接続を取得する関数"""
    return pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB'],
        port=app.config['MYSQL_PORT'],
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=True
    )

# エラーログ出力関数
def log_error(message):
    """エラーメッセージをログに出力する関数"""
    try:
        app.logger.error(message)
    except:
        pass
    
    # stderr にも出力
    print(message, file=sys.stderr)

# Google Calendarからイベントを取得する関数
def get_google_calendar_events():
    """Google Calendarからイベントを取得する関数"""
    try:
        # Google Calendar APIから予定を取得する実装
        pass
    except Exception as e:
        log_error(f"Error fetching Google Calendar events: {e}")
        return []

# テーブル作成確認関数をまとめる
def create_subjects_table(conn):
    """subjects テーブルを作成する"""
    try:
        with conn.cursor() as cur:
            # テーブル作成の実装
            pass
    except Exception as e:
        log_error(f"Error creating subjects table: {e}")

def create_internal_points_table(conn):
    """internal_points テーブルを作成する"""
    try:
        with conn.cursor() as cur:
            # テーブル作成の実装
            pass
    except Exception as e:
        log_error(f"Error creating internal_points table: {e}")

def create_class_schedule_master_table(conn):
    """学年別曜日設定テーブルを作成する"""
    try:
        with conn.cursor() as cur:
            # テーブル作成の実装
            pass
    except Exception as e:
        log_error(f"Error creating class_schedule_master table: {e}")

def add_attendance_day_column_to_users(conn):
    """usersテーブルに attendance_days 列を追加"""
    try:
        with conn.cursor() as cur:
            # カラムが存在するかチェック
            cur.execute("SHOW COLUMNS FROM users LIKE 'attendance_days'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN attendance_days INT DEFAULT 0")
                app.logger.info("attendance_days column added to users table")
    except Exception as e:
        log_error(f"Error adding attendance_days column: {e}")

def ensure_elementary_grades_table(conn):
    """小学生用成績テーブルを確認・作成する"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS elementary_grades (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    grade_year INT NOT NULL,
                    subject_name VARCHAR(100) NOT NULL,
                    score INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            app.logger.info("elementary_grades table ensured")
    except Exception as e:
        log_error(f"Error creating elementary_grades table: {e}")

def ensure_monthly_test_comments_table(conn):
    """テスト成績のコメント用テーブルを確認・作成する"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS monthly_test_comments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    grade_year INT NOT NULL,
                    term INT NOT NULL,
                    subject_id INT NOT NULL,
                    comment TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
                )
            """)
            app.logger.info("monthly_test_comments table ensured")
    except Exception as e:
        log_error(f"Error creating monthly_test_comments table: {e}")

# 英検単語関連の機能は削除されました

def create_event_types_table(conn):
    """point_event_typesテーブルを作成する"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS point_event_types (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    event_name VARCHAR(100) NOT NULL UNIQUE,
                    points_awarded INT NOT NULL DEFAULT 0,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            app.logger.info("point_event_types table ensured")
    except Exception as e:
        log_error(f"Error creating event_types table: {e}")

def insert_default_event_types(conn):
    """デフォルトのイベントタイプを挿入する"""
    try:
        with conn.cursor() as cur:
            default_events = [
                ('ログイン', 5, '毎日のログインボーナス'),
                ('宿題完了', 10, '宿題を期限内に完了'),
                ('テスト向上', 20, 'テスト成績が向上した場合'),
                ('皆勤賞', 50, '月間皆勤達成'),
                ('誕生日', 100, '誕生日ボーナス'),
                ('特別賞', 30, '講師が特別に認めた場合')
            ]
            
            for event_name, points, description in default_events:
                cur.execute("""
                    INSERT IGNORE INTO point_event_types (event_name, points_awarded, description)
                    VALUES (%s, %s, %s)
                """, (event_name, points, description))
            
            app.logger.info("Default event types inserted")
    except Exception as e:
        log_error(f"Error inserting default event types: {e}")

# 内申点合計計算関数
def calculate_current_internal_points(user_id):
    """生徒の現在の内申点合計を計算する（2年生3学期 + 3年生2学期×2）- 最終修正版"""
    conn = get_db_connection()
    result = {
        'total': 0,
        'details': [],
        'second_year_points': [],
        'third_year_points': [],
        'calculation_method': '2年生3学期 + 3年生2学期×2'
    }
    
    try:
        # 内申点計算ロジックの実装
        pass
    except Exception as e:
        log_error(f"Error calculating internal points: {e}")
    finally:
        conn.close()
    
    return result

# テスト用のサンプル通知生成関数
def generate_sample_notifications():
    """サンプルの成績向上通知を生成する（テスト用）"""
    current_time = datetime.now()
    one_day_ago = current_time - timedelta(days=1)
    two_days_ago = current_time - timedelta(days=2)
    one_hour_ago = current_time - timedelta(hours=1)
    
    return [
        {
            'id': 1,
            'student_id': 7,
            'student_name': 'テスト生徒A',
            'grade_year': 3,
            'subject_id': 2,
            'subject_name': '数学',
            'term': 2,
            'previous_score': 65,
            'new_score': 85,
            'improvement_level': '大',
            'potential_points': 50,
            'is_processed': 0,
            'processed_by': None,
            'processed_at': None,
            'teacher_name': None,
            'created_at': one_hour_ago
        },
        {
            'id': 2,
            'student_id': 8,
            'student_name': 'テスト生徒B',
            'grade_year': 2,
            'subject_id': 1,
            'subject_name': '国語',
            'term': 1,
            'previous_score': 72,
            'new_score': 82,
            'improvement_level': '中',
            'potential_points': 30,
            'is_processed': 0,
            'processed_by': None,
            'processed_at': None,
            'teacher_name': None,
            'created_at': one_day_ago
        },
        {
            'id': 3,
            'student_id': 9,
            'student_name': 'テスト生徒C',
            'grade_year': 1,
            'subject_id': 3,
            'subject_name': '英語',
            'term': 3,
            'previous_score': 55,
            'new_score': 62,
            'improvement_level': '小',
            'potential_points': 20,
            'is_processed': 1,
            'processed_by': 1,
            'processed_at': two_days_ago,
            'teacher_name': '講師A',
            'created_at': two_days_ago - timedelta(hours=2)
        }
    ]

# テスト用のサンプル通知生成関数
def generate_sample_improvement_notifications():
    """サンプルの成績・内申向上通知を生成する（テスト用）"""
    current_time = datetime.now()
    one_day_ago = current_time - timedelta(days=1)
    two_days_ago = current_time - timedelta(days=2)
    one_hour_ago = current_time - timedelta(hours=1)
    
    return [
        {
            'id': 1,
            'student_id': 7,
            'student_name': 'テスト生徒A',
            'student_type': 'elementary',
            'grade_year': 3,
            'subject_id': 2,
            'subject_name': '算数',
            'term': 2,
            'previous_score': 65,
            'new_score': 85,
            'improvement_level': '大',
            'potential_points': 50,
            'is_processed': 0,
            'processed_by': None,
            'processed_at': None,
            'teacher_name': None,
            'term_display': '3年2学期',
            'notification_text': '算数の成績が65点から85点に向上しました',
            'created_at': one_hour_ago
        },
        {
            'id': 2,
            'student_id': 8,
            'student_name': 'テスト生徒B',
            'student_type': 'middle',
            'grade_year': 7,
            'subject_id': 1,
            'subject_name': '国語',
            'term': 1,
            'previous_point': 3,
            'new_point': 4,
            'improvement_level': '小',
            'potential_points': 20,
            'is_processed': 0,
            'processed_by': None,
            'processed_at': None,
            'teacher_name': None,
            'term_display': '7年1学期',
            'notification_text': '国語の内申点が3から4に向上しました',
            'created_at': one_day_ago
        },
        {
            'id': 3,
            'student_id': 9,
            'student_name': 'テスト生徒C',
            'student_type': 'middle',
            'grade_year': 9,
            'subject_id': 3,
            'subject_name': '英語',
            'term': 3,
            'previous_score': 55,
            'new_score': 75,
            'improvement_level': '大',
            'potential_points': 50,
            'is_processed': 1,
            'processed_by': 1,
            'processed_at': two_days_ago,
            'teacher_name': '講師A',
            'term_display': '9年3学期',
            'notification_text': '英語の成績が55点から75点に向上しました',
            'created_at': two_days_ago - timedelta(hours=2)
        }
    ]

@app.before_request
def initialize_on_first_request():
    # リクエスト前処理の実装
    pass

@app.route('/')
def index():
    # トップページの実装
    pass

@app.route('/login', methods=['GET', 'POST'])
def login():
    # ログイン処理の実装
    pass

@app.route('/student/dashboard')
def student_dashboard():
    # 生徒ダッシュボードの実装
    pass

@app.route('/student/profile', methods=['GET', 'POST'])
def student_profile():
    # 生徒プロフィールの実装
    pass

@app.route('/student/performance')
@app.route('/student/performance/<int:year>')
def student_performance(year=None):
    # 生徒成績表示の実装
    pass

@app.route('/teacher/dashboard')
def teacher_dashboard():
    # 講師ダッシュボードの実装
    pass

@app.route('/teacher/student-access-token/<int:student_id>')
def generate_student_access_token(student_id):
    # 生徒アクセストークン生成の実装
    pass

@app.route('/auth/student-access/<int:student_id>')
def student_access_with_id(student_id):
    # 生徒ID認証の実装
    pass

@app.route('/teacher/student-view/<int:student_id>')
def teacher_student_view(student_id):
    # 講師による生徒表示の実装
    pass

@app.route('/teacher/login-as-student/<int:student_id>')
def teacher_login_as_student(student_id):
    # 講師による生徒ログインの実装
    pass

@app.route('/student/return-to-teacher')
def return_to_teacher():
    # 講師に戻る機能の実装
    pass

@app.route('/hope_room_settings', methods=['GET', 'POST'])
def hope_room_settings():
    # HOPE ROOM設定の実装
    pass

@app.route('/hope-room')
def hope_room_info():
    # HOPE ROOMの情報表示の実装
    pass

@app.route('/myetr')
def myetr_info():
    # myETRの情報表示の実装
    pass

# API関連のエンドポイント
@app.route('/api/student/grades')
def get_student_grades():
    # 生徒成績API実装
    pass

def get_elementary_grades(conn, student_id, grade_year):
    """小学生の成績データを取得する"""
    try:
        # 小学生成績取得の実装
        pass
    except Exception as e:
        log_error(f"Error getting elementary grades: {e}")
        return []

def get_middle_high_grades(conn, student_id, grade_year):
    """中学生・高校生の成績データを取得する（元のロジック）"""
    try:
        # 中高生成績取得の実装
        pass
    except Exception as e:
        log_error(f"Error getting middle/high grades: {e}")
        return []

@app.route('/api/student/update-grade', methods=['POST'])
def update_student_grade():
    # 生徒成績更新API実装
    pass

@app.route('/api/student/update-internal-point', methods=['POST'])
def update_student_internal_point():
    # 内申点更新API実装
    pass

@app.route('/api/student/preferences')
def get_student_preferences():
    # 生徒設定取得API実装
    pass

@app.route('/api/calendar-events')
def calendar_events():
    # カレンダーイベント取得API実装
    pass

@app.route('/api/eiken-schedule')
def eiken_schedule_api():
    # 英検スケジュールAPI実装
    pass

@app.route('/logout')
def logout():
    # ログアウト処理実装
    pass

# CSVファイルから高校情報をインポートする関数
def import_high_schools_from_csv(file_content, year, user_id):
    """CSVファイルから高校情報をインポートする関数"""
    try:
        # 高校情報インポート実装
        pass
    except Exception as e:
        log_error(f"Error importing high schools: {e}")
        return {"success": False, "message": str(e)}

# 内申点テーブルを作成する関数
def create_internal_points_table(conn):
    """internal_points テーブルを作成する"""
    try:
        with conn.cursor() as cur:
            # テーブル作成の実装
            pass
    except Exception as e:
        log_error(f"Error creating internal points table: {e}")

# 内申点合計計算関数
def calculate_current_internal_points(user_id):
    """生徒の現在の内申点合計を計算する（2年生3学期 + 3年生2学期×2）- 最終修正版"""
    conn = get_db_connection()
    result = {
        'total': 0,
        'details': [],
        'second_year_points': [],
        'third_year_points': [],
        'calculation_method': '2年生3学期 + 3年生2学期×2'
    }
    
    try:
        # 内申点計算ロジックの実装
        pass
    except Exception as e:
        log_error(f"Error calculating internal points: {e}")
    finally:
        conn.close()
    
    return result

# 科目テーブルを作成する関数
def create_subjects_table(conn):
    """subjects テーブルを作成する"""
    try:
        with conn.cursor() as cur:
            # テーブル作成の実装
            pass
    except Exception as e:
        log_error(f"Error creating subjects table: {e}")

@app.route('/student/high-schools')
def student_high_schools():
    # 生徒用高校リストの実装
    pass

@app.route('/student/high-school/<int:school_id>')
def student_high_school_detail(school_id):
    # 生徒用高校詳細の実装
    pass

@app.route('/student/points')
def student_points():
    # 生徒ポイント表示の実装
    pass

@app.route('/student/crane-game')
def student_crane_game():
    # クレーンゲーム実装
    pass

# クレジット使用処理API
@app.route('/api/teacher/use-crane-game-credit', methods=['POST'])
def use_crane_game_credit():
    # クレジット使用API実装
    pass

# クレーンゲームプレイ権取得API
@app.route('/api/student/get-crane-game-credit', methods=['POST'])
def get_crane_game_credit():
    # プレイ権取得API実装
    pass

# 講師用のクレーンゲームプレイ権管理画面
@app.route('/teacher/crane-game-credits')
def teacher_crane_game_credits():
    # プレイ権管理画面実装
    pass

# クレーンゲーム景品交換API
@app.route('/api/student/redeem-prize', methods=['POST'])
def redeem_prize():
    # 景品交換API実装
    pass

# イベントタイプテーブルを作成する関数
def create_event_types_table(conn):
    """point_event_typesテーブルを作成する"""
    try:
        with conn.cursor() as cur:
            # テーブル作成の実装
            pass
    except Exception as e:
        log_error(f"Error creating event types table: {e}")

# デフォルトのイベントタイプを挿入する関数
def insert_default_event_types(conn):
    """デフォルトのイベントタイプを挿入する"""
    try:
        with conn.cursor() as cur:
            # イベントタイプ挿入の実装
            pass
    except Exception as e:
        log_error(f"Error inserting default event types: {e}")

@app.route('/teacher/points', methods=['GET', 'POST'])
def teacher_points():
    # 講師ポイント管理実装
    pass

@app.route('/api/student/points')
def get_student_points_api():
    # 生徒ポイント取得API実装
    pass

@app.route('/debug/event-types')
def debug_event_types():
    # イベントタイプデバッグ実装
    pass

# イベントタイプのデータを挿入・更新するエンドポイント
@app.route('/admin/reset-event-types')
def reset_event_types():
    # イベントタイプリセット実装
    pass

# 内部サーバーエラーのハンドラー
@app.errorhandler(500)
def internal_error(error):
    # エラーハンドラー実装
    pass

# 特定の高校情報をデバッグ表示するルート
@app.route('/debug/high-school/<int:school_id>')
def debug_high_school(school_id):
    # 高校デバッグ実装
    pass

@app.route('/direct/high-school/<int:school_id>')
def direct_high_school_detail(school_id):
    # 高校直接アクセス実装
    pass

# 超基本的なテスト用ルート（テンプレートもDBも使わないバージョン）

@app.route('/test/basic')
def test_basic():
    # 基本テスト実装
    return "Basic test route is working!"

@app.route('/test/session')
def test_session():
    # セッションテスト実装
    session['test'] = 'test value'
    return "Session test complete"

@app.route('/test/db')
def test_db():
    # DB接続テスト実装
    try:
        conn = get_db_connection()
        conn.close()
        return "Database connection successful"
    except Exception as e:
        return f"Database connection error: {str(e)}"

@app.route('/test/high-schools')
def test_high_schools():
    # 高校テスト実装
    return "High schools test"

@app.route('/test/direct')
def test_direct():
    # 直接レスポンステスト実装
    return "Direct response test"

@app.route('/test/log-error')
def test_log_error():
    # エラーログテスト実装
    log_error("Test error log")
    return "Error log test complete"

# データベース修復スクリプト
@app.route('/admin/db-repair')
def db_repair():
    # DB修復実装
    pass

@app.route('/student/points-basic')
def student_points_basic():
    # 基本ポイント実装
    pass

@app.route('/student/crane-game-basic')
def student_crane_game_basic():
    # 基本クレーンゲーム実装
    pass

@app.route('/api/teacher/notification-count')
def teacher_notification_count():
    # 通知カウント実装
    pass

# 成績向上通知ページ
@app.route('/teacher/grade-notifications', methods=['GET', 'POST'])
def teacher_grade_notifications():
    # 成績向上通知実装
    pass

# 出席管理ページ
@app.route('/teacher/attendance', methods=['GET', 'POST'])
def teacher_attendance():
    # 出席管理実装
    pass

# 模試点数取得API
@app.route('/api/teacher/mock-exam-scores', methods=['GET'])
def get_teacher_mock_exam_scores():
    # 模試点数取得API実装
    pass

# 模試点数保存API
@app.route('/api/teacher/mock-exam-score', methods=['POST'])
def save_teacher_mock_exam_score():
    # 模試点数保存API実装
    pass

# 模試点数削除API
@app.route('/api/teacher/mock-exam-score/<int:score_id>', methods=['DELETE'])
def delete_teacher_mock_exam_score(score_id):
    """模試の点数を削除するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    teacher_id = session.get('user_id')
    
    try:
        # 削除処理の実装
        pass
    except Exception as e:
        log_error(f"Error deleting mock exam score: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# 成績・内申向上通知ページ
@app.route('/teacher/improvement-notifications', methods=['GET', 'POST'])
def teacher_improvement_notifications():
    """講師用の成績・内申点向上通知ページ（統合版）"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    teacher_id = session.get('user_id')
    error = None
    success = None
    
    # POSTリクエスト処理（ポイント付与）
    if request.method == 'POST':
        # ポイント付与処理の実装
        pass
    
    # 全ての通知を取得
    notifications = []
    unprocessed_count = 0
    
    try:
        # 通知取得処理の実装
        pass
    except Exception as e:
        error = f"通知の取得に失敗しました: {str(e)}"
    
    # データがない場合はテスト用データ生成
    if not notifications:
        notifications = generate_sample_improvement_notifications()
        unprocessed_count = 2
    
    return render_template(
        'teacher_improvement_notifications.html',
        name=session.get('user_name', ''),
        notifications=notifications,
        unprocessed_count=unprocessed_count,
        error=error,
        success=success
    )

# API: 未処理の通知数を取得
@app.route('/api/teacher/improvement-notification-count')
def improvement_notification_count():
    """未処理の成績・内申向上通知数を取得するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    try:
        # 通知カウント取得処理の実装
        pass
    except Exception as e:
        log_error(f"Error getting notification count: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# 小学生模試点数管理ページ
@app.route('/teacher/manual-score', methods=['GET', 'POST'])
def teacher_manual_score():
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    students = []
    
    try:
        # 生徒リスト取得処理の実装
        pass
    except Exception as e:
        log_error(f"Error in teacher_manual_score: {e}")
    finally:
        pass
    
    # テンプレート名が正しいか確認
    return render_template('teacher_mock_exam.html', 
                          name=session.get('user_name', ''),
                          students=students)

@app.route('/api/teacher/students')
def get_teacher_students():
    """生徒データと出席情報を取得するAPI - 改善版"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    # フィルターパラメータ
    grade = request.args.get('grade', 'all')
    day = request.args.get('day')  # 曜日フィルター
    grade_level = request.args.get('grade_level')  # 詳細な学年レベル
    school_type = request.args.get('school_type')  # 学校種別
    student_id = request.args.get('student_id')  # 個別生徒ID
    
    try:
        # 生徒リスト取得処理の実装
        return jsonify({'success': True, 'students': []})
    except Exception as e:
        log_error(f"Error getting teacher students: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# app.pyに追加するAPIデバッグ用エンドポイント

@app.route('/api/debug/info')
def api_debug_info():
    """APIデバッグ情報を返すエンドポイント"""
    # 基本情報を収集
    debug_info = {
        'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'app_root': os.path.dirname(os.path.abspath(__file__)),
        'python_version': sys.version,
        'routes': [],
        'session': {},
        'request': {
            'path': request.path,
            'method': request.method,
            'headers': dict(request.headers),
            'args': dict(request.args),
        }
    }
    
    # セッション情報（セキュリティ上重要な情報は除く）
    if session:
        # セッション処理の実装
        pass
    
    # 登録されているルート情報
    for rule in app.url_map.iter_rules():
        # ルート情報処理の実装
        pass
    
    # データベース���続テスト
    db_status = {'connected': False, 'message': ''}
    try:
        # DB接続テストの実装
        pass
    except Exception as e:
        db_status['message'] = str(e)
    
    debug_info['database'] = db_status
    
    return jsonify(debug_info)

@app.route('/api/debug/test-query')
def api_debug_test_query():
    """APIデバッグ用にテストクエリを実行するエンドポイント"""
    query = request.args.get('query')
    params_str = request.args.get('params', '[]')
    
    if not query:
        return jsonify({'success': False, 'message': 'クエリが指定されていません'}), 400
    
    try:
        # テストクエリ実行処理の実装
        pass
    except Exception as e:
        log_error(f"Error in test query: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/teacher/attendance', methods=['POST'])
def update_student_attendance():
    """生徒の出席状況を更新するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    teacher_id = session.get('user_id')
    data = request.json
    
    if not data or 'attendance_records' not in data:
        return jsonify({'success': False, 'message': 'データが送信されていません'}), 400
    
    try:
        # 出席更新処理の実装
        pass
    except Exception as e:
        log_error(f"Error updating attendance: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# app.pyに追加
@app.route('/api/teacher/class-schedule', methods=['GET', 'POST'])
def manage_class_schedule():
    """学年別曜日設定の取得・更新API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    # GETリクエスト: 設定取得
    if request.method == 'GET':
        # 設定取得処理の実装
        pass
    else:
        # 設定更新処理の実装
        pass

# 生徒の出席曜日を更新するAPI - 追加
@app.route('/api/teacher/update-student-attendance-days', methods=['POST'])
def update_student_attendance_days():
    """生徒の出席曜日設定を更新するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'データが送信されていません'}), 400
    
    student_id = data.get('student_id')
    attendance_days = data.get('attendance_days')  # "0,1,3,5" のような形式
    
    if not student_id:
        return jsonify({'success': False, 'message': '生徒IDが指定されていません'}), 400
    
    try:
        # 出席曜日更新処理の実装
        pass
    except Exception as e:
        log_error(f"Error updating student attendance days: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# テストコメント取得API
@app.route('/api/student/test-comments')
def get_test_comments():
    """生徒のテスト成績コメントを取得するAPI"""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    # クエリパラメータから生徒IDと年度を取得
    student_id = request.args.get('student_id', type=int)
    grade_year = request.args.get('grade_year', type=int)
    
    # ユーザーIDを決定
    if session.get('role') == 'teacher' and student_id:
        user_id = student_id
    else:
        user_id = session.get('user_id')
    
    # 年度が指定されていない場合は現在の学年を使用
    if not grade_year:
        # 現在の学年を取得
        pass
    
    try:
        conn = get_db_connection()
        
        # テーブルの存在確認
        ensure_monthly_test_comments_table(conn)
        
        # コメントデータを取得
        with conn.cursor() as cur:
            # データ取得処理の実装
            pass
        
        # 科目と月ごとのコメントを整理
        result = {}
        for row in comments:
            # データ整理処理の実装
            pass
        
        conn.close()
        return jsonify({
            'success': True,
            'comments': result
        })
    
    except Exception as e:
        log_error(f"Error getting test comments: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# テストコメント更新API
@app.route('/api/student/update-test-comment', methods=['POST'])
def update_test_comment():
    """テスト成績のコメントを更新するAPI"""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'データが送信されていません'}), 400
    
    student_id = data.get('student_id')
    grade_year = data.get('grade_year')
    subject_id = data.get('subject_id')
    month = data.get('month')
    comment = data.get('comment', '')
    
    # 必要なパラメータが揃っているか確認
    if not all([student_id, grade_year, subject_id, month]):
        return jsonify({'success': False, 'message': '必要なパラメータが不足しています'}), 400
    
    # アクセス権チェック - 自分自身または講師のみ編集可能
    if int(student_id) != int(session.get('user_id')) and session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '権限がありません'}), 403
    
    try:
        conn = get_db_connection()
        
        # テーブルの存在確認
        ensure_monthly_test_comments_table(conn)
        
        with conn.cursor() as cur:
            # コメント更新処理の実装
            pass
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'comment_id': comment_id,
            'message': 'コメントを保存しました'
        })
    
    except Exception as e:
        log_error(f"Error updating test comment: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/student/update-elementary-grade', methods=['POST'])
def update_elementary_grade():
    """小学生の成績データを更新するAPI"""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
        
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'データが送信されていません'}), 400
    
    student_id = data.get('student_id')
    grade_year = data.get('grade_year')
    subject_id = data.get('subject_id')
    month = data.get('month')
    score = data.get('score')
    comment = data.get('comment', '')
    grade_id = data.get('grade_id')  # 既存の成績の場合はID
    
    if not all([student_id, grade_year, subject_id, month]) or score is None:
        return jsonify({'success': False, 'message': '必要なパラメータが不足しています'}), 400
    
    # 権限チェック - 自分自身または講師のみ編集可能
    if int(student_id) != int(session.get('user_id')) and session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '権限がありません'}), 403
    
    try:
        conn = get_db_connection()
        
        # テーブルの存在確認
        ensure_elementary_grades_table(conn)
        
        with conn.cursor() as cur:
            # 成績更新処理の実装
            pass
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'grade_id': grade_id,
            'message': '成績を保存しました'
        })
    
    except Exception as e:
        log_error(f"Error updating elementary grade: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/teacher/improved-students')
def get_improved_students():
    """成績向上生徒データ取得API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    # クエリパラメータの取得
    school_type = request.args.get('type', 'elementary')
    
    try:
        conn = get_db_connection()
        
        if school_type == 'elementary':
            # 小学生データ取得
            pass
        else:
            # 中高生データ取得
            pass
        
        conn.close()
        
        return jsonify({'success': True, 'students': students})
        
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        log_error(f"Error fetching improved students: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/teacher/award-improvement-points', methods=['POST'])
def api_award_improvement_points():
    """成績向上ポイントを付与するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    teacher_id = session.get('user_id')
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'message': 'データが送信されていません'}), 400
    
    try:
        student_id = data.get('student_id')
        points = data.get('points')
        event_type = data.get('event_type')
        comment = data.get('comment')
        subject_id = data.get('subject_id')
        
        if not all([student_id, points, event_type]):
            return jsonify({'success': False, 'message': '必要なパラメータが不足しています'}), 400
        
        conn = get_db_connection()
        
        # ポイント付与実行
        success, message = teacher_award_points(
            conn,
            teacher_id,
            student_id,
            event_type,
            points,
            comment
        )
        
        conn.close()
        
        return jsonify({
            'success': success,
            'message': message,
            'points': points,
            'student_id': student_id
        })
    
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        log_error(f"Error in award_improvement_points: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# フロントエンド用デバッグツール
@app.route('/debug/api-tester')
def debug_api_tester():
    # API テスターの実装
    pass

if __name__ == '__main__':
    app.run(debug=True)
