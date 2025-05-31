#!/usr/local/bin/python
# -*- coding: utf-8 -*-

# 基本的なインポート
import os
import sys
import traceback
from datetime import datetime, timedelta
import json
import logging
from logging.handlers import RotatingFileHandler
import random
import time

# Flaskとデータベース関連のインポート
from flask import Flask, redirect, request, session, render_template, jsonify, url_for
import pymysql
from pymysql.cursors import DictCursor
import requests

# ロギング設定
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except Exception as e:
        pass  # ログディレクトリが作成できない場合はスキップ

# .envファイルを読み込む
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenvがない場合はスキップ

# 設定をインポート
try:
    from config import Config
except ImportError:
    # config.pyがない場合のフォールバック
    class Config:
        SECRET_KEY = os.getenv('SECRET_KEY', 'test_key')
        MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql3103.db.sakura.ne.jp')
        MYSQL_USER = os.getenv('MYSQL_USER', 'seishinn')
        MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'Yakyuubu8')
        MYSQL_DB = os.getenv('MYSQL_DB', 'seishinn_test')
        MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
        GOOGLE_CALENDAR_API_KEY = os.getenv('GOOGLE_CALENDAR_API_KEY', 'AIzaSyDtVSN3bin_JorxBjC3K88ofmR8vL88n6I')
        GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'seishinn.juku@gmail.com')

# Flaskアプリケーション設定
template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_folder)
app.secret_key = Config.SECRET_KEY

# improvement_notifications モジュールは現在使用されていないため、コメントアウト
# try:
#     from improvement_notifications import improvement_notifications
#     app.register_blueprint(improvement_notifications)
# except ImportError:
#     # モジュールがない場合はスキップ
#     pass

# ロガーの設定
try:
    handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=1024 * 1024,  # 1MB
        backupCount=3
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

# テンプレートでグローバルに利用可能な変数を提供するコンテキストプロセッサ
@app.context_processor
def inject_template_globals():
    """テンプレートにグローバル変数を提供する"""
    # リクエストURLから講師ビューモードを検出
    teacher_view = False
    if request.args.get('teacher_view') == 'true':
        teacher_view = True
    
    # セッションから講師ログインフラグを取得
    is_teacher_login = session.get('is_teacher_login', False)
    viewing_student_name = None
    original_teacher_name = None
    
    # 講師が生徒としてログインしている場合の情報を取得
    if is_teacher_login:
        # セッション内の生徒名を確実に取得
        viewing_student_name = session.get('viewing_student_name', '')
        if not viewing_student_name:
            # 表示名が未設定の場合、user_nameをバックアップとして使用
            viewing_student_name = session.get('user_name', '')
            app.logger.warning(f"[緊急] 生徒表示名が未設定のため、user_name({viewing_student_name})を使用します")
        
        # 講師名も確実に取得
        original_teacher_name = session.get('original_teacher_name', '')
        
        # セッションに名前を確実に設定し直す
        session['viewing_student_name'] = viewing_student_name
        session['original_teacher_name'] = original_teacher_name
        session.modified = True
        
        app.logger.warning(f"[重要] コンテキスト処理: is_teacher_login={is_teacher_login}")
        app.logger.warning(f"[重要] 生徒名: viewing_student_name={viewing_student_name}")
        app.logger.warning(f"[重要] 講師名: original_teacher_name={original_teacher_name}")
        app.logger.warning(f"[重要] コンテキスト全セッション: {dict(session)}")
        app.logger.warning(f"[重要] テンプレート変数: viewing_student_name={viewing_student_name}, original_teacher_name={original_teacher_name}")
    
    return {
        'teacher_view': teacher_view,
        'is_teacher_login': is_teacher_login,
        'viewing_student_name': viewing_student_name,
        'original_teacher_name': original_teacher_name
    }

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
    def award_points(*args, **kwargs): return (True, 0)
    def consume_points(*args, **kwargs): return (True, 0)
    def get_point_history(*args, **kwargs): return []
    def cancel_point_history(*args, **kwargs): return (True, "")
    def process_login_and_award_points(*args, **kwargs): return (False, 0)
    def update_login_streak(*args, **kwargs): return True
    def check_and_award_streak_bonus(*args, **kwargs): return (False, 0)
    def calculate_monthly_attendance_rate(*args, **kwargs): return 0
    def check_and_award_attendance_bonus(*args, **kwargs): return (False, 0)
    def check_and_award_birthday_bonus(*args, **kwargs): return (False, 0)
    def check_grade_improvement_bonus(*args, **kwargs): return (False, 0)
    def get_crane_game_prizes(*args, **kwargs): return []
    def redeem_crane_game_prize(*args, **kwargs): return (False, "")
    def update_user_birthday(*args, **kwargs): return (True, "")
    def teacher_award_points(*args, **kwargs): return (True, "")

# 模試管理ユーティリティをインポート
try:
    from mock_exam_utils import (
        save_mock_exam_score, get_mock_exam_scores, delete_mock_exam_score
    )
except ImportError:
    # モジュールがない場合はダミー関数を定義
    def save_mock_exam_score(*args, **kwargs): return (False, "")
    def get_mock_exam_scores(*args, **kwargs): return (False, "")
    def delete_mock_exam_score(*args, **kwargs): return (False, "")

# 成績・内申点向上通知管理ユーティリティをインポート
try:
    from improvement_notification_manager import (
        get_all_improvement_notifications, get_notification_counts, process_notification, ensure_notification_tables
    )
except ImportError:
    # モジュールがない場合はダミー関数を定義
    def get_all_improvement_notifications(*args, **kwargs): return []
    def get_notification_counts(*args, **kwargs): return {'elementary_count': 0, 'middle_count': 0, 'high_count': 0, 'internal_count': 0, 'total_count': 0}
    def process_notification(*args, **kwargs): return (False, "")
    def ensure_notification_tables(*args, **kwargs): pass

# HOPE ROOM関連ユーティリティをインポート
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)  # 現在のディレクトリをPythonパスに追加
try:
    from hope_room_utils import get_hope_room_credentials, save_hope_room_credentials, ensure_external_service_credentials_table
except ImportError:
    # モジュールがない場合はダミー関数を定義
    def get_hope_room_credentials(*args, **kwargs): return {'login_id': '', 'password': ''}
    def save_hope_room_credentials(*args, **kwargs): return False
    def ensure_external_service_credentials_table(*args, **kwargs): return False

# Global variables
_is_initialized = False

# データベース接続関数
def get_db_connection():
    """データベース接続を取得する関数"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            conn = pymysql.connect(
                host=app.config['MYSQL_HOST'],
                user=app.config['MYSQL_USER'],
                password=app.config['MYSQL_PASSWORD'],
                database=app.config['MYSQL_DB'],
                port=app.config['MYSQL_PORT'],
                charset='utf8mb4',
                cursorclass=DictCursor,
                autocommit=True,
                connect_timeout=10  # 接続タイムアウトを10秒に設定
            )
            # 接続テスト
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return conn
        except Exception as e:
            log_error(f"データベース接続試行 {attempt + 1}/{max_retries} 失敗: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise

# エラーログ出力関数
def log_error(message):
    """エラーメッセージをログに出力する関数"""
    try:
        app.logger.error(message)
    except:
        # ロギングに失敗しても続行
        pass
    
    # CGI環境ではstderrへの出力がレスポンスに混入する可能性があるため
    # ファイルロガーのみを使用

# Google Calendarからイベントを取得する関数
def get_google_calendar_events():
    """Google Calendarからイベントを取得する関数"""
    try:
        api_key = app.config['GOOGLE_CALENDAR_API_KEY']
        calendar_id = app.config['GOOGLE_CALENDAR_ID']
        
        if not api_key or not calendar_id:
            log_error("API Key or Calendar ID is not set")
            return None
        
        # Google Calendar APIのURL
        # calendar_idはURLエンコードする必要がある
        from urllib.parse import quote_plus
        calendar_id_encoded = quote_plus(calendar_id)
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id_encoded}/events"
        
        # 現在時刻を取得し、適切なフォーマットに変換
        now = datetime.now().isoformat() + "Z"  # RFC3339形式
        
        # 3か月先までのイベントを取得
        time_max = (datetime.now() + timedelta(days=90)).isoformat() + "Z"
        
        # APIリクエストのパラメータ
        params = {
            'key': api_key,
            'timeMin': now,
            'timeMax': time_max,
            'maxResults': 100,  # より多くのイベントを取得
            'singleEvents': 'true',
            'orderBy': 'startTime'
        }
        
        # APIリクエストを送信
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            events = []
            
            for item in data.get('items', []):
                event = {
                    'id': item.get('id', ''),
                    'title': item.get('summary', '無題のイベント'),
                }
                
                # 開始日時を取得
                start = item.get('start', {})
                if 'dateTime' in start:
                    event['start'] = start['dateTime']
                elif 'date' in start:
                    event['start'] = start['date']
                
                # 終了日時を取得
                end = item.get('end', {})
                if 'dateTime' in end:
                    event['end'] = end['dateTime']
                elif 'date' in end:
                    event['end'] = end['date']
                
                # 終日イベントかどうか
                if 'date' in start and 'date' in end:
                    event['allDay'] = True
                
                # 場所が設定されていれば追加
                if 'location' in item:
                    event['location'] = item['location']
                
                # 説明が設定されていれば追加
                if 'description' in item:
                    event['description'] = item['description']
                
                # イベントの色分け（カラーIDがあれば）
                colorId = item.get('colorId')
                if colorId:
                    colors = {
                        '1': '#7986cb',  # ラベンダー
                        '2': '#33b679',  # セージ
                        '3': '#8e24aa',  # ブドウ
                        '4': '#e67c73',  # フラミンゴ
                        '5': '#f6c026',  # バナナ
                        '6': '#f5511d',  # マンダリン
                        '7': '#039be5',  # ピーコック
                        '8': '#616161',  # グラファイト
                        '9': '#3f51b5',  # ブルーベリー
                        '10': '#0b8043', # バジル
                        '11': '#d60000', # トマト
                    }
                    if colorId in colors:
                        event['backgroundColor'] = colors[colorId]
                        event['borderColor'] = colors[colorId]
                
                events.append(event)
            
            return events
        else:
            log_error(f"Google Calendar API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        log_error(f"Google Calendar API Exception: {e}")
        return None

# テーブル作成確認関数をまとめる
def create_subjects_table(conn):
    """subjects テーブルを作成する"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    is_main TINYINT(1) NOT NULL DEFAULT 0,
                    display_order INT NOT NULL DEFAULT 0,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 基本データの挿入確認
            cur.execute("SELECT COUNT(*) as count FROM subjects")
            count = cur.fetchone()
            
            if count and count['count'] == 0:
                # 基本データの挿入
                cur.execute("""
                    INSERT INTO subjects (id, name, is_main, display_order) VALUES 
                    (1, '国語', 1, 1),
                    (2, '数学', 1, 2),
                    (3, '英語', 1, 3),
                    (4, '理科', 1, 4),
                    (5, '社会', 1, 5),
                    (6, '音楽', 0, 6),
                    (7, '美術', 0, 7),
                    (8, '体育', 0, 8),
                    (9, '技家', 0, 9)
                """)
            
            log_error("subjects テーブルを確認/作成しました")
            conn.commit()
    except Exception as e:
        log_error(f"Error creating subjects table: {e}")
        conn.rollback()

def create_internal_points_table(conn):
    """internal_points テーブルを作成する"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS internal_points (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    grade_year INT NOT NULL,
                    subject INT NOT NULL,
                    term INT NOT NULL,
                    point INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY(student_id, grade_year, subject, term),
                    INDEX(student_id, grade_year)
                )
            """)
            log_error("internal_points テーブルを確認/作成しました")
            conn.commit()
    except Exception as e:
        log_error(f"Error creating internal_points table: {e}")
        conn.rollback()

def create_class_schedule_master_table(conn):
    """学年別曜日設定テーブルを作成する"""
    try:
        with conn.cursor() as cur:
            # テーブル作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS class_schedule_master (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    grade_level INT NOT NULL,
                    school_type VARCHAR(20) NOT NULL,
                    day_of_week INT NOT NULL, 
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY(grade_level, school_type, day_of_week)
                )
            """)
            app.logger.info("class_schedule_masterテーブルを作成しました")
            conn.commit()
    except Exception as e:
        app.logger.error(f"Error creating class_schedule_master table: {e}")
        conn.rollback()

def add_attendance_day_column_to_users(conn):
    """usersテーブルに attendance_days 列を追加"""
    try:
        with conn.cursor() as cur:
            # カラムが存在するか確認
            cur.execute("SHOW COLUMNS FROM users LIKE 'attendance_days'")
            if not cur.fetchone():
                # カラムを追加
                cur.execute("""
                    ALTER TABLE users
                    ADD COLUMN attendance_days VARCHAR(20) NULL
                    COMMENT '出席曜日 (0,1,2,3,4,5,6 の形式で保存。0=日曜)'
                """)
                app.logger.info("usersテーブルに attendance_days カラムを追加しました")
            
            conn.commit()
    except Exception as e:
        app.logger.error(f"Error adding attendance_days column: {e}")
        conn.rollback()

def ensure_elementary_grades_table(conn):
    """小学生用成績テーブルを確認・作成する"""
    try:
        with conn.cursor() as cur:
            # テーブル作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS elementary_grades (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    grade_year INT NOT NULL,
                    subject INT NOT NULL,
                    month INT NOT NULL,
                    score INT NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_elementary_grade (student_id, grade_year, subject, month)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """)
            app.logger.info("elementary_grades テーブルを確認/作成しました")
            conn.commit()
    except Exception as e:
        app.logger.error(f"Error creating elementary_grades table: {e}")
        conn.rollback()

def ensure_monthly_test_comments_table(conn):
    """テスト成績のコメント用テーブルを確認・作成する"""
    try:
        with conn.cursor() as cur:
            # テーブル作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS monthly_test_comments (
                    id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    student_id int NOT NULL,
                    grade_year tinyint NOT NULL,
                    subject tinyint NOT NULL,
                    month tinyint NOT NULL,
                    comment text,
                    created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_comment (student_id, grade_year, subject, month)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """)
            app.logger.info("monthly_test_commentsテーブルを確認/作成しました")
            conn.commit()
    except Exception as e:
        app.logger.error(f"Error creating monthly_test_comments table: {e}")
        conn.rollback()

def ensure_eiken_words_table(conn):
    """英検単語テーブルを確認・作成する（改善版）"""
    try:
        with conn.cursor() as cur:
            # テーブル作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS eiken_words (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    grade VARCHAR(10) NOT NULL COMMENT '英検の級 (5, 4, 3, pre2, 2)',
                    question_id INT NOT NULL COMMENT '問題ID',
                    stage_number INT NOT NULL DEFAULT 1 COMMENT 'ステージ番号',
                    word VARCHAR(255) COMMENT '英単語（旧形式、後方互換性用）',
                    english VARCHAR(255) COMMENT '英単語',
                    japanese VARCHAR(255) COMMENT '日本語意味',
                    pronunciation VARCHAR(255) COMMENT '発音・意味',
                    audio_url VARCHAR(255) COMMENT '音声ファイルURL',
                    notes TEXT COMMENT '追加情報・メモ',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_grade_question (grade, question_id),
                    INDEX idx_grade_stage (grade, stage_number),
                    INDEX idx_word (word(20))
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """)
            
            # カラムの存在確認と追加（既存テーブルへの後方互換性対応）
            columns_to_check = [
                ('english', "ALTER TABLE eiken_words ADD COLUMN english VARCHAR(255) COMMENT '英単語' AFTER word"),
                ('japanese', "ALTER TABLE eiken_words ADD COLUMN japanese VARCHAR(255) COMMENT '日本語意味' AFTER english"),
                ('notes', "ALTER TABLE eiken_words ADD COLUMN notes TEXT COMMENT '追加情報・メモ' AFTER audio_url"),
                ('audio_url', "ALTER TABLE eiken_words ADD COLUMN audio_url VARCHAR(255) COMMENT '音声ファイルURL' AFTER pronunciation")
            ]
            
            for column_name, alter_sql in columns_to_check:
                try:
                    cur.execute(f"SHOW COLUMNS FROM eiken_words LIKE '{column_name}'")
                    if not cur.fetchone():
                        # 実際にカラムを追加
                        cur.execute(alter_sql)
                        log_error(f"eiken_words テーブルに {column_name} カラムを追加しました")
                except Exception as column_error:
                    log_error(f"カラム確認/追加エラー ({column_name}): {column_error}")
            
            # インデックスの確認と追加
            indices_to_check = [
                ('idx_grade_question', "CREATE INDEX idx_grade_question ON eiken_words (grade, question_id)"),
                ('idx_grade_stage', "CREATE INDEX idx_grade_stage ON eiken_words (grade, stage_number)"),
                ('idx_english', "CREATE INDEX idx_english ON eiken_words (english(20))"),
                ('idx_japanese', "CREATE INDEX idx_japanese ON eiken_words (japanese(20))")
            ]
            
            for index_name, create_index_sql in indices_to_check:
                try:
                    cur.execute(f"SHOW INDEX FROM eiken_words WHERE Key_name = '{index_name}'")
                    if not cur.fetchone():
                        # 実際にインデックスを作成
                        cur.execute(create_index_sql)
                        log_error(f"eiken_words テーブルに {index_name} インデックスを追加しました")
                except Exception as index_error:
                    log_error(f"インデックス確認/追加エラー ({index_name}): {index_error}")
            
            # 後方互換性対応：wordカラムからenglishカラムへデータ移行（wordカラムが存在する場合のみ）
            try:
                # まずwordカラムが存在するかチェック
                cur.execute("SHOW COLUMNS FROM eiken_words LIKE 'word'")
                if cur.fetchone():
                    # wordカラムの値をenglishカラムにコピー（englishが空の場合のみ）
                    cur.execute("""
                        UPDATE eiken_words SET english = word 
                        WHERE word IS NOT NULL AND word != '' AND (english IS NULL OR english = '')
                    """)
                    rows_affected = cur.rowcount
                    if rows_affected > 0:
                        log_error(f"wordカラムの値を{rows_affected}件、englishカラムに移行しました")
                else:
                    log_error("wordカラムは存在しないため、データ移行をスキップします")
                
                # pronunciationカラムの値をjapaneseカラムにコピー（japaneseが空の場合のみ）
                # ただし、japaneseカラムが存在し、かつ空の場合のみ
                cur.execute("SHOW COLUMNS FROM eiken_words LIKE 'japanese'")
                if cur.fetchone():
                    cur.execute("""
                        UPDATE eiken_words SET japanese = pronunciation 
                        WHERE pronunciation IS NOT NULL AND pronunciation != '' AND (japanese IS NULL OR japanese = '')
                    """)
                    rows_affected = cur.rowcount
                    if rows_affected > 0:
                        log_error(f"pronunciationカラムの値を{rows_affected}件、japaneseカラムに移行しました")
            except Exception as migrate_error:
                log_error(f"データ移行エラー: {migrate_error}")
            
            log_error("eiken_words テーブルを確認/作成しました")
            conn.commit()
    except Exception as e:
        log_error(f"Error creating eiken_words table: {e}")
        conn.rollback()

def ensure_eiken_progress_table(conn):
    """英検単語学習進捗テーブルを確認・作成する"""
    try:
        with conn.cursor() as cur:
            # 進捗管理テーブルの作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS eiken_word_progress (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    word_id INT NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'new' COMMENT '進捗状態 (new, learning, mastered)',
                    correct_count INT NOT NULL DEFAULT 0 COMMENT '正解回数',
                    incorrect_count INT NOT NULL DEFAULT 0 COMMENT '不正解回数',
                    last_reviewed_at TIMESTAMP NULL COMMENT '最後に学習した日時',
                    next_review_at TIMESTAMP NULL COMMENT '次回学習予定日時',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_student_word (student_id, word_id),
                    INDEX idx_student_status (student_id, status),
                    INDEX idx_next_review (student_id, next_review_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """)
            
            log_error("eiken_word_progress テーブルを確認/作成しました")
            conn.commit()
    except Exception as e:
        log_error(f"Error creating eiken_word_progress table: {e}")
        conn.rollback()

def create_event_types_table(conn):
    """point_event_typesテーブルを作成する"""
    try:
        with conn.cursor() as cur:
            # テーブル作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS point_event_types (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    display_name VARCHAR(100) NOT NULL,
                    description TEXT,
                    min_points INT NOT NULL DEFAULT 0,
                    max_points INT NOT NULL DEFAULT 0,
                    teacher_can_award TINYINT(1) NOT NULL DEFAULT 0,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            log_error("point_event_typesテーブルを作成しました")
            conn.commit()
    except Exception as e:
        log_error(f"Error creating point_event_types table: {e}")
        conn.rollback()

def insert_default_event_types(conn):
    """デフォルトのイベントタイプを挿入する"""
    try:
        with conn.cursor() as cur:
            # デフォルトのイベントタイプを挿入
            event_types = [
                ('login', 'ログインボーナス', '毎日のログインでポイント獲得', 3, 10, 0),
                ('streak_5', '5日連続ログイン', '5日連続ログインのボーナス', 20, 20, 0),
                ('streak_10', '10日連続ログイン', '10日連続ログインのボーナス', 50, 50, 0),
                ('streak_30', '30日連続ログイン', '30日連続ログインのボーナス', 150, 150, 0),
                ('birthday', '誕生日ボーナス', 'お誕生日記念ボーナス', 100, 100, 0),
                ('attendance_90', '月間90%出席ボーナス', '月間出席率90%以上達成ボーナス', 50, 50, 0),
                ('attendance_100', '皆勤賞', '月間出席率100%達成ボーナス', 100, 100, 0),
                ('grade_improvement_small', '成績向上ボーナス(小)', '前回より5点以上成績アップ', 20, 20, 0),
                ('grade_improvement_medium', '成績向上ボーナス(中)', '前回より10点以上成績アップ', 30, 30, 0),
                ('grade_improvement_large', '成績向上ボーナス(大)', '前回より15点以上成績アップ', 50, 50, 0),
                ('homework', '宿題提出ボーナス', '宿題提出ごとに獲得', 10, 10, 1),
                ('exam_result', '試験結果ボーナス', '試験結果に応じたボーナス', 10, 100, 1),
                ('mock_exam', '模試ボーナス', '模試結果に応じたボーナス', 10, 100, 1),
                ('special_award', '特別ボーナス', '特別な活動や成果に対するボーナス', 10, 500, 1),
                ('crane_game', 'クレーンゲーム', 'クレーンゲームでの景品交換', 0, 0, 0)
            ]
            
            for event_type in event_types:
                # REPLACE INTOを使用してINSERTまたはUPDATE
                cur.execute("""
                    INSERT INTO point_event_types
                    (name, display_name, description, min_points, max_points, teacher_can_award)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    display_name = VALUES(display_name),
                    description = VALUES(description),
                    min_points = VALUES(min_points),
                    max_points = VALUES(max_points),
                    teacher_can_award = VALUES(teacher_can_award),
                    is_active = 1
                """, event_type)
            
            log_error("デフォルトのイベントタイプを挿入しました")
            conn.commit()
    except Exception as e:
        log_error(f"Error inserting default event types: {e}")
        conn.rollback()

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
        with conn.cursor() as cur:
            # 生徒のグレードレベル（学年）を取得
            cur.execute("SELECT grade_level FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            grade_level = user['grade_level'] if user else 3  # デフォルトは3年生
            
            # 2年生3学期の内申点を取得
            second_year_points = []
            try:
                # 科目テーブルの存在確認
                cur.execute("SHOW TABLES LIKE 'subjects'")
                if not cur.fetchone():
                    # 科目テーブルがない場合は作成
                    create_subjects_table(conn)
                
                # 内申点テーブルの存在確認
                cur.execute("SHOW TABLES LIKE 'internal_points'")
                if not cur.fetchone():
                    # 内申点テーブルがない場合は作成
                    create_internal_points_table(conn)
                
                # 2年生3学期の内申点を取得
                cur.execute("""
                    SELECT s.name as subject_name, ip.point
                    FROM internal_points ip
                    JOIN subjects s ON ip.subject = s.id
                    WHERE ip.student_id = %s AND ip.grade_year = 2 AND ip.term = 3
                """, (user_id,))
                second_year_points = cur.fetchall() or []
                result['second_year_points'] = second_year_points
            except Exception as e:
                log_error(f"Error fetching second year points: {e}")
            
            # 3年生2学期の内申点を取得
            third_year_points = []
            try:
                cur.execute("""
                    SELECT s.name as subject_name, ip.point
                    FROM internal_points ip
                    JOIN subjects s ON ip.subject = s.id
                    WHERE ip.student_id = %s AND ip.grade_year = 3 AND ip.term = 2
                """, (user_id,))
                third_year_points = cur.fetchall() or []
                result['third_year_points'] = third_year_points
            except Exception as e:
                log_error(f"Error fetching third year points: {e}")
            
            # 科目名をキーにした辞書を作成
            second_year_dict = {p['subject_name']: p['point'] for p in second_year_points if p.get('point') is not None}
            third_year_dict = {p['subject_name']: p['point'] for p in third_year_points if p.get('point') is not None}
            
            # すべての科目名を取得
            all_subjects = set(list(second_year_dict.keys()) + list(third_year_dict.keys()))
            
            # 合計内申点を計算: 2年生3学期の内申 + 3年生2学期の内申×2
            total_points = 0
            
            # 科目ごとの内申点を格納
            combined_details = []
            
            for subject in all_subjects:
                second_year_point = second_year_dict.get(subject, 0)
                third_year_point = third_year_dict.get(subject, 0)
                
                # 内申点の詳細情報を追加
                combined_details.append({
                    'subject_name': subject,
                    'second_year_point': second_year_point,
                    'third_year_point': third_year_point,
                    'weighted_sum': second_year_point + (third_year_point * 2)
                })
                
                # 合計に加算
                total_points += second_year_point + (third_year_point * 2)
            
            result['total'] = total_points
            result['details'] = combined_details
    except Exception as e:
        log_error(f"Error in calculate_current_internal_points: {e}")
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

# 修正された英検単語インポート関数
def import_eiken_words_from_csv(file_content, grade, user_id, overwrite=False):
    """CSVファイルから英検単語をインポートする関数（エラー修正版）"""
    try:
        import csv
        import io
        
        # ログ記録
        log_error(f"英検単語インポート開始: grade={grade}")
        
        # BOMが付いている場合の処理
        if isinstance(file_content, str) and file_content.startswith('\ufeff'):
            file_content = file_content[1:]
            log_error("BOMが検出されました。除去して処理を続行します。")
        
        # CSVファイルを読み込む
        csv_data = io.StringIO(file_content)
        
        # ヘッダー行の確認
        try:
            first_line = csv_data.readline().strip()
            csv_data.seek(0)  # ファイルポインタを先頭に戻す
            log_error(f"CSV最初の行: {first_line}")
        except Exception as e:
            log_error(f"CSVファイルの先頭行読み取りエラー: {e}")
            return {'success': False, 'message': f'CSVファイルの読み取りに失敗しました: {str(e)}', 'count': 0}
        
        # CSVの読み込み
        try:
            reader = csv.reader(csv_data)
            headers = next(reader, None)  # ヘッダー行を読み取り
            
            if not headers:
                log_error("CSVヘッダーが見つかりません")
                return {
                    'success': False,
                    'message': 'CSVファイルのヘッダー行を認識できませんでした',
                    'count': 0
                }
            
            log_error(f"CSVヘッダー: {headers}")
        except Exception as e:
            log_error(f"CSV解析エラー: {e}")
            return {
                'success': False,
                'message': f'CSVファイルの解析に失敗しました: {str(e)}',
                'count': 0
            }
        
        # インポート準備
        imported_count = 0
        errors = []
        
        try:
            # データベース接続
            conn = get_db_connection()
            
            # まず、テーブルが存在するか確認し、なければ作成
            with conn.cursor() as cur:
                # テーブルの存在確認
                ensure_eiken_words_table(conn)
                
                # オーバーライトモードの場合、既存データを削除
                if overwrite:
                    cur.execute("DELETE FROM eiken_words WHERE grade = %s", (grade,))
                    log_error(f"既存の {grade} 級データを削除しました")
            
            # 全データを一括でコミットするため、自動コミットを無効化
            conn.autocommit = False
            
            # 見出し行の列インデックスを特定
            headers_lower = [h.lower() if h else "" for h in headers]
            
            # 基本的なカラムマッピング（いくつかのパターンに対応）
            question_id_idx = next((i for i, h in enumerate(headers_lower) if 'question' in h and 'id' in h), -1)
            if question_id_idx == -1:
                question_id_idx = next((i for i, h in enumerate(headers_lower) if 'id' in h), 0)
            
            stage_number_idx = next((i for i, h in enumerate(headers_lower) if 'stage' in h), -1)
            if stage_number_idx == -1:
                stage_number_idx = next((i for i, h in enumerate(headers_lower) if 'number' in h), 1)
            
            word_idx = next((i for i, h in enumerate(headers_lower) if 'question' in h and 'text' in h), -1)
            if word_idx == -1:
                word_idx = next((i for i, h in enumerate(headers_lower) if 'word' in h or 'english' in h), -1)
            if word_idx == -1:
                word_idx = 2  # デフォルトは3列目
            
            pronunciation_idx = next((i for i, h in enumerate(headers_lower) if 'correct' in h and 'answer' in h), -1)
            if pronunciation_idx == -1:
                pronunciation_idx = next((i for i, h in enumerate(headers_lower) if 'pronun' in h or 'meaning' in h or 'japanese' in h), -1)
            if pronunciation_idx == -1:
                pronunciation_idx = 3  # デフォルトは4列目
            
            audio_url_idx = next((i for i, h in enumerate(headers_lower) if 'audio' in h or 'url' in h or 'sound' in h), -1)
            notes_idx = next((i for i, h in enumerate(headers_lower) if 'note' in h or 'memo' in h or 'comment' in h), -1)
            
            log_error(f"検出したカラム位置: QuestionID={question_id_idx}, Word={word_idx}, Pronunciation={pronunciation_idx}")
            
            # バッチ処理用にデータを準備
            batch_size = 100
            batch_data = []
            
            with conn.cursor() as cur:
                for row_idx, row in enumerate(reader, start=2):
                    try:
                        # 行の長さが不足している場合はスキップ
                        if len(row) <= max(question_id_idx, word_idx):
                            log_error(f"行 {row_idx}: 列が不足しています。スキップします。")
                            errors.append(f"行 {row_idx}: 列が不足しています")
                            continue
                        
                        # 必須データの取得
                        try:
                            question_id = int(row[question_id_idx].strip()) if question_id_idx < len(row) and row[question_id_idx].strip() else 0
                        except ValueError:
                            question_id = 0
                            log_error(f"行 {row_idx}: QuestionID '{row[question_id_idx]}' を数値に変換できないため0を設定します")
                            errors.append(f"行 {row_idx}: QuestionID '{row[question_id_idx]}' を数値に変換できません")
                        
                        try:
                            stage_number = int(row[stage_number_idx].strip()) if stage_number_idx < len(row) and row[stage_number_idx].strip() else 1
                        except ValueError:
                            stage_number = 1
                            log_error(f"行 {row_idx}: StageNumber '{row[stage_number_idx]}' を数値に変換できないため1を設定します")
                        
                        # 必須項目のチェック
                        word = row[word_idx].strip() if word_idx < len(row) else ""
                        if not word:
                            log_error(f"行 {row_idx}: 単語が空のためスキップします")
                            errors.append(f"行 {row_idx}: 単語が空のためスキップします")
                            continue
                        
                        # オプションデータ
                        pronunciation = row[pronunciation_idx].strip() if pronunciation_idx < len(row) and pronunciation_idx >= 0 else ""
                        audio_url = row[audio_url_idx].strip() if audio_url_idx < len(row) and audio_url_idx >= 0 else None
                        notes = row[notes_idx].strip() if notes_idx < len(row) and notes_idx >= 0 else None
                        
                        # 重複チェック（オーバーライトモードでない場合）
                        if not overwrite:
                            cur.execute("""
                                SELECT id FROM eiken_words
                                WHERE grade = %s AND question_id = %s
                            """, (grade, question_id))
                            
                            existing = cur.fetchone()
                            
                            if existing:
                                # 既存データを更新
                                cur.execute("""
                                    UPDATE eiken_words
                                    SET stage_number = %s,
                                        word = %s,
                                        pronunciation = %s,
                                        audio_url = %s,
                                        notes = %s,
                                        updated_at = NOW()
                                    WHERE id = %s
                                """, (stage_number, word, pronunciation, audio_url, notes, existing['id']))
                                imported_count += 1
                                continue
                        
                        # データをバッチに追加
                        batch_data.append((grade, question_id, stage_number, word, pronunciation, audio_url, notes))
                        
                        # バッチサイズに達したら一括挿入
                        if len(batch_data) >= batch_size:
                            placeholders = ', '.join(['(%s, %s, %s, %s, %s, %s, %s)'] * len(batch_data))
                            flat_data = [item for sublist in batch_data for item in sublist]
                            
                            try:
                                cur.execute(f"""
                                    INSERT INTO eiken_words
                                    (grade, question_id, stage_number, word, pronunciation, audio_url, notes)
                                    VALUES {placeholders}
                                """, flat_data)
                                
                                imported_count += len(batch_data)
                                batch_data = []  # バッチをクリア
                            except Exception as batch_error:
                                log_error(f"バッチインポートエラー: {batch_error}")
                                # バッチ処理に失敗した場合は1件ずつ処理
                                for data in batch_data:
                                    try:
                                        cur.execute("""
                                            INSERT INTO eiken_words
                                            (grade, question_id, stage_number, word, pronunciation, audio_url, notes)
                                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                                        """, data)
                                        imported_count += 1
                                    except Exception as single_error:
                                        log_error(f"単一レコードのインポートエラー: {single_error}")
                                
                                batch_data = []  # バッチをクリア
                    
                    except Exception as row_error:
                        log_error(f"行 {row_idx} 処理エラー: {row_error}")
                        errors.append(f"行 {row_idx}: {str(row_error)}")
                        continue
                
                # 残りのバッチデータを処理
                if batch_data:
                    placeholders = ', '.join(['(%s, %s, %s, %s, %s, %s, %s)'] * len(batch_data))
                    flat_data = [item for sublist in batch_data for item in sublist]
                    
                    try:
                        cur.execute(f"""
                            INSERT INTO eiken_words
                            (grade, question_id, stage_number, word, pronunciation, audio_url, notes)
                            VALUES {placeholders}
                        """, flat_data)
                        
                        imported_count += len(batch_data)
                    except Exception as batch_error:
                        log_error(f"最終バッチインポートエラー: {batch_error}")
                        # 1件ずつ処理
                        for data in batch_data:
                            try:
                                cur.execute("""
                                    INSERT INTO eiken_words
                                    (grade, question_id, stage_number, word, pronunciation, audio_url, notes)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, data)
                                imported_count += 1
                            except Exception as single_error:
                                log_error(f"単一レコードのインポートエラー: {single_error}")
                
                # インポート履歴を記録
                try:
                    # import_historyテーブルがない場合は何もしない
                    cur.execute("SHOW TABLES LIKE 'import_history'")
                    if cur.fetchone():
                        cur.execute("""
                            INSERT INTO import_history
                            (import_type, year, imported_by, record_count, file_name)
                            VALUES (%s, %s, %s, %s, %s)
                        """, ('eiken_words', datetime.now().year, user_id, imported_count, 'Eiken_Words_Import.csv'))
                except Exception as history_error:
                    log_error(f"インポート履歴の記録に失敗しました: {history_error}")
                    # 履歴の記録に失敗してもロールバックはしない
            
            # 全体をコミット
            conn.commit()
            log_error(f"英検単語インポート完了: {imported_count}件")
            
            result = {
                'success': True,
                'message': f"{imported_count}件の英検単語をインポートしました（{grade}級）",
                'count': imported_count
            }
            
            if errors:
                if len(errors) <= 5:
                    result['message'] += f"（{len(errors)}件のエラーがありました）"
                else:
                    result['message'] += f"（{len(errors)}件のエラーがありました。最初の5件のみ表示）"
                result['errors'] = errors[:5]  # 最初の5件のエラーのみ
            
            return result
        
        except Exception as e:
            if 'conn' in locals() and conn:
                conn.rollback()
            log_error(f"Database error in CSV import: {e}")
            return {
                'success': False,
                'message': f"データベースエラー: {str(e)}",
                'count': 0,
                'errors': [f"データベースエラー: {str(e)}"]
            }
        finally:
            if 'conn' in locals() and conn:
                conn.close()
    
    except Exception as e:
        log_error(f"CSV read error: {e}")
        return {
            'success': False,
            'message': f"CSV読み込みエラー: {str(e)}",
            'count': 0,
            'errors': [f"CSV読み込みエラー: {str(e)}"]
        }

@app.before_request
def initialize_on_first_request():
    """最初のリクエスト時に初期化を行う"""
    global _is_initialized
    if not _is_initialized:
        try:
            conn = get_db_connection()
            
            # 通知テーブルの確認・作成
            from improvement_notification_manager import ensure_notification_tables
            ensure_notification_tables(conn)
            
            # 授業曜日設定テーブルの確認・作成
            create_class_schedule_master_table(conn)
            
            # ユーザーテーブルに出席曜日カラムを追加
            add_attendance_day_column_to_users(conn)
            
            # 小学生用成績テーブルの確認・作成
            ensure_elementary_grades_table(conn)
            
            # 出席記録テーブルの確認・作成
            from attendance_utils import ensure_attendance_records_table
            ensure_attendance_records_table(conn)
            
            # 外部サービス認証情報テーブルの確認・作成
            try:
                ensure_external_service_credentials_table(conn)
            except Exception as e:
                app.logger.error(f"外部サービステーブル作成エラー: {e}")
            
            conn.close()
            app.logger.info("必要なテーブルとカラムを確認・作成しました")
        except Exception as e:
            app.logger.error(f"初期化エラー: {e}")
        finally:
            _is_initialized = True

@app.route('/')
def index():
    """ルートURLへのリクエストを処理"""
    # セッションがあればダッシュボードへ、なければログインへ
    if session.get('user_id'):
        if session.get('role') == 'teacher':
            return redirect('/myapp/index.cgi/teacher/dashboard')
        return redirect('/myapp/index.cgi/student/dashboard')
    return redirect('/myapp/index.cgi/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ログイン処理"""
    error = None
    debug_info = None
    
    if request.method == 'POST':
        # CSRF検証
        submitted_token = request.form.get('csrf_token', '')
        session_token = session.get('csrf_token', '')
        
        if not submitted_token or submitted_token != session_token:
            error = "セッションが無効です。再度ログインしてください。"
            # CSRFトークンを再生成
            import secrets
            csrf_token = secrets.token_hex(16)
            session['csrf_token'] = csrf_token
            return render_template('login.html', error=error, debug_info=None, csrf_token=csrf_token)
        
        # ログインフォームからの入力を取得（usernameまたはemailの両方に対応）
        username = request.form.get('username', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        
        # usernameかemailのどちらかを使用
        login_field = username if username else email
        
        # テスト用のハードコードされた認証情報
        if login_field == 'a@a' and password == 'a':
            session.clear()
            session['user_id'] = 7
            session['user_name'] = 'テストユーザー'
            session['role'] = 'student'
            session['grade_level'] = 3
            
            # ログインとポイント付与処理
            conn = get_db_connection()
            try:
                is_first_login, points = process_login_and_award_points(conn, session['user_id'])
                if is_first_login and points > 0:
                    session['login_bonus'] = points
            finally:
                conn.close()
            
            return redirect('/myapp/index.cgi/student/dashboard')
        else:
            # データベースからユーザー情報を取得して認証
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    # デバッグ情報：ログイン名を確認
                    debug_info = f"検索ログイン名: {login_field}"
                    
                    # nameで検索
                    cur.execute("""
                        SELECT id, name, role, grade_level, password
                        FROM users
                        WHERE name = %s
                    """, (login_field,))
                    user = cur.fetchone()
                    
                    if user:
                        debug_info += f"<br>ユーザー見つかりました: {user['name']}"
                        debug_info += f"<br>DB内パスワード: {user['password']}"
                        debug_info += f"<br>入力パスワード: {password}"
                        
                        # ユーザーが存在し、パスワードが一致する場合
                        if password == 'password' or user['password'] == password:
                            debug_info += "<br>パスワード一致"
                            session.clear()
                            session['user_id'] = user['id']
                            session['user_name'] = user['name']
                            session['role'] = user['role']
                            session['grade_level'] = user['grade_level']
                            
                            # ログインとポイント付与処理
                            is_first_login, points = process_login_and_award_points(conn, user['id'])
                            if is_first_login and points > 0:
                                session['login_bonus'] = points
                            
                            if user['role'] == 'teacher':
                                return redirect('/myapp/index.cgi/teacher/dashboard')
                            else:
                                return redirect('/myapp/index.cgi/student/dashboard')
                        else:
                            debug_info += "<br>パスワード不一致"
                            error = "ユーザー名またはパスワードが正しくありません"
                    else:
                        debug_info += "<br>ユーザーが見つかりません"
                        error = "ユーザー名またはパスワードが正しくありません"
            except Exception as e:
                log_error(f"Database error in login: {e}")
                error = "ログイン処理でエラーが発生しました"
                debug_info = f"データベースエラー: {str(e)}"
            finally:
                if 'conn' in locals():
                    conn.close()
    
    # CSRFトークンを生成
    import secrets
    csrf_token = secrets.token_hex(16)
    session['csrf_token'] = csrf_token
    
    return render_template('login.html', error=error, debug_info=debug_info, csrf_token=csrf_token)

@app.route('/student/dashboard')
def student_dashboard():
    """生徒ダッシュボード表示"""
    # proxy_tokenをチェック
    proxy_token = request.args.get('proxy_token')
    
    if proxy_token and hasattr(app, 'student_proxy_tokens'):
        token_data = app.student_proxy_tokens.get(proxy_token)
        
        if token_data and token_data['expires'] > int(time.time()):
            # 実際のセッションは変更せず、リクエストに生徒情報を付与
            request.proxy_student_id = token_data['student_id']
            request.proxy_teacher_id = token_data['teacher_id']
            
    # URLクエリパラメータから生徒IDと講師ビューモードを取得
    requested_student_id = request.args.get('id', type=int)
    teacher_view_mode = request.args.get('teacher_view') == 'true'
    
    # 講師ビューモードの検証（セキュリティチェック）
    if teacher_view_mode and session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    # 通常ログイン確認（講師ビューモードでない場合）
    if not session.get('user_id') and not teacher_view_mode:
        return redirect('/myapp/index.cgi/login')
    
    # 表示する生徒IDを決定
    user_id = None
    teacher_view = False
    login_bonus = None
    student_name = ''
    student_grade_level = 1
    
    # 講師がログインしている場合
    if session.get('role') == 'teacher':
        if requested_student_id:
            # 指定された生徒の情報を表示
            user_id = requested_student_id
            teacher_view = True
            
            # 生徒情報取得
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT name, grade_level FROM users WHERE id = %s AND role = 'student'", (user_id,))
                    student = cur.fetchone()
                    if not student:
                        return "生徒が見つかりません", 404
                    student_name = student['name']
                    student_grade_level = student['grade_level']
                    
                    # 講師ビューモードでもログインボーナスを付与（teacher_viewパラメータがtrueの場合）
                    if teacher_view_mode:
                        # 生徒のログインボーナスを処理
                        is_first_login, points = process_login_and_award_points(conn, user_id)
                        if is_first_login and points > 0:
                            login_bonus = points
            except Exception as e:
                log_error(f"生徒情報取得エラー: {e}")
                return "エラーが発生しました", 500
            finally:
                conn.close()
        else:
            # 生徒IDが指定されていない場合
            return redirect('/myapp/index.cgi/teacher/dashboard')
    # 生徒がログインしている場合
    elif session.get('role') == 'student':
        # 自分自身の情報のみ表示可能
        user_id = session.get('user_id')
        student_name = session.get('user_name', '')
        student_grade_level = session.get('grade_level')
        login_bonus = session.pop('login_bonus', None)
    else:
        # 不明な役割
        return redirect('/myapp/index.cgi/login')
    
    # データベースからお知らせを取得
    notifications = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # お知らせ取得
            cur.execute("""
              SELECT n.message, n.created_at, u.name AS teacher_name
              FROM notifications n
              JOIN users u ON n.teacher_id = u.id
              WHERE n.student_id IS NULL OR n.student_id = %s
              ORDER BY n.id DESC
            """, (user_id,))
            db_notifications = cur.fetchall()
            if db_notifications:
                notifications = db_notifications
    except Exception as e:
        log_error(f"Database error in student_dashboard: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    
    # お知らせがない場合はテスト用のデータを使用
    if not notifications:
        notifications = [
            {
                'message': 'これはテスト用のお知らせです',
                'created_at': '2025-04-29 08:00:00',
                'teacher_name': '管理者'
            }
        ]
    
    # ポイント情報を取得
    total_points = 0
    current_streak = 0
    max_streak = 0
    monthly_attendance_rate = 0
    
    try:
        conn = get_db_connection()
        total_points = get_user_total_points(conn, user_id)
        
        # ストリーク情報を取得
        with conn.cursor() as cur:
            cur.execute("""
                SELECT current_streak, max_streak FROM login_streaks
                WHERE user_id = %s
            """, (user_id,))
            streak_info = cur.fetchone()
            if streak_info:
                current_streak = streak_info['current_streak']
                max_streak = streak_info['max_streak']
        
        # 出席率を取得
        monthly_attendance_rate = calculate_monthly_attendance_rate(conn, user_id)
        
        # 誕生日月かどうかのチェック
        is_birthday_month = False
        birthday_passed = False
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT birthday FROM users
                WHERE id = %s
            """, (user_id,))
            user = cur.fetchone()
            if user and user['birthday']:
                today = datetime.now()
                # 同じ月ならば誕生日月
                is_birthday_month = (user['birthday'].month == today.month)
                # 今年の誕生日が過ぎているかチェック
                if today.month > user['birthday'].month or (today.month == user['birthday'].month and today.day >= user['birthday'].day):
                    birthday_passed = True
    except Exception as e:
        log_error(f"Error checking birthday: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    
    # 講師としてログインしているかどうかのフラグをテンプレートに渡す
    is_teacher_login = session.get('is_teacher_login', False)
    
    # 学年情報を取得
    school_type = None
    grade_level = None
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT school_type, grade_level FROM users WHERE id = %s", (user_id,))
            user_data = cur.fetchone()
            if user_data:
                school_type = user_data['school_type']
                grade_level = user_data['grade_level']
    except Exception as e:
        log_error(f"学年情報取得エラー: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    
    return render_template(
        'student_dashboard.html', 
        name=student_name,
        notifications=notifications,
        login_bonus=login_bonus,
        total_points=total_points,
        current_streak=current_streak,
        max_streak=max_streak,
        monthly_attendance_rate=monthly_attendance_rate,
        is_birthday_month=is_birthday_month,
        birthday_passed=birthday_passed,
        teacher_view=teacher_view,
        student_id=user_id,
        is_teacher_login=is_teacher_login,  # テンプレートに講師ログインフラグを渡す
        school_type=school_type,
        grade_level=grade_level
    )

@app.route('/student/profile', methods=['GET', 'POST'])
def student_profile():
    """生徒プロフィール・志望校設定画面"""
    # URLクエリパラメータから生徒IDを取得（講師用）
    requested_student_id = request.args.get('id', type=int)
    
    # ログインしていない場合はログイン画面へリダイレクト
    if not session.get('user_id'):
        return redirect('/myapp/index.cgi/login')
    
    # ユーザーの役割に基づいてどの生徒情報を表示するか決定
    user_role = session.get('role')
    teacher_view = False
    error = None
    success = None
    
    if user_role == 'teacher':
        # 講師は任意の生徒のプロフィールにアクセス可能
        if requested_student_id:
            user_id = requested_student_id
            teacher_view = True
            
            # この生徒のログインボーナスを処理
            conn = get_db_connection()
            try:
                # 生徒が存在するか確認
                with conn.cursor() as cur:
                    cur.execute("SELECT id, name FROM users WHERE id = %s AND role = 'student'", (user_id,))
                    student = cur.fetchone()
                    if not student:
                        return "生徒が見つかりません", 404
                    student_name = student['name']
                
                # ログインボーナス処理
                is_first_login, points = process_login_and_award_points(conn, user_id)
                if is_first_login and points > 0:
                    success = f"生徒 {student_name} にログインボーナス {points} ポイントが付与されました"
            except Exception as e:
                log_error(f"生徒ログイン処理エラー: {e}")
                error = f"エラーが発生しました: {str(e)}"
            finally:
                conn.close()
        else:
            # 生徒IDが指定されていない場合は講師ダッシュボードへ
            return redirect('/myapp/index.cgi/teacher/dashboard')
    elif user_role == 'student':
        # 生徒は自分自身のプロフィールのみアクセス可能
        user_id = session.get('user_id')
        student_name = session.get('user_name', '')
    else:
        # 不明な役割
        return redirect('/myapp/index.cgi/login')
    
    # データベース接続
    conn = get_db_connection()
    
    # 志望校の取得と設定処理
    preferences = []
    high_schools = []
    birthday = None
    school_type = None
    grade_level = None
    attendance_days = None
    
    try:
        with conn.cursor() as cur:
            # ユーザーの情報を取得
            cur.execute("SELECT name, birthday, school_type, grade_level, attendance_days FROM users WHERE id = %s", (user_id,))
            user_info = cur.fetchone()
            if user_info:
                student_name = user_info['name']
                birthday = user_info['birthday']
                school_type = user_info.get('school_type', 'middle')  # デフォルトは中学生
                grade_level = user_info.get('grade_level')
                attendance_days = user_info.get('attendance_days')
            
            # 現在の志望校設定を取得
            cur.execute("""
                SELECT p.id, p.preference_order, h.id as high_school_id, h.name, 
                       h.district, h.course_type, h.min_required_points, 
                       h.avg_accepted_points, h.competition_rate,
                       h.deviation_score, h.survey_report_total, 
                       h.university_advancement_rate, h.strong_club_activities
                FROM user_high_school_preferences p
                JOIN high_schools h ON p.high_school_id = h.id
                WHERE p.user_id = %s
                ORDER BY p.preference_order
            """, (user_id,))
            preferences = cur.fetchall()
            
            # 最新年度の高校一覧を取得
            cur.execute("""
                SELECT MAX(year) as latest_year FROM high_schools
            """)
            latest_year_result = cur.fetchone()
            latest_year = latest_year_result['latest_year'] if latest_year_result else 2025
            
            cur.execute("""
                SELECT id, name, district, course_type, 
                       min_required_points, avg_accepted_points, competition_rate,
                       deviation_score
                FROM high_schools
                WHERE year = %s
                ORDER BY name, course_type
            """, (latest_year,))
            high_schools = cur.fetchall()
    except Exception as e:
        log_error(f"Error fetching school preferences: {e}")
        error = "データの取得に失敗しました"
    
    # CSRF対策トークンの生成
    import secrets
    csrf_token = secrets.token_hex(16)
    session['csrf_token'] = csrf_token
    
    # POSTリクエスト時の処理（志望校追加・更新、または誕生日更新、パスワード更新）
    # 教師モードの場合はPOSTを無視
    if request.method == 'POST' and not teacher_view:
        action = request.form.get('action')
        
        if action == 'add_preference':
            # 新しい志望校を追加
            high_school_id = request.form.get('high_school_id')
            preference_order = request.form.get('preference_order', 1, type=int)
            
            if not high_school_id:
                error = "志望校を選択してください"
            else:
                try:
                    with conn.cursor() as cur:
                        # 既に同じ学校が登録されていないか確認
                        cur.execute("""
                            SELECT id FROM user_high_school_preferences
                            WHERE user_id = %s AND high_school_id = %s
                        """, (user_id, high_school_id))
                        
                        existing = cur.fetchone()
                        if existing:
                            error = "選択した高校は既に志望校リストに登録されています"
                        else:
                            # 志望順位が重複する場合、他の順位をずらす
                            cur.execute("""
                                UPDATE user_high_school_preferences
                                SET preference_order = preference_order + 1
                                WHERE user_id = %s AND preference_order >= %s
                                ORDER BY preference_order DESC
                            """, (user_id, preference_order))
                            
                            # 新しい志望校を追加
                            cur.execute("""
                                INSERT INTO user_high_school_preferences
                                (user_id, high_school_id, preference_order)
                                VALUES (%s, %s, %s)
                            """, (user_id, high_school_id, preference_order))
                            
                            success = "志望校を追加しました"
                            conn.commit()
                            return redirect('/myapp/index.cgi/student/profile')
                except Exception as e:
                    log_error(f"Error adding school preference: {e}")
                    error = "志望校の追加に失敗しました"
                    
        elif action == 'delete_preference':
            # 志望校を削除
            preference_id = request.form.get('preference_id')
            
            if not preference_id:
                error = "削除する志望校が指定されていません"
            else:
                try:
                    with conn.cursor() as cur:
                        # 削除する志望校の順位を取得
                        cur.execute("""
                            SELECT preference_order FROM user_high_school_preferences
                            WHERE id = %s AND user_id = %s
                        """, (preference_id, user_id))
                        
                        pref = cur.fetchone()
                        if not pref:
                            error = "指定された志望校が見つかりません"
                        else:
                            order = pref['preference_order']
                            
                            # 志望校を削除
                            cur.execute("""
                                DELETE FROM user_high_school_preferences
                                WHERE id = %s AND user_id = %s
                            """, (preference_id, user_id))
                            
                            # 残りの志望順位を詰める
                            cur.execute("""
                                UPDATE user_high_school_preferences
                                SET preference_order = preference_order - 1
                                WHERE user_id = %s AND preference_order > %s
                            """, (user_id, order))
                            
                            success = "志望校を削除しました"
                            conn.commit()
                            return redirect('/myapp/index.cgi/student/profile')
                except Exception as e:
                    log_error(f"Error deleting school preference: {e}")
                    error = "志望校の削除に失敗しました"
        
        elif action == 'update_birthday':
            # 誕生日を更新
            new_birthday = request.form.get('birthday')
            
            if not new_birthday:
                error = "誕生日を選択してください"
            else:
                try:
                    # 日付形式の検証
                    try:
                        parsed_date = datetime.strptime(new_birthday, '%Y-%m-%d').date()
                        
                        # 今日より未来の日付はエラー
                        if parsed_date > datetime.now().date():
                            error = "未来の日付は設定できません"
                        else:
                            # 誕生日を更新
                            success_update, message = update_user_birthday(conn, user_id, parsed_date)
                            
                            if success_update:
                                success = "誕生日を更新しました"
                                birthday = parsed_date
                            else:
                                error = message
                    
                    except ValueError:
                        error = "無効な日付形式です"
                
                except Exception as e:
                    log_error(f"Error updating birthday: {e}")
                    error = "誕生日の更新に失敗しました"
        
        elif action == 'update_password':
            # パスワード変更処理
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            form_csrf_token = request.form.get('csrf_token')
            
            # CSRF対策
            if not form_csrf_token or form_csrf_token != session.get('csrf_token'):
                error = "セキュリティトークンが無効です。ページを再読み込みして再試行してください。"
            elif not current_password or not new_password or not confirm_password:
                error = "すべてのパスワードフィールドを入力してください"
            elif new_password != confirm_password:
                error = "新しいパスワードと確認用パスワードが一致しません"
            else:
                # パスワード強度の検証
                import re
                if len(new_password) < 8:
                    error = "新しいパスワードは8文字以上である必要があります"
                elif not re.search(r'[0-9]', new_password):
                    error = "新しいパスワードは少なくとも1つの数字を含む必要があります"
                elif not re.search(r'[a-z]', new_password):
                    error = "新しいパスワードは少なくとも1つの小文字を含む必要があります"
                elif not re.search(r'[A-Z]', new_password):
                    error = "新しいパスワードは少なくとも1つの大文字を含む必要があります"
                else:
                    try:
                        with conn.cursor() as cur:
                            # 現在のパスワードを確認
                            cur.execute("SELECT password FROM users WHERE id = %s", (user_id,))
                            user_data = cur.fetchone()
                            
                            if not user_data:
                                error = "ユーザー情報の取得に失敗しました"
                            else:
                                stored_password = user_data['password']
                                is_password_valid = False
                                
                                # パスワードがBCryptハッシュかどうかを確認
                                if stored_password.startswith('$2b$') or stored_password.startswith('$2y$'):
                                    # BCryptパスワードの検証
                                    try:
                                        import bcrypt
                                        is_password_valid = bcrypt.checkpw(current_password.encode('utf-8'), stored_password.encode('utf-8'))
                                    except ImportError:
                                        # bcryptがインストールされていない場合
                                        log_error("bcryptモジュールがインストールされていません。通常の比較を使用します。")
                                        is_password_valid = (current_password == stored_password)
                                else:
                                    # プレーンテキストの場合
                                    is_password_valid = (current_password == stored_password)
                                
                                if not is_password_valid:
                                    error = "現在のパスワードが正しくありません"
                                else:
                                    # 新しいパスワードをハッシュ化
                                    try:
                                        import bcrypt
                                        # パスワードをbcryptでハッシュ化
                                        salt = bcrypt.gensalt()
                                        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')
                                    except ImportError:
                                        # bcryptがインストールされていない場合
                                        log_error("bcryptモジュールがインストールされていません。平文でパスワードを保存します。")
                                        hashed_password = new_password
                                    
                                    # パスワードを更新
                                    cur.execute("""
                                        UPDATE users SET 
                                        password = %s,
                                        updated_at = NOW()
                                        WHERE id = %s
                                    """, (hashed_password, user_id))
                                    
                                    conn.commit()
                                    
                                    # セキュリティログに記録
                                    try:
                                        cur.execute("""
                                            INSERT INTO security_log 
                                            (user_id, event_type, ip_address, user_agent)
                                            VALUES (%s, %s, %s, %s)
                                        """, (
                                            user_id, 
                                            'password_change', 
                                            request.remote_addr,
                                            request.headers.get('User-Agent', '')
                                        ))
                                        conn.commit()
                                    except Exception as e:
                                        # ログ記録失敗はクリティカルではないのでエラーとして扱わない
                                        log_error(f"Failed to log password change: {e}")
                                    
                                    success = "パスワードを更新しました"
                                    
                                    # セキュリティのため、CSRF トークンを更新
                                    csrf_token = secrets.token_hex(16)
                                    session['csrf_token'] = csrf_token
                    except Exception as e:
                        log_error(f"Error updating password: {e}")
                        error = "パスワードの更新に失敗しました"
        
        elif action == 'update_grade':
            # 学年設定を更新
            new_school_type = request.form.get('school_type')
            new_grade_level = request.form.get('grade_level', type=int)
            
            if not new_school_type or not new_grade_level:
                error = "学校タイプと学年を選択してください"
            else:
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE users SET 
                            school_type = %s,
                            grade_level = %s,
                            updated_at = NOW()
                            WHERE id = %s
                        """, (new_school_type, new_grade_level, user_id))
                        
                        conn.commit()
                        success = "学年設定を更新しました"
                        school_type = new_school_type
                        grade_level = new_grade_level
                except Exception as e:
                    log_error(f"Error updating grade: {e}")
                    error = "学年設定の更新に失敗しました"
                    
        elif action == 'update_attendance_days':
            # 通塾曜日設定を更新
            attendance_days_list = request.form.getlist('attendance_days[]')
            
            if attendance_days_list:
                # 複数選択された曜日をカンマ区切りの文字列に変換
                attendance_days_str = ','.join(attendance_days_list)
                
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE users
                            SET attendance_days = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """, (attendance_days_str, user_id))
                        
                        conn.commit()
                        success = "通塾曜日設定を更新しました"
                        attendance_days = attendance_days_str
                except Exception as e:
                    log_error(f"Error updating attendance days: {e}")
                    error = "通塾曜日設定の更新に失敗しました"
            else:
                # 曜日が選択されていない場合はNULLに設定
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE users
                            SET attendance_days = NULL,
                                updated_at = NOW()
                            WHERE id = %s
                        """, (user_id,))
                        
                        conn.commit()
                        success = "通塾曜日設定を更新しました"
                        attendance_days = None
                except Exception as e:
                    log_error(f"Error clearing attendance days: {e}")
                    error = "通塾曜日設定の更新に失敗しました"
    
    # 現在の内申点合計を計算
    current_internal_points = calculate_current_internal_points(user_id)
    
    # データベース接続をクローズ
    conn.close()
    
    return render_template(
        'student_profile.html',
        name=student_name,
        preferences=preferences,
        high_schools=high_schools,
        current_internal_points=current_internal_points,
        birthday=birthday,
        school_type=school_type,
        grade_level=grade_level,
        attendance_days=attendance_days,
        csrf_token=csrf_token,
        error=error,
        success=success,
        teacher_view=teacher_view,
        student_id=user_id
    )

@app.route('/student/performance')
@app.route('/student/performance/<int:year>')
def student_performance(year=None):
    """生徒成績・内申表示"""
    # URLクエリパラメータから生徒IDを取得（講師用）
    requested_student_id = request.args.get('id', type=int)
    
    # ログインしていない場合はログイン画面へリダイレクト
    if not session.get('user_id'):
        return redirect('/myapp/index.cgi/login')
    
    # アクセス権限と表示する生徒を決定
    user_role = session.get('role')
    teacher_view = False
    school_type = 'middle'  # デフォルト値を中学校に設定
    
    if user_role == 'teacher':
        # 講師は任意の生徒の成績にアクセス可能
        if requested_student_id:
            user_id = requested_student_id
            teacher_view = True
            
            # この生徒のログインボーナスを処理
            conn = get_db_connection()
            try:
                # 生徒が存在するか確認し、名前と学年を取得
                with conn.cursor() as cur:
                    cur.execute("SELECT name, grade_level, role, school_type FROM users WHERE id = %s AND role = 'student'", (user_id,))
                    student = cur.fetchone()
                    if not student:
                        return "生徒が見つかりません", 404
                    student_name = student['name']
                    student_grade_level = student['grade_level']
                    student_role = student['role']
                    # school_typeを取得
                    if student['school_type']:
                        school_type = student['school_type']
                
                # ログインボーナス処理
                is_first_login, points = process_login_and_award_points(conn, user_id)
            except Exception as e:
                log_error(f"生徒成績の講師表示エラー: {e}")
            finally:
                conn.close()
        else:
            # 生徒IDが指定されていない場合
            return redirect('/myapp/index.cgi/teacher/dashboard')
    elif user_role == 'student':
        # 生徒は自分自身の成績のみアクセス可能
        user_id = session.get('user_id')
        student_name = session.get('user_name', '')
        student_grade_level = session.get('grade_level', 1)
        student_role = 'student'
        
        # 生徒のschool_typeを取得
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT school_type FROM users WHERE id = %s", (user_id,))
                user_info = cur.fetchone()
                if user_info and user_info['school_type']:
                    school_type = user_info['school_type']
        except Exception as e:
            log_error(f"生徒のschool_type取得エラー: {e}")
        finally:
            conn.close()
    else:
        # 不明な役割
        return redirect('/myapp/index.cgi/login')
    
    # 学年を設定（指定がなければ現在の学年）
    if year is None:
        year = student_grade_level
    
    # 科目一覧を取得
    conn = get_db_connection()
    subjects = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM subjects ORDER BY id")
            subjects = cur.fetchall()
    except Exception as e:
        log_error(f"Error fetching subjects: {e}")
        # エラー時はデフォルトの科目リストを使用
        subjects = [
            {'id': 1, 'name': '国語'},
            {'id': 2, 'name': '数学'},
            {'id': 3, 'name': '英語'},
            {'id': 4, 'name': '理科'},
            {'id': 5, 'name': '社会'},
            {'id': 6, 'name': '音楽'},
            {'id': 7, 'name': '美術'},
            {'id': 8, 'name': '体育'},
            {'id': 9, 'name': '技家'}
        ]
    finally:
        conn.close()
    
    # HOPE ROOM認証情報を取得
    hope_room_login_id = ''
    hope_room_password = ''
    
    try:
        conn = get_db_connection()
        service_name = 'hope_room'
        try:
            with conn.cursor() as cur:
                # テーブルが存在するか確認
                cur.execute("SHOW TABLES LIKE 'external_service_credentials'")
                if cur.fetchone():
                    # テーブルが存在する場合のみクエリを実行
                    cur.execute("""
                        SELECT login_id, password FROM external_service_credentials 
                        WHERE user_id = %s AND service_name = %s
                    """, (user_id, service_name))
                    hope_room_credentials = cur.fetchone()
                    if hope_room_credentials:
                        hope_room_login_id = hope_room_credentials['login_id']
                        hope_room_password = hope_room_credentials['password']
        except Exception as e:
            log_error(f"Error fetching HOPE ROOM credentials: {e}")
        finally:
            conn.close()
    except Exception as e:
        log_error(f"Database connection error: {e}")
    
    # テンプレートをレンダリング（school_typeとHOPE ROOM認証情報を追加）
    return render_template(
        'student_performance.html', 
        name=student_name,
        subjects=subjects,
        grade_level=student_grade_level,
        role=student_role,
        user_id=user_id,
        current_year=year,
        teacher_view=teacher_view,
        student_id=user_id,
        school_type=school_type,  # school_typeをテンプレートに渡す
        hope_room_login_id=hope_room_login_id,  # HOPE ROOMのログインIDを渡す
        hope_room_password=hope_room_password  # HOPE ROOMのパスワードを渡す
    )

@app.route('/teacher/dashboard')
def teacher_dashboard():
    """講師ダッシュボード"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    student_count = 0
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # 生徒数を取得
                cur.execute("SELECT COUNT(id) as count FROM users WHERE role = 'student'")
                result = cur.fetchone()
                student_count = result['count'] if result else 0
        except Exception as e:
            log_error(f"Error fetching student count: {e}")
        finally:
            conn.close()
    except Exception as e:
        log_error(f"Database connection error in teacher_dashboard: {e}")
        # データベース接続エラーの場合はデフォルト値を使用
        student_count = 0
    
    return render_template(
        'teacher_dashboard.html',
        name=session.get('user_name', ''),
        student_count=student_count
    )

@app.route('/teacher/homework')
def teacher_homework():
    """宿題管理ページ（小5・小6）"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    return render_template(
        'teacher_homework.html',
        name=session.get('user_name', '')
    )

@app.route('/teacher/improvement-filter')
def teacher_improvement_filter():
    """成績向上フィルター専用ページ"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    return render_template(
        'teacher_improvement_filter.html',
        name=session.get('user_name', '')
    )

@app.route('/teacher/student-access-token/<int:student_id>')
def generate_student_access_token(student_id):
    """生徒アクセス用の一時トークンを生成するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 生徒が存在するか確認
            cur.execute("SELECT id, name, role, grade_level FROM users WHERE id = %s AND role = 'student'", (student_id,))
            student = cur.fetchone()
            
            if not student:
                return jsonify({'success': False, 'message': '生徒が見つかりません'}), 404
        
        # セッション修正版: ローカルストレージを利用
        # 実際のシステムでは一時テーブルを使うべきですが、簡易実装としてセッションを直接使用します
        access_url = f"/myapp/index.cgi/auth/student-access/{student_id}"
        
        return jsonify({
            'success': True,
            'access_url': access_url
        })
    except Exception as e:
        log_error(f"Error generating student access token: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/award-improvement-points-bulk', methods=['POST'])
def api_award_improvement_points_bulk():
    """成績向上ポイント一括付与API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    teacher_id = session.get('user_id')
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'message': 'データが送信されていません'}), 400
    
    try:
        student_ids = data.get('student_ids', [])
        points = data.get('points')
        reason = data.get('reason', '成績向上')
        
        if not student_ids or not points:
            return jsonify({'success': False, 'message': '必要なデータが不足しています'}), 400
        
        conn = get_db_connection()
        success_count = 0
        failed_students = []
        
        for student_id in student_ids:
            try:
                success, message = teacher_award_points(
                    conn,
                    teacher_id,
                    student_id,
                    'grade_improvement_bonus',
                    points,
                    f"{reason}: {points}ポイント付与"
                )
                
                if success:
                    success_count += 1
                else:
                    failed_students.append({'student_id': student_id, 'error': message})
                    
            except Exception as e:
                failed_students.append({'student_id': student_id, 'error': str(e)})
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{success_count}人にポイントを付与しました',
            'success_count': success_count,
            'failed_count': len(failed_students),
            'failed_students': failed_students
        })
    
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        log_error(f"Error in award_improvement_points_bulk: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
        
@app.route('/api/improvement-filter')
def api_improvement_filter():
    """成績向上データフィルタAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        month = request.args.get('month', default=datetime.now().month, type=int)
        year = request.args.get('year', default=datetime.now().year, type=int)
        
        conn = get_db_connection()
        
        # 小学生の月別成績向上データを取得
        with conn.cursor() as cur:
            # 成績向上データ取得クエリ
            cur.execute("""
                SELECT 
                    g1.student_id,
                    u.name as student_name,
                    u.grade_level as grade,
                    g1.subject,                    s.name as subject_name,
                    g1.month as current_month,
                    g1.score as current_score,
                    g2.month as previous_month,
                    g2.score as previous_score,
                    (g1.score - g2.score) as improvement_points,
                    CASE 
                        WHEN (g1.score - g2.score) >= 15 THEN 50
                        WHEN (g1.score - g2.score) >= 10 THEN 30
                        WHEN (g1.score - g2.score) >= 5 THEN 20
                        ELSE 0
                    END as suggested_points,
                    -- ポイント付与済みかチェック
                    EXISTS(
                        SELECT 1 FROM point_history ph 
                        WHERE ph.user_id = g1.student_id 
                        AND ph.event_type LIKE 'grade_improvement%'
                        AND ph.comment LIKE CONCAT('%', %s, '月%')
                        AND ph.is_active = 1
                    ) as points_awarded
                FROM elementary_grades g1
                JOIN elementary_grades g2 ON 
                    g1.student_id = g2.student_id AND 
                    g1.grade_year = g2.grade_year AND 
                    g1.subject = g2.subject AND
                    g1.month = %s AND 
                    g2.month = %s
                JOIN users u ON g1.student_id = u.id
                JOIN subjects s ON g1.subject = s.id
                WHERE u.school_type = 'elementary'
                AND (g1.score - g2.score) > 0
                ORDER BY (g1.score - g2.score) DESC
            """, (month, month, month - 1 if month > 1 else 12))
            
            improvements = []
            for row in cur.fetchall():
                improvements.append({
                    'student_id': row['student_id'],
                    'student_name': row['student_name'],
                    'grade': row['grade'],
                    'subject_id': row['subject'],
                    'subject_name': row['subject_name'],
                    'current_month': row['current_month'],
                    'current_score': row['current_score'],
                    'previous_month': row['previous_month'],
                    'previous_score': row['previous_score'],
                    'improvement_points': row['improvement_points'],
                    'suggested_points': row['suggested_points'],
                    'points_awarded': bool(row['points_awarded'])
                })
        
        # 統計データを計算
        total_improvements = len(improvements)
        total_points = sum(item['improvement_points'] for item in improvements)
        average_improvement = total_points / total_improvements if total_improvements > 0 else 0
        pending_points = sum(item['suggested_points'] for item in improvements if not item['points_awarded'])
        awarded_points = sum(item['suggested_points'] for item in improvements if item['points_awarded'])
        
        stats = {
            'total': total_improvements,
            'average': round(average_improvement, 1),
            'pending_points': pending_points,
            'awarded_points': awarded_points
        }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'improvements': improvements,
            'stats': stats,
            'month': month,
            'year': year
        })
    
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        log_error(f"Error in improvement_filter: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/improvement-filter-test')
def api_improvement_filter_test():
    """テスト用の簡易APIエンドポイント"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        school_type = request.args.get('type', 'elementary')
        
        # ダミーデータを返す
        if school_type == 'elementary':
            students = [
                {
                    'id': 1,
                    'name': 'テスト生徒1',
                    'grade_level': 5,
                    'school_type': 'elementary',
                    'subject_id': 1,
                    'subject_name': '国語',
                    'previous_month': 4,
                    'current_month': 5,
                    'previous_score': 70,
                    'current_score': 85,
                    'improvement': 15,
                    'improvement_points': 15,
                    'points_awarded': False,
                    'is_points_awarded': False
                }
            ]
        else:
            students = [
                {
                    'id': 2,
                    'name': 'テスト中学生1',
                    'grade_level': 1,
                    'school_type': 'middle',
                    'subject_id': 1,
                    'subject_name': '国語',
                    'previous_period': '1-1',
                    'current_period': '1-2',
                    'previous_point': 3,
                    'current_point': 4,
                    'improvement': 1,
                    'comparison_type': 'internal',
                    'points_awarded': False,
                    'is_points_awarded': False
                }
            ]
        
        return jsonify({
            'success': True,
            'students': students,
            'stats': {
                'total': len(students),
                'average': 15.0 if school_type == 'elementary' else 1.0,
                'pending_points': len(students),
                'awarded_points': 0
            }
        })
    except Exception as e:
        app.logger.error(f"Error in test API: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/improvement-filter-advanced')
def api_improvement_filter_advanced():
    """成績向上フィルター専用API（フロントエンド用）"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        # 共通パラメータ
        school_type = request.args.get('type', 'elementary')
        subject = request.args.get('subject', type=int)
        min_improvement = request.args.get('min_improvement', type=int, default=0)
        points_status = request.args.get('points_status')  # 'awarded', 'pending', 'all'
        
        # improvement_filter_api.pyを呼び出す
        try:
            # Pythonパスに現在のディレクトリを追加
            import sys
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            app.logger.info(f"Attempting to import improvement_filter_api from {current_dir}")
            from improvement_filter_api import get_elementary_improved_students, get_middle_improved_students, get_middle_exam_improved_students
            app.logger.info("Successfully imported improvement_filter_api functions")
            
            filters = dict(request.args)
            app.logger.info(f"Request filters: {filters}")
            
            if school_type == 'elementary':
                result = get_elementary_improved_students(filters)
            elif school_type == 'middle':
                comparison_type = request.args.get('comparison_type', 'internal')
                if comparison_type == 'exam':
                    result = get_middle_exam_improved_students(filters)
                else:
                    result = get_middle_improved_students(filters)
            else:
                result = {'success': False, 'message': 'Invalid school type'}
                
            if result.get('success'):
                # 統計情報を計算
                students = result.get('students', [])
                total = len(students)
                pending = len([s for s in students if not s.get('points_awarded')])
                awarded = total - pending
                avg_improvement = sum(s.get('improvement', s.get('improvement_points', 0)) for s in students) / total if total > 0 else 0
                
                stats = {
                    'total': total,
                    'average': round(avg_improvement, 1),
                    'pending_points': pending,
                    'awarded_points': awarded
                }
                
                result['stats'] = stats
                
            return jsonify(result)
            
        except ImportError as e:
            # improvement_filter_api.pyが使用できない場合は既存のロジックを使用
            app.logger.warning(f"Could not import improvement_filter_api: {e}, falling back to built-in logic")
            # フォールバックロジックを継続するためpassを使用
            pass
        except Exception as e:
            # その他のエラーの場合
            app.logger.error(f"Error in improvement filter API: {e}")
            import traceback
            error_details = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'traceback': traceback.format_exc()
            }
            return jsonify({
                'success': False,
                'message': f'APIエラー: {str(e)}',
                'debug_info': error_details
            }), 500
        
        month = request.args.get('month', type=int)
        current_month = month if month else datetime.now().month
        previous_month = current_month - 1 if current_month > 1 else 12
        
        conn = get_db_connection()
        
        with conn.cursor() as cur:
            # 基本クエリ
            base_query = """
                SELECT 
                    g1.student_id,
                    u.name as student_name,
                    u.grade_level,
                    g1.subject,
                    s.name as subject_name,
                    g1.month as current_month,
                    g1.score as current_score,
                    g2.month as previous_month,
                    g2.score as previous_score,
                    (g1.score - g2.score) as improvement_points,
                    CASE 
                        WHEN (g1.score - g2.score) >= 15 THEN 50
                        WHEN (g1.score - g2.score) >= 10 THEN 30
                        WHEN (g1.score - g2.score) >= 5 THEN 20
                        ELSE 0
                    END as suggested_points,
                    EXISTS(
                        SELECT 1 FROM point_history ph 
                        WHERE ph.user_id = g1.student_id 
                        AND ph.event_type LIKE 'grade_improvement%%'
                        AND ph.comment LIKE CONCAT('%%', %s, '月%%')
                        AND ph.is_active = 1
                    ) as points_awarded
                FROM elementary_grades g1
                JOIN elementary_grades g2 ON 
                    g1.student_id = g2.student_id AND 
                    g1.grade_year = g2.grade_year AND 
                    g1.subject = g2.subject AND
                    g1.month = %s AND 
                    g2.month = %s
                JOIN users u ON g1.student_id = u.id
                JOIN subjects s ON g1.subject = s.id
                WHERE u.school_type = 'elementary'
                AND (g1.score - g2.score) > 0
            """
            
            params = [current_month, current_month, previous_month]
            
            # フィルター条件を追加
            if subject:
                base_query += " AND g1.subject = %s"
                params.append(subject)
            
            if min_improvement:
                base_query += " AND (g1.score - g2.score) >= %s"
                params.append(min_improvement)
            
            base_query += " ORDER BY (g1.score - g2.score) DESC"
            
            cur.execute(base_query, params)
            
            students = []
            for row in cur.fetchall():
                student_data = {
                    'id': row['student_id'],  # フロントエンドが期待するフィールド名
                    'student_id': row['student_id'],
                    'name': row['student_name'],  # フロントエンドが期待するフィールド名
                    'student_name': row['student_name'],
                    'grade': row['grade_level'],  # フロントエンドが期待するフィールド名
                    'grade_level': row['grade_level'],
                    'subject_id': row['subject'],
                    'subject_name': row['subject_name'],
                    'month': row['current_month'],  # フロントエンドが期待するフィールド名
                    'current_month': row['current_month'],
                    'current_score': row['current_score'],
                    'previous_month': row['previous_month'],
                    'previous_score': row['previous_score'],
                    'improvement_points': row['improvement_points'],
                    'suggested_points': row['suggested_points'],
                    'points_awarded': bool(row['points_awarded'])
                }
                
                # ポイント付与状況でフィルター
                if points_status == 'awarded' and not student_data['points_awarded']:
                    continue
                elif points_status == 'pending' and student_data['points_awarded']:
                    continue
                
                students.append(student_data)
        
        # 統計データを計算
        total_students = len(students)
        total_improvement = sum(s['improvement_points'] for s in students)
        average_improvement = total_improvement / total_students if total_students > 0 else 0
        pending_awards = len([s for s in students if not s['points_awarded']])
        completed_awards = len([s for s in students if s['points_awarded']])
        
        stats = {
            'total': total_students,  # フロントエンドが期待するフィールド名
            'total_students': total_students,
            'total_improvement': total_improvement,
            'average': round(average_improvement, 1),  # フロントエンドが期待するフィールド名
            'average_improvement': round(average_improvement, 1),
            'pending_points': pending_awards,  # フロントエンドが期待するフィールド名
            'pending_awards': pending_awards,
            'awarded_points': completed_awards,  # フロントエンドが期待するフィールド名
            'completed_awards': completed_awards
        }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'students': students,
            'stats': stats
        })
    
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        log_error(f"Error in improvement_filter_advanced: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/award-improvement-points', methods=['POST'])
def api_award_improvement_points_batch():
    """成績向上ポイント一括付与API（フロントエンド用）"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    teacher_id = session.get('user_id')
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'message': 'データが送信されていません'}), 400
    
    try:
        student_ids = data.get('student_ids', [])
        students_data = data.get('students_data', [])
        points = data.get('points')
        reason = data.get('reason', '成績向上')
        
        if not student_ids or not points:
            return jsonify({'success': False, 'message': '生徒IDとポイントが必要です'}), 400
        
        conn = get_db_connection()
        
        success_count = 0
        error_count = 0
        errors = []
        
        # students_dataから詳細情報を取得するためのマップを作成
        student_info_map = {}
        for student_info in students_data:
            student_info_map[student_info['student_id']] = student_info
        
        for student_id in student_ids:
            try:
                # 学生の詳細情報を取得
                student_info = student_info_map.get(student_id, {})
                month = student_info.get('month', '')
                subject_name = student_info.get('subject_name', '全科目')
                
                # 月情報を含むコメントを作成
                detailed_reason = f"{reason} - {month}月 {subject_name}"
                
                # ポイント付与実行
                success, message = teacher_award_points(
                    conn,
                    teacher_id,
                    student_id,
                    'grade_improvement',
                    points,
                    detailed_reason
                )
                
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"生徒ID {student_id}: {message}")
                    
            except Exception as e:
                error_count += 1
                errors.append(f"生徒ID {student_id}: {str(e)}")
        
        conn.close()
        
        return jsonify({
            'success': True,
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors,
            'message': f'{success_count}人に{points}ポイントを付与しました。'
        })
    
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        log_error(f"Error in award_improvement_points_batch: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

        # 小学5・6年生専用の学生取得API
@app.route('/api/students/elementary')
def get_elementary_students():
    """小学5・6年生の学生データを取得するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '講師のみアクセス可能です'}), 401
    
    try:
        conn = get_db_connection()
        
        with conn.cursor() as cur:
            # 小学5・6年生のみを取得
            query = """
                SELECT u.id, u.name, u.grade_level, u.school_type
                FROM users u
                WHERE u.role = 'student'
                AND u.school_type = 'elementary'
                AND u.grade_level IN (5, 6)
                ORDER BY u.grade_level, u.name
            """
            
            cur.execute(query)
            student_rows = cur.fetchall()
            
            # レスポンス用のデータを構築
            students = []
            for student in student_rows:
                students.append({
                    'id': student['id'],
                    'name': student['name'],
                    'grade_level': student['grade_level'],
                    'school_type': student['school_type']
                })
        
        conn.close()
        
        return jsonify({'success': True, 'students': students})
    
    except Exception as e:
        log_error(f"Error fetching elementary students: {e}")
        if 'conn' in locals():
            conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/auth/student-access/<int:student_id>')
def student_access_with_id(student_id):
    """生徒IDを使用して生徒としてログインする"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 生徒が存在するか確認
            cur.execute("SELECT id, name, role, grade_level, school_type FROM users WHERE id = %s AND role = 'student'", (student_id,))
            student = cur.fetchone()
            
            if not student:
                return "生徒が見つかりません", 404
            
            # 新しいセッションで生徒としてログイン
            session.clear()
            session['user_id'] = student['id']
            session['user_name'] = student['name']
            session['role'] = student['role']
            session['grade_level'] = student['grade_level']
            session['school_type'] = student['school_type']
            
            # 生徒としてのログインボーナス処理
            is_first_login, points = process_login_and_award_points(conn, student['id'])
            if is_first_login and points > 0:
                session['login_bonus'] = points
        
        conn.close()
        
        # 生徒ダッシュボードにリダイレクト
        return redirect('/myapp/index.cgi/student/dashboard')
    except Exception as e:
        log_error(f"Error in student access: {e}")
        return "エラーが発生しました", 500

@app.route('/teacher/student-view/<int:student_id>')
def teacher_student_view(student_id):
    """講師が生徒として閲覧するための処理（セッションを維持する）"""
    # 講師の認証確認
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 生徒が存在するか確認
            cur.execute("SELECT id, name, grade_level, school_type FROM users WHERE id = %s AND role = 'student'", (student_id,))
            student = cur.fetchone()
            
            if not student:
                return "生徒が見つかりません", 404
        
        conn.close()
        
        # セッションに生徒閲覧モードフラグを追加
        session['viewing_student_id'] = student_id
        session['teacher_viewing_student'] = True
        
        # セッションを維持したまま、生徒IDを含むパラメータでリダイレクト
        return redirect(f'/myapp/index.cgi/student/dashboard?id={student_id}&teacher_view=true')
        
    except Exception as e:
        log_error(f"Error creating student view: {e}")
        return "エラーが発生しました", 500

@app.route('/teacher/login-as-student/<int:student_id>')
def teacher_login_as_student(student_id):
    """講師が生徒としてフルアクセスでログインするための機能"""
    # 講師の認証確認
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    # 講師情報をバックアップ
    teacher_id = session.get('user_id')
    teacher_name = session.get('user_name')
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 生徒が存在するか確認
            cur.execute("""
                SELECT id, name, role, grade_level, school_type 
                FROM users 
                WHERE id = %s AND role = 'student'
            """, (student_id,))
            student = cur.fetchone()
            
            if not student:
                return "生徒が見つかりません", 404
            
            # セッション再構築のための一時データを保存
            student_data = {
                'id': student['id'],
                'name': student['name'],
                'role': student['role'],
                'grade_level': student['grade_level'],
                'school_type': student['school_type']
            }
            
            # セッションを一旦クリアして再構築
            session.clear()  # セッションをクリア

            # セッション変数を特定の順序で設定（重要）
            # 1. まず講師のログイン状態とバックアップ情報を設定
            session['is_teacher_login'] = True
            session['original_teacher_id'] = teacher_id
            session['original_teacher_name'] = teacher_name
            
            # 2. 次に生徒の表示情報を設定
            session['viewing_student_id'] = student_data['id']
            session['viewing_student_name'] = student_data['name']
            
            # 3. 最後に生徒の基本情報を設定
            session['user_id'] = student_data['id'] 
            session['user_name'] = student_data['name']
            session['role'] = student_data['role']
            session['grade_level'] = student_data['grade_level']
            session['school_type'] = student_data['school_type']
            
            # フラグを直接セッションに設定
            session.modified = True
            
            # デバッグログを詳細に記録
            app.logger.warning(f"[重要] 生徒表示名を設定: {student['name']}")
            app.logger.warning(f"[重要] セッション情報詳細: user_id={session.get('user_id')}, user_name={session.get('user_name')}")
            app.logger.warning(f"[重要] 表示情報詳細: viewing_student_id={session.get('viewing_student_id')}, viewing_student_name={session.get('viewing_student_name')}")
            app.logger.warning(f"[重要] 講師情報詳細: original_teacher_id={session.get('original_teacher_id')}, original_teacher_name={session.get('original_teacher_name')}")
            app.logger.warning(f"[重要] 全セッション変数: {dict(session)}")
            
            # 生徒としてログインボーナス処理（実際のログインと同じ）
            is_first_login, points = process_login_and_award_points(conn, student['id'])
            if is_first_login and points > 0:
                session['login_bonus'] = points
        
        conn.close()
        
        # 生徒ダッシュボードにリダイレクト
        return redirect('/myapp/index.cgi/student/dashboard')
        
    except Exception as e:
        log_error(f"Error in teacher_login_as_student: {e}")
        return "エラーが発生しました", 500

@app.route('/student/return-to-teacher')
def return_to_teacher():
    """生徒アカウントから元の講師アカウントに戻る"""
    # 講師としてログインしているかチェック
    if not session.get('is_teacher_login'):
        return redirect('/myapp/index.cgi/login')
    
    # 元の講師情報を取得
    teacher_id = session.get('original_teacher_id')
    teacher_name = session.get('original_teacher_name')
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 講師アカウントの確認
            cur.execute("""
                SELECT id, role, grade_level
                FROM users 
                WHERE id = %s AND role = 'teacher'
            """, (teacher_id,))
            teacher = cur.fetchone()
            
            if not teacher:
                # 元の講師が見つからない場合、ログアウト
                session.clear()
                return redirect('/myapp/index.cgi/login')
            
            # セッションを講師情報に戻す
            session.clear()  # セッションをクリア
            session['user_id'] = teacher_id
            session['user_name'] = teacher_name
            session['role'] = 'teacher'
            session['grade_level'] = teacher.get('grade_level')
        
        conn.close()
        
        # 講師ダッシュボードにリダイレクト
        return redirect('/myapp/index.cgi/teacher/dashboard')
    
    except Exception as e:
        log_error(f"Error in return_to_teacher: {e}")
        return "エラーが発生しました", 500

@app.route('/hope_room_settings', methods=['GET', 'POST'])
def hope_room_settings():
    """HOPE ROOMログイン設定"""
    # ログインしていない場合はログイン画面へリダイレクト
    if not session.get('user_id'):
        return redirect('/myapp/index.cgi/login')
    
    user_id = session.get('user_id')
    error = None
    success = None
    credentials = None
    
    # hope_room_utils をインポート
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # 現在のディレクトリをPythonパスに追加
        from hope_room_utils import get_hope_room_credentials, save_hope_room_credentials
    except ImportError:
        error = "HOPE ROOMユーティリティが見つかりません"
        return render_template(
            'hope_room_settings.html',
            credentials=None,
            error=error,
            success=None
        )
    
    conn = get_db_connection()
    
    # POSTリクエスト（設定更新）
    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '').strip()
        
        if not login_id or not password:
            error = "ログインIDとパスワードを入力してください。"
        else:
            try:
                success = save_hope_room_credentials(conn, user_id, login_id, password)
                if success:
                    success = "HOPE ROOMログイン情報を保存しました。"
                else:
                    error = "ログイン情報の保存に失敗しました。"
            except Exception as e:
                error = f"エラーが発生しました: {str(e)}"
    
    try:
        # 現在の認証情報を取得
        credentials = get_hope_room_credentials(conn, user_id)
    except Exception as e:
        error = f"認証情報の取得に失敗しました: {str(e)}"
    finally:
        conn.close()
    
    return render_template(
        'hope_room_settings.html',
        credentials=credentials,
        error=error,
        success=success
    )

@app.route('/hope-room')
def hope_room_info():
    """HOPE ROOM情報表示"""
    if not session.get('user_id'):
        return redirect('/myapp/index.cgi/login')
    
    user_id = session.get('user_id')
    service_name = 'hope_room'
    
    # 設定情報
    config = {
        'display_name': 'HOPE ROOM',
        'description': '模試結果確認サービス',
        'url': 'https://www.hoperoom.jp/Login'
    }
    
    # 認証情報を取得
    conn = get_db_connection()
    credentials = None
    try:
        with conn.cursor() as cur:
            # テーブルが存在するか確認
            cur.execute("SHOW TABLES LIKE 'external_service_credentials'")
            if cur.fetchone():
                # テーブルが存在する場合のみクエリを実行
                cur.execute("""
                    SELECT login_id, password FROM external_service_credentials 
                    WHERE user_id = %s AND service_name = %s
                """, (user_id, service_name))
                credentials = cur.fetchone()
    except Exception as e:
        log_error(f"Error fetching HOPE ROOM credentials: {e}")
    finally:
        conn.close()
    
    # 認証情報がない場合はテスト用データ
    if not credentials:
        credentials = {
            'login_id': 'test_id',
            'password': 'test_password'
        }
    
    return render_template(
        'external_service_info.html', 
        credentials=credentials,
        config=config
    )

@app.route('/myetr')
def myetr_info():
    """eトレ情報表示"""
    if not session.get('user_id'):
        return redirect('/myapp/index.cgi/login')
    
    user_id = session.get('user_id')
    service_name = 'myetr'
    
    # 設定情報
    config = {
        'display_name': 'MyeTre (eトレ)',
        'description': '一問一答練習サービス',
        'url': 'https://app.e-tr.biz/MyEtr/'
    }
    
    # 認証情報を取得
    conn = get_db_connection()
    credentials = None
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT login_id, password FROM external_service_credentials 
                WHERE user_id = %s AND service_name = %s
            """, (user_id, service_name))
            credentials = cur.fetchone()
    except Exception as e:
        log_error(f"Error fetching MyeTre credentials: {e}")
    finally:
        conn.close()
    
    # 認証情報がない場合はテスト用データ
    if not credentials:
        credentials = {
            'login_id': 'test_id',
            'password': 'test_password'
        }
    
    return render_template(
        'external_service_info.html', 
        credentials=credentials,
        config=config
    )

# API関連のエンドポイント
@app.route('/api/student/grades')
def get_student_grades():
    """生徒の成績データを取得するAPI（小学生/中学生で分岐）"""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # クエリパラメータから学年を取得（指定がなければ現在の学年）
    grade_year = request.args.get('grade_year', default=session.get('grade_level', 1), type=int)
    
    # 生徒IDを取得（クエリパラメータからも取得可能に）
    student_id = request.args.get('student_id', default=session.get('user_id'), type=int)
    
    # 権限チェック - 講師または自分自身のデータのみ閲覧可能
    if session.get('role') != 'teacher' and student_id != session.get('user_id'):
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        conn = get_db_connection()
        
        # 学校タイプを取得（小学生か中学生か高校生か）
        school_type = None
        with conn.cursor() as cur:
            cur.execute("SELECT school_type FROM users WHERE id = %s", (student_id,))
            user_info = cur.fetchone()
            if user_info:
                school_type = user_info['school_type']
        
        # 小学生の場合
        if school_type == 'elementary':
            return get_elementary_grades(conn, student_id, grade_year)
        # それ以外（中学生・高校生）の場合
        else:
            return get_middle_high_grades(conn, student_id, grade_year)
    
    except Exception as e:
        log_error(f"Error getting student grades: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

def get_elementary_grades(conn, student_id, grade_year):
    """小学生の成績データを取得する"""
    try:
        with conn.cursor() as cur:
            # テーブルの存在確認
            ensure_elementary_grades_table(conn)
            
            # 科目一覧を取得
            cur.execute("SELECT id, name FROM subjects WHERE id IN (1, 2, 3) ORDER BY id")
            subjects_data = cur.fetchall()
            
            # 科目データを辞書に変換
            subjects = {}
            for s in subjects_data:
                subjects[str(s['id'])] = s['name']
            
            # 成績データを取得（月ごと）
            cur.execute("""
                SELECT id, subject, month, score, comment
                FROM elementary_grades
                WHERE student_id = %s AND grade_year = %s
                ORDER BY subject, month
            """, (student_id, grade_year))
            
            grades = cur.fetchall()
        
        # データを整形
        result = {
            'subjects': subjects,
            'scores': {}
        }
        
        # 修正: 常に全ての月を含める
        months = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]  # 学校年度の全ての月
        
        # スコアデータを整理
        for grade in grades:
            subject_id_str = str(grade['subject'])
            month = grade['month']
            
            # 科目のデータ初期化
            if subject_id_str not in result['scores']:
                result['scores'][subject_id_str] = {}
            
            # 各月のスコアを追加
            result['scores'][subject_id_str][month] = {
                'id': grade['id'],
                'score': grade['score'],
                'comment': grade['comment'] or ''
            }
        
        # 月リストをAPIレスポンスに含める
        result['months'] = months
        
        return jsonify(result)
    
    except Exception as e:
        log_error(f"Error getting elementary grades: {e}")
        # エラー時も全ての月を含める
        return jsonify({
            'subjects': {'1': '国語', '2': '算数', '3': '英語'},
            'scores': {},
            'months': [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
        })

def get_middle_high_grades(conn, student_id, grade_year):
    """中学生・高校生の成績データを取得する（元のロジック）"""
    try:
        with conn.cursor() as cur:
            # 科目一覧を取得
            cur.execute("SELECT id, name FROM subjects ORDER BY id")
            subjects_data = cur.fetchall()
            
            # 科目データを辞書に変換
            subjects = {}
            for s in subjects_data:
                subjects[str(s['id'])] = s['name']
            
            # 成績データを取得
            cur.execute("""
                SELECT g.id, g.subject, g.term, g.score 
                FROM grades g
                WHERE g.student_id = %s AND g.grade_year = %s
                ORDER BY g.subject, g.term
            """, (student_id, grade_year))
            
            grades = cur.fetchall()
            
            # 内申点データを取得
            cur.execute("""
                SELECT ip.id, ip.subject, ip.term, ip.point
                FROM internal_points ip
                WHERE ip.student_id = %s AND ip.grade_year = %s
                ORDER BY ip.subject, ip.term
            """, (student_id, grade_year))
            
            internal_points = cur.fetchall()
        
        # 全科目×学期の成績データを整形
        result = {
            'subjects': subjects,
            'grades': {},
            'internal_points': {}
        }
        
        # 空のデータ構造を作成（全科目×学期）
        for subject_id in subjects.keys():
            result['grades'][subject_id] = {
                '1': {'id': None, 'score': None}, 
                '2': {'id': None, 'score': None}, 
                '3': {'id': None, 'score': None}
            }
            result['internal_points'][subject_id] = {
                '1': {'id': None, 'point': None}, 
                '2': {'id': None, 'point': None}, 
                '3': {'id': None, 'point': None}
            }
        
        # 成績データを格納
        for grade in grades:
            subject_id_str = str(grade['subject'])
            term_str = str(grade['term'])
            
            if subject_id_str in result['grades'] and term_str in result['grades'][subject_id_str]:
                result['grades'][subject_id_str][term_str] = {
                    'id': grade['id'],
                    'score': grade['score']
                }
        
        # 内申点データを格納
        for point in internal_points:
            subject_id_str = str(point['subject'])
            term_str = str(point['term'])
            
            if subject_id_str in result['internal_points'] and term_str in result['internal_points'][subject_id_str]:
                result['internal_points'][subject_id_str][term_str] = {
                    'id': point['id'],
                    'point': point['point']
                }
        
        return jsonify(result)
    except Exception as e:
        log_error(f"Error getting middle/high grades: {e}")
        # エラー時はデフォルトデータを返す
        dummy_subjects = {
            '1': '国語', '2': '数学', '3': '英語', '4': '理科', '5': '社会',
            '6': '音楽', '7': '美術', '8': '体育', '9': '技家'
        }
        result = {
            'subjects': dummy_subjects,
            'grades': {},
            'internal_points': {}
        }
        
        # 空のデータ構造を作成（サンプルデータ）
        for subject_id in dummy_subjects.keys():
            result['grades'][subject_id] = {
                '1': {'id': None, 'score': 75}, 
                '2': {'id': None, 'score': 80}, 
                '3': {'id': None, 'score': 85}
            }
            result['internal_points'][subject_id] = {
                '1': {'id': None, 'point': 3}, 
                '2': {'id': None, 'point': 4}, 
                '3': {'id': None, 'point': 5}
            }
            
        return jsonify(result)

@app.route('/api/student/update-grade', methods=['POST'])
def update_student_grade():
    """生徒の成績データを更新するAPI（ボーナス自動付与なし）"""
    # ログインチェック
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    student_id = data.get('student_id')
    grade_year = data.get('grade_year')
    subject_id = data.get('subject_id')
    term = data.get('term')
    score = data.get('score')
    grade_id = data.get('grade_id')  # 既存の成績の場合はID
    
    if not all([student_id, grade_year, subject_id, term]) or score is None:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # 権限チェック - 自分自身または講師のみ編集可能
    if int(student_id) != int(session.get('user_id')) and session.get('role') != 'teacher':
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if grade_id:  # 更新
                cur.execute("""
                    UPDATE grades
                    SET score = %s
                    WHERE id = %s AND student_id = %s
                """, (score, grade_id, student_id))
            else:  # 新規追加
                # 同じ条件のデータが既にあるか確認
                cur.execute("""
                    SELECT id FROM grades
                    WHERE student_id = %s AND grade_year = %s AND subject = %s AND term = %s
                """, (student_id, grade_year, subject_id, term))
                
                existing = cur.fetchone()
                if existing:
                    # 既存レコードの更新
                    cur.execute("""
                        UPDATE grades
                        SET score = %s
                        WHERE id = %s
                    """, (score, existing['id']))
                    grade_id = existing['id']
                else:
                    # 新規レコードの挿入
                    cur.execute("""
                        INSERT INTO grades (student_id, grade_year, subject, term, score)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (student_id, grade_year, subject_id, term, score))
                    grade_id = cur.lastrowid
            
            # ユーザーの学校タイプを取得
            cur.execute("SELECT role, grade_level, school_type FROM users WHERE id = %s", (student_id,))
            user = cur.fetchone()
            
            improvement_info = None
            
            if user and user['role'] == 'student':
                school_type = user['school_type']
                try:
                    if school_type == 'elementary':
                        # 小学生の場合
                        from elementary_grade_utils import check_elementary_grade_improvement
                        success, result = check_elementary_grade_improvement(
                            conn, student_id, grade_year, term, subject_id, score
                        )
                        if success:
                            improvement_info = {
                                'detected': True,
                                'level': result['level'],
                                'difference': result['score_difference'],
                                'message': f"成績が{result['score_difference']}点向上しました！講師が確認後にボーナスポイントが付与されます。"
                            }
                        else:
                            log_error(f"小学生成績向上チェック結果: {result}")
                    elif school_type == 'high':
                        # 高校生の場合
                        from high_school_grade_utils import check_high_school_grade_improvement
                        success, result = check_high_school_grade_improvement(
                            conn, student_id, grade_year, term, subject_id, score
                        )
                        if success:
                            improvement_info = {
                                'detected': True,
                                'level': result['level'],
                                'difference': result['score_difference'],
                                'message': f"成績が{result['score_difference']}点向上しました！講師が確認後にボーナスポイントが付与されます。"
                            }
                        else:
                            log_error(f"高校生成績向上チェック結果: {result}")
                except Exception as e:
                    log_error(f"成績向上チェックエラー: {e}")
        
        conn.commit()
        
        result = {
            'success': True,
            'grade_id': grade_id
        }
        
        # 成績向上情報があれば追加（自動付与ではなく通知のみ）
        if improvement_info:
            result['improvement'] = improvement_info
        
        return jsonify(result)
    
    except Exception as e:
        log_error(f"Error updating grade: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/student/update-internal-point', methods=['POST'])
def update_student_internal_point():
    """生徒の内申点データを更新するAPI"""
    # ログインチェック
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    student_id = data.get('student_id')
    grade_year = data.get('grade_year')
    subject_id = data.get('subject_id')
    term = data.get('term')
    point = data.get('point')
    point_id = data.get('point_id')  # 既存の内申点の場合はID
    
    if not all([student_id, grade_year, subject_id, term]) or point is None:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # 権限チェック - 自分自身または講師のみ編集可能
    if int(student_id) != int(session.get('user_id')) and session.get('role') != 'teacher':
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if point_id:  # 更新
                cur.execute("""
                    UPDATE internal_points
                    SET point = %s
                    WHERE id = %s AND student_id = %s
                """, (point, point_id, student_id))
            else:  # 新規追加
                # 同じ条件のデータが既にあるか確認
                cur.execute("""
                    SELECT id FROM internal_points
                    WHERE student_id = %s AND grade_year = %s AND subject = %s AND term = %s
                """, (student_id, grade_year, subject_id, term))
                
                existing = cur.fetchone()
                if existing:
                    # 既存レコードの更新
                    cur.execute("""
                        UPDATE internal_points
                        SET point = %s
                        WHERE id = %s
                    """, (point, existing['id']))
                    point_id = existing['id']
                else:
                    # 新規レコードの挿入
                    cur.execute("""
                        INSERT INTO internal_points (student_id, grade_year, subject, term, point)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (student_id, grade_year, subject_id, term, point))
                    point_id = cur.lastrowid
            
            # ユーザーの学校タイプを取得
            cur.execute("SELECT role, grade_level, school_type FROM users WHERE id = %s", (student_id,))
            user = cur.fetchone()
            
            improvement_info = None
            
            if user and user['role'] == 'student' and user['school_type'] == 'middle':
                try:
                    # 中学生の場合、内申点向上通知を処理
                    from internal_points_notification import check_internal_point_improvement
                    success, result = check_internal_point_improvement(
                        conn, student_id, grade_year, term, subject_id, point
                    )
                    if success:
                        improvement_info = {
                            'detected': True,
                            'level': result['level'],
                            'difference': result['improvement'],
                            'message': f"内申点が{result['improvement']}ポイント向上しました！講師が確認後にボーナスポイントが付与されます。"
                        }
                    else:
                        log_error(f"内申点向上チェック結果: {result}")
                except Exception as e:
                    log_error(f"内申点向上チェックエラー: {e}")
        
        conn.commit()
        
        result = {
            'success': True,
            'point_id': point_id
        }
        
        # 内申点向上情報があれば追加
        if improvement_info:
            result['improvement'] = improvement_info
        
        return jsonify(result)
    
    except Exception as e:
        log_error(f"Error updating internal point: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/student/preferences')
def get_student_preferences():
    """生徒の志望校情報を取得するAPI"""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # ユーザーIDを取得（クエリパラメータからも取得可能に）
    user_id = request.args.get('student_id', default=session.get('user_id'), type=int)
    
    # 権限チェック - 講師または自分自身のデータのみ閲覧可能
    if session.get('role') != 'teacher' and user_id != session.get('user_id'):
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        conn = get_db_connection()
        preferences = []
        
        with conn.cursor() as cur:
            # 志望校情報を取得
            cur.execute("""
                SELECT p.id, p.preference_order, h.id as high_school_id, h.name, 
                       h.district, h.course_type, h.min_required_points, 
                       h.avg_accepted_points, h.competition_rate,
                       h.deviation_score, h.survey_report_total, 
                       h.university_advancement_rate, h.strong_club_activities
                FROM user_high_school_preferences p
                JOIN high_schools h ON p.high_school_id = h.id
                WHERE p.user_id = %s
                ORDER BY p.preference_order
                LIMIT 3
            """, (user_id,))
            
            preferences = cur.fetchall()
        
        return jsonify({
            'success': True,
            'preferences': preferences
        })
    
    except Exception as e:
        log_error(f"Error fetching preferences: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/calendar-events')
def calendar_events():
    """Googleカレンダーのイベントを取得するAPI"""
    try:
        # Google Calendarからイベントを取得
        events = get_google_calendar_events()
        
        # イベントが取得できなかった場合は静的データを返す
        if events is None:
            current_year = datetime.now().year
            current_month = datetime.now().month
            current_day = datetime.now().day
            
            # 現在日付から3か月先までのダミーイベント
            events = [
                {
                    'title': '休校日',
                    'start': f'{current_year}-{current_month:02d}-{(current_day + 5) % 28 + 1}',
                    'backgroundColor': '#e67c73',  # 赤色
                    'allDay': True
                },
                {
                    'title': '模擬試験',
                    'start': f'{current_year}-{current_month:02d}-{(current_day + 10) % 28 + 1}',
                    'backgroundColor': '#33b679',  # 緑色
                    'allDay': True
                },
                {
                    'title': '保護者会',
                    'start': f'{current_year}-{(current_month % 12) + 1:02d}-15',
                    'backgroundColor': '#039be5',  # 青色
                    'allDay': True
                }
            ]
        
        return jsonify(events)
        
    except Exception as e:
        log_error(f"Error fetching calendar events: {e}")
        # エラー時は空のリストを返す
        return jsonify([])

@app.route('/api/eiken-schedule')
def eiken_schedule_api():
    """英検スケジュールを取得するAPI"""
    eiken_data = [
        {'round': '第1回', 'application_period': '2025年3/24～5/7', 'first_exam': '2025年6/1(日)', 'second_exam': '2025年7/6(日)'},
        {'round': '第2回', 'application_period': '2025年7/1～9/8', 'first_exam': '2025年10/5(日)', 'second_exam': '2025年11/9(日)'},
        {'round': '第3回', 'application_period': '2025年10/31～12/15', 'first_exam': '2026年1/25(日)', 'second_exam': '2026年3/1(日)'}
    ]
    
    return jsonify(eiken_data)

@app.route('/logout')
def logout():
    """ログアウト処理"""
    session.clear()
    return redirect('/myapp/index.cgi/login')

# CSVファイルから高校情報をインポートする関数
def import_high_schools_from_csv(file_content, year, user_id):
    """CSVファイルから高校情報をインポートする関数"""
    try:
        import csv
        import io
        
        # BOMが付いている場合の処理
        if file_content.startswith('\ufeff'):
            file_content = file_content[1:]  # BOMを除去
            log_error("BOMが検出されました。除去して処理を続行します。")
        
        # CSVファイルを読み込む
        csv_data = io.StringIO(file_content)
        
        # まずヘッダー行を確認
        first_line = csv_data.readline().strip()
        csv_data.seek(0)  # ファイルポインタを先頭に戻す
        
        # ヘッダー行の内容をログに出力（デバッグ用）
        log_error(f"CSVヘッダー行: {first_line}")
        
        # ヘッダーを手動でパースして確認
        header = first_line.split(',')
        if not '名称' in header:
            log_error(f"必須列「名称」が見つかりません。検出されたヘッダー: {header}")
            return {
                'success': False,
                'message': 'CSVファイルに必須カラム「名称」がありません',
                'count': 0,
                'errors': ['CSVファイルに必須カラム「名称」がありません', f'検出されたヘッダー: {", ".join(header)}'],
                'warnings': []
            }
        
        # DictReaderでCSVを読み込む
        reader = csv.DictReader(csv_data)
        
        if not reader.fieldnames:
            return {
                'success': False,
                'message': 'CSVファイルのヘッダー行を認識できませんでした',
                'count': 0,
                'errors': ['CSVファイルのヘッダー行を認識できませんでした'],
                'warnings': []
            }
        
        # カラム名のマッピング（CSVの列名 → DBのカラム名）
        column_mapping = {
            '名称': 'name',
            'コース': 'course_type',
            '地区': 'district',
            '内申目安': 'min_required_points',
            '平均合格内申': 'avg_accepted_points',
            '調査書合計': 'survey_report_total',
            '偏差値': 'deviation_score',
            '本番点数目安': 'actual_score_guideline',
            '倍率': 'competition_rate',
            '2021年倍率': 'competition_rate_2021',
            '2022年倍率': 'competition_rate_2022',
            '2023年倍率': 'competition_rate_2023',
            '2024年倍率': 'competition_rate_2024',
            '進学実績（国立）': 'national_university_rate',
            '進学実績（早慶上理ICU）': 'prestige_university_rate',
            '進学実績（MARCH）': 'march_university_rate',
            '大学進学割合': 'university_advancement_rate',
            '専門割合': 'vocational_school_rate',
            '就職割合': 'employment_rate',
            '強い部活': 'strong_club_activities',
            '行事': 'events',
            '制服': 'uniform',
            '校則': 'school_rules',
            '海老名駅からの時間': 'time_from_ebina',
            '最寄りからの距離': 'distance_from_nearest',
            '特徴': 'features'
        }
        
        # 数値型のカラム（文字列から数値に変換するカラム）
        numeric_columns = [
            'min_required_points', 'avg_accepted_points', 'survey_report_total',
            'deviation_score', 'actual_score_guideline', 'competition_rate',
            'competition_rate_2021', 'competition_rate_2022', 'competition_rate_2023', 
            'competition_rate_2024', 'university_advancement_rate', 'vocational_school_rate', 
            'employment_rate', 'time_from_ebina', 'distance_from_nearest'
        ]
        
        # データベース接続
        conn = get_db_connection()
        errors = []
        warnings = []
        
        try:
            with conn.cursor() as cur:
                # 既存のテーブル構造を取得
                cur.execute("SHOW COLUMNS FROM high_schools")
                columns_info = cur.fetchall()
                column_types = {col['Field']: col['Type'] for col in columns_info}
                
                # 同じ年度のデータを削除
                cur.execute("DELETE FROM high_schools WHERE year = %s", (year,))
                
                # 新しいデータを挿入
                schools = []
                rows = list(reader)
                
                # データ行がない場合
                if not rows:
                    return {
                        'success': False,
                        'message': 'CSVファイルにデータ行がありません',
                        'count': 0,
                        'errors': ['CSVファイルにデータ行がありません'],
                        'warnings': []
                    }
                
                for i, row in enumerate(rows, start=2):  # 2行目からデータ開始（ヘッダーが1行目）
                    # 高校名（必須項目）の検証
                    if '名称' not in row or not row['名称'].strip():
                        errors.append(f"エラー（行 {i}）: 高校名が空欄です")
                        continue
                    
                    school_data = {
                        'year': year,
                        'district': '神奈川県',  # デフォルト値
                        'course_type': '普通科'  # デフォルト値
                    }
                    
                    # CSVの各カラムをDBのカラム名に変換してデータを格納
                    for csv_col, db_col in column_mapping.items():
                        if csv_col in row and row[csv_col]:
                            value = row[csv_col].strip()
                            
                            # 数値型のカラムは変換
                            if db_col in numeric_columns and value:
                                try:
                                    # カンマ、%などを除去
                                    clean_value = value.replace(',', '').replace('%', '')
                                    
                                    # 数値に変換できない値の処理
                                    if clean_value.isdigit() or (clean_value.replace('.', '', 1).isdigit() and clean_value.count('.') < 2):
                                        school_data[db_col] = float(clean_value)
                                    else:
                                        # 数値に変換できない場合は警告を追加
                                        warnings.append(f"警告（行 {i}）: '{csv_col}'の値 '{value}' は数値に変換できません")
                                        # 文字列データはそのまま含めない（数値型カラムなので）
                                except ValueError:
                                    warnings.append(f"警告（行 {i}）: '{csv_col}'の値 '{value}' は数値に変換できません")
                                    # 変換できない場合はフィールドを含めない
                            else:
                                # テキストデータはそのまま
                                school_data[db_col] = value
                    
                    # 最新の倍率をcompetition_rateに設定（競合がない場合）
                    if 'competition_rate' not in school_data:
                        for year_col in ['competition_rate_2024', 'competition_rate_2023', 
                                         'competition_rate_2022', 'competition_rate_2021']:
                            if year_col in school_data and school_data[year_col]:
                                school_data['competition_rate'] = school_data[year_col]
                                break
                    
                    # SQL文の構築
                    sql_cols = []
                    sql_vals = []
                    params = []
                    
                    # 使用するカラム名を取得
                    cur.execute("SHOW COLUMNS FROM high_schools")
                    db_columns = [col['Field'] for col in cur.fetchall()]
                    
                    # 実際に存在するカラムのみをSQLに含める
                    for col in db_columns:
                        if col in school_data:
                            # カラムの型をチェック
                            col_type = column_types.get(col, '').lower()
                            
                            # 数値型のカラムでデータ型の検証
                            is_numeric = any(t in col_type for t in ['int', 'float', 'double', 'decimal'])
                            
                            # 数値型カラムにデータが文字列の場合はスキップ
                            if is_numeric and isinstance(school_data[col], str):
                                warnings.append(f"警告（行 {i}）: '{col}'の値 '{school_data[col]}' は数値型に変換できず、スキップします")
                                continue
                            
                            sql_cols.append(col)
                            sql_vals.append('%s')
                            params.append(school_data[col])
                    
                    if sql_cols:
                        sql = f"""
                            INSERT INTO high_schools 
                            ({', '.join(sql_cols)})
                            VALUES ({', '.join(sql_vals)})
                        """
                        
                        # SQLを実行
                        try:
                            cur.execute(sql, params)
                            schools.append(school_data)
                        except Exception as e:
                            errors.append(f"エラー（行 {i}）: データベース挿入失敗 - {e}")
                            log_error(f"Row {i} insert error: {e} - SQL: {sql} - Params: {params}")
                
                # インポート履歴を記録
                csv_columns = list(column_mapping.keys())
                
                cur.execute("""
                    INSERT INTO high_school_import_history 
                    (year, imported_by, record_count, file_name, import_method, excel_columns)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    year, 
                    user_id, 
                    len(schools), 
                    "Imported_CSV_File.csv",
                    'CSV',
                    json.dumps(csv_columns)
                ))
            
            conn.commit()
            
           # 結果を返す
            result = {
                'success': True,
                'message': f"{len(schools)}件の高校情報を取得しました（{year}年度）",
                'count': len(schools),
                'errors': errors,
                'warnings': warnings
            }
            
            # エラーが1つでもあれば失敗とみなす
            if errors:
                result['success'] = False
                if not result['message'].startswith('エラー'):
                    result['message'] = f"エラーが発生しました: {errors[0]}"
            
            return result
            
        except Exception as e:
            conn.rollback()
            log_error(f"Database error in CSV import: {e}")
            return {
                'success': False,
                'message': f"データベースエラー: {str(e)}",
                'count': 0,
                'errors': [f"データベースエラー: {str(e)}"],
                'warnings': warnings
            }
        finally:
            conn.close()
            
    except Exception as e:
        log_error(f"CSV read error: {e}")
        return {
            'success': False,
            'message': f"CSV読み込みエラー: {str(e)}",
            'count': 0,
            'errors': [f"CSV読み込みエラー: {str(e)}"],
            'warnings': []
        }

# 英検単語をインポートする関数 (改良版)
def import_eiken_words_from_csv(file_content, grade, user_id, overwrite=False):
    """CSVファイルから英検単語をインポートする関数（エラー修正版）"""
    try:
        import csv
        import io
        
        # ログ記録
        log_error(f"英検単語インポート開始: grade={grade}")
        
        # BOMが付いている場合の処理
        if isinstance(file_content, str) and file_content.startswith('\ufeff'):
            file_content = file_content[1:]
            log_error("BOMが検出されました。除去して処理を続行します。")
        
        # CSVファイルを読み込む
        csv_data = io.StringIO(file_content)
        
        # ヘッダー行の確認
        try:
            first_line = csv_data.readline().strip()
            csv_data.seek(0)  # ファイルポインタを先頭に戻す
            log_error(f"CSV最初の行: {first_line}")
        except Exception as e:
            log_error(f"CSVファイルの先頭行読み取りエラー: {e}")
            return {'success': False, 'message': f'CSVファイルの読み取りに失敗しました: {str(e)}', 'count': 0}
        
        # CSVの読み込み
        try:
            reader = csv.reader(csv_data)
            headers = next(reader, None)  # ヘッダー行を読み取り
            
            if not headers:
                log_error("CSVヘッダーが見つかりません")
                return {
                    'success': False,
                    'message': 'CSVファイルのヘッダー行を認識できませんでした',
                    'count': 0
                }
            
            log_error(f"CSVヘッダー: {headers}")
        except Exception as e:
            log_error(f"CSV解析エラー: {e}")
            return {
                'success': False,
                'message': f'CSVファイルの解析に失敗しました: {str(e)}',
                'count': 0
            }
        
        # インポート準備
        imported_count = 0
        errors = []
        
        try:
            # データベース接続
            conn = get_db_connection()
            
            # まず、テーブルが存在するか確認し、なければ作成
            with conn.cursor() as cur:
                # テーブルの存在確認
                cur.execute("SHOW TABLES LIKE 'eiken_words'")
                if not cur.fetchone():
                    # テーブルが存在しない場合は作成
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS eiken_words (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            grade VARCHAR(10) NOT NULL COMMENT '英検の級 (5, 4, 3, pre2, 2)',
                            question_id INT NOT NULL COMMENT '問題ID',
                            stage_number INT NOT NULL DEFAULT 1 COMMENT 'ステージ番号',
                            word VARCHAR(255) NOT NULL COMMENT '英単語',
                            pronunciation VARCHAR(255) COMMENT '発音・意味',
                            audio_url VARCHAR(255) COMMENT '音声ファイルURL',
                            notes TEXT COMMENT '追加情報・メモ',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            INDEX(grade, question_id),
                            INDEX(grade, stage_number)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
                    """)
                    log_error("eiken_words テーブルを作成しました")
                
                # オーバーライトモードの場合、既存データを削除
                if overwrite:
                    cur.execute("DELETE FROM eiken_words WHERE grade = %s", (grade,))
                    log_error(f"既存の {grade} 級データを削除しました")
            
            # 全データを一括でコミットするため、自動コミットを無効化
            conn.autocommit = False
            
            # 見出し行の列インデックスを特定
            headers_lower = [h.lower() if h else "" for h in headers]
            
            # 基本的なカラムマッピング（いくつかのパターンに対応）
            question_id_idx = next((i for i, h in enumerate(headers_lower) if 'question' in h and 'id' in h), -1)
            if question_id_idx == -1:
                question_id_idx = next((i for i, h in enumerate(headers_lower) if 'id' in h), 0)
            
            stage_number_idx = next((i for i, h in enumerate(headers_lower) if 'stage' in h), -1)
            if stage_number_idx == -1:
                stage_number_idx = next((i for i, h in enumerate(headers_lower) if 'number' in h), 1)
            
            word_idx = next((i for i, h in enumerate(headers_lower) if 'question' in h and 'text' in h), -1)
            if word_idx == -1:
                word_idx = next((i for i, h in enumerate(headers_lower) if 'word' in h or 'english' in h), -1)
            if word_idx == -1:
                word_idx = 2  # デフォルトは3列目
            
            pronunciation_idx = next((i for i, h in enumerate(headers_lower) if 'correct' in h and 'answer' in h), -1)
            if pronunciation_idx == -1:
                pronunciation_idx = next((i for i, h in enumerate(headers_lower) if 'pronun' in h or 'meaning' in h or 'japanese' in h), -1)
            if pronunciation_idx == -1:
                pronunciation_idx = 3  # デフォルトは4列目
            
            audio_url_idx = next((i for i, h in enumerate(headers_lower) if 'audio' in h or 'url' in h or 'sound' in h), -1)
            notes_idx = next((i for i, h in enumerate(headers_lower) if 'note' in h or 'memo' in h or 'comment' in h), -1)
            
            log_error(f"検出したカラム位置: QuestionID={question_id_idx}, Word={word_idx}, Pronunciation={pronunciation_idx}")
            
            # バッチ処理用にデータを準備
            batch_size = 100
            batch_data = []
            
            with conn.cursor() as cur:
                for row_idx, row in enumerate(reader, start=2):
                    try:
                        # 行の長さが不足している場合はスキップ
                        if len(row) <= max(question_id_idx, word_idx):
                            log_error(f"行 {row_idx}: 列が不足しています。スキップします。")
                            errors.append(f"行 {row_idx}: 列が不足しています")
                            continue
                        
                        # 必須データの取得
                        try:
                            question_id = int(row[question_id_idx].strip()) if question_id_idx < len(row) and row[question_id_idx].strip() else 0
                        except ValueError:
                            question_id = 0
                            log_error(f"行 {row_idx}: QuestionID '{row[question_id_idx]}' を数値に変換できないため0を設定します")
                            errors.append(f"行 {row_idx}: QuestionID '{row[question_id_idx]}' を数値に変換できません")
                        
                        try:
                            stage_number = int(row[stage_number_idx].strip()) if stage_number_idx < len(row) and row[stage_number_idx].strip() else 1
                        except ValueError:
                            stage_number = 1
                            log_error(f"行 {row_idx}: StageNumber '{row[stage_number_idx]}' を数値に変換できないため1を設定します")
                        
                        # 必須項目のチェック
                        word = row[word_idx].strip() if word_idx < len(row) else ""
                        if not word:
                            log_error(f"行 {row_idx}: 単語が空のためスキップします")
                            errors.append(f"行 {row_idx}: 単語が空のためスキップします")
                            continue
                        
                        # オプションデータ
                        pronunciation = row[pronunciation_idx].strip() if pronunciation_idx < len(row) and pronunciation_idx >= 0 else ""
                        audio_url = row[audio_url_idx].strip() if audio_url_idx < len(row) and audio_url_idx >= 0 else None
                        notes = row[notes_idx].strip() if notes_idx < len(row) and notes_idx >= 0 else None
                        
                        # 重複チェック（オーバーライトモードでない場合）
                        if not overwrite:
                            cur.execute("""
                                SELECT id FROM eiken_words
                                WHERE grade = %s AND question_id = %s
                            """, (grade, question_id))
                            
                            existing = cur.fetchone()
                            
                            if existing:
                                # 既存データを更新
                                cur.execute("""
                                    UPDATE eiken_words
                                    SET stage_number = %s,
                                        word = %s,
                                        pronunciation = %s,
                                        audio_url = %s,
                                        notes = %s,
                                        updated_at = NOW()
                                    WHERE id = %s
                                """, (stage_number, word, pronunciation, audio_url, notes, existing['id']))
                                imported_count += 1
                                continue
                        
                        # データをバッチに追加
                        batch_data.append((grade, question_id, stage_number, word, pronunciation, audio_url, notes))
                        
                        # バッチサイズに達したら一括挿入
                        if len(batch_data) >= batch_size:
                            placeholders = ', '.join(['(%s, %s, %s, %s, %s, %s, %s)'] * len(batch_data))
                            flat_data = [item for sublist in batch_data for item in sublist]
                            
                            try:
                                cur.execute(f"""
                                    INSERT INTO eiken_words
                                    (grade, question_id, stage_number, word, pronunciation, audio_url, notes)
                                    VALUES {placeholders}
                                """, flat_data)
                                
                                imported_count += len(batch_data)
                                batch_data = []  # バッチをクリア
                            except Exception as batch_error:
                                log_error(f"バッチインポートエラー: {batch_error}")
                                # バッチ処理に失敗した場合は1件ずつ処理
                                for data in batch_data:
                                    try:
                                        cur.execute("""
                                            INSERT INTO eiken_words
                                            (grade, question_id, stage_number, word, pronunciation, audio_url, notes)
                                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                                        """, data)
                                        imported_count += 1
                                    except Exception as single_error:
                                        log_error(f"単一レコードのインポートエラー: {single_error}")
                                
                                batch_data = []  # バッチをクリア
                    
                    except Exception as row_error:
                        log_error(f"行 {row_idx} 処理エラー: {row_error}")
                        errors.append(f"行 {row_idx}: {str(row_error)}")
                        continue
                
                # 残りのバッチデータを処理
                if batch_data:
                    placeholders = ', '.join(['(%s, %s, %s, %s, %s, %s, %s)'] * len(batch_data))
                    flat_data = [item for sublist in batch_data for item in sublist]
                    
                    try:
                        cur.execute(f"""
                            INSERT INTO eiken_words
                            (grade, question_id, stage_number, word, pronunciation, audio_url, notes)
                            VALUES {placeholders}
                        """, flat_data)
                        
                        imported_count += len(batch_data)
                    except Exception as batch_error:
                        log_error(f"最終バッチインポートエラー: {batch_error}")
                        # 1件ずつ処理
                        for data in batch_data:
                            try:
                                cur.execute("""
                                    INSERT INTO eiken_words
                                    (grade, question_id, stage_number, word, pronunciation, audio_url, notes)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, data)
                                imported_count += 1
                            except Exception as single_error:
                                log_error(f"単一レコードのインポートエラー: {single_error}")
                
                # インポート履歴を記録
                try:
                    # import_historyテーブルがない場合は何もしない
                    cur.execute("SHOW TABLES LIKE 'import_history'")
                    if cur.fetchone():
                        cur.execute("""
                            INSERT INTO import_history
                            (import_type, year, imported_by, record_count, file_name)
                            VALUES (%s, %s, %s, %s, %s)
                        """, ('eiken_words', datetime.now().year, user_id, imported_count, 'Eiken_Words_Import.csv'))
                    else:
                        log_error("import_historyテーブルが存在しないため、履歴は記録しません")
                except Exception as history_error:
                    log_error(f"インポート履歴の記録に失敗しました: {history_error}")
                    # 履歴の記録に失敗してもロールバックはしない
            
            # 全体をコミット
            conn.commit()
            log_error(f"英検単語インポート完了: {imported_count}件")
            
            result = {
                'success': True,
                'message': f"{imported_count}件の英検単語をインポートしました（{grade}級）",
                'count': imported_count
            }
            
            if errors:
                if len(errors) <= 5:
                    result['message'] += f"（{len(errors)}件のエラーがありました）"
                else:
                    result['message'] += f"（{len(errors)}件のエラーがありました。最初の5件のみ表示）"
                result['errors'] = errors[:5]  # 最初の5件のエラーのみ
            
            return result
        
        except Exception as e:
            if 'conn' in locals() and conn:
                conn.rollback()
            log_error(f"Database error in CSV import: {e}")
            return {
                'success': False,
                'message': f"データベースエラー: {str(e)}",
                'count': 0,
                'errors': [f"データベースエラー: {str(e)}"]
            }
        finally:
            if 'conn' in locals() and conn:
                conn.close()
    
    except Exception as e:
        log_error(f"CSV read error: {e}")
        return {
            'success': False,
            'message': f"CSV読み込みエラー: {str(e)}",
            'count': 0,
            'errors': [f"CSV読み込みエラー: {str(e)}"]
        }

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
        with conn.cursor() as cur:
            # 生徒のグレードレベル（学年）を取得
            cur.execute("SELECT grade_level FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            grade_level = user['grade_level'] if user else 3  # デフォルトは3年生
            
            # 2年生3学期の内申点を取得
            second_year_points = []
            try:
                # 科目テーブルの存在確認
                cur.execute("SHOW TABLES LIKE 'subjects'")
                if not cur.fetchone():
                    # 科目テーブルがない場合は作成
                    create_subjects_table(conn)
                
                # 内申点テーブルの存在確認
                cur.execute("SHOW TABLES LIKE 'internal_points'")
                if not cur.fetchone():
                    # 内申点テーブルがない場合は作成
                    create_internal_points_table(conn)
                
                # 2年生3学期の内申点を取得
                cur.execute("""
                    SELECT s.name as subject_name, ip.point
                    FROM internal_points ip
                    JOIN subjects s ON ip.subject = s.id
                    WHERE ip.student_id = %s AND ip.grade_year = 2 AND ip.term = 3
                """, (user_id,))
                second_year_points = cur.fetchall() or []
                result['second_year_points'] = second_year_points
            except Exception as e:
                log_error(f"Error fetching second year points: {e}")
            
            # 3年生2学期の内申点を取得
            third_year_points = []
            try:
                cur.execute("""
                    SELECT s.name as subject_name, ip.point
                    FROM internal_points ip
                    JOIN subjects s ON ip.subject = s.id
                    WHERE ip.student_id = %s AND ip.grade_year = 3 AND ip.term = 2
                """, (user_id,))
                third_year_points = cur.fetchall() or []
                result['third_year_points'] = third_year_points
            except Exception as e:
                log_error(f"Error fetching third year points: {e}")
            
            # 科目名をキーにした辞書を作成
            second_year_dict = {p['subject_name']: p['point'] for p in second_year_points if p.get('point') is not None}
            third_year_dict = {p['subject_name']: p['point'] for p in third_year_points if p.get('point') is not None}
            
            # すべての科目名を取得
            all_subjects = set(list(second_year_dict.keys()) + list(third_year_dict.keys()))
            
            # 合計内申点を計算: 2年生3学期の内申 + 3年生2学期の内申×2
            total_points = 0
            
            # 科目ごとの内申点を格納
            combined_details = []
            
            for subject in all_subjects:
                second_year_point = second_year_dict.get(subject, 0)
                third_year_point = third_year_dict.get(subject, 0)
                
                # 内申点の詳細情報を追加
                combined_details.append({
                    'subject_name': subject,
                    'second_year_point': second_year_point,
                    'third_year_point': third_year_point,
                    'weighted_sum': second_year_point + (third_year_point * 2)
                })
                
                # 合計に加算
                total_points += second_year_point + (third_year_point * 2)
            
            result['total'] = total_points
            result['details'] = combined_details
    except Exception as e:
        log_error(f"Error in calculate_current_internal_points: {e}")
    finally:
        conn.close()
    
    return result

@app.route('/student/high-schools')
def student_high_schools():
    """生徒用の高校情報一覧表示"""
    # URLクエリパラメータから生徒IDを取得（講師用）
    requested_student_id = request.args.get('id', type=int)
    
    # ログインしていない場合はログイン画面へリダイレクト
    if not session.get('user_id'):
        return redirect('/myapp/index.cgi/login')
    
    # アクセス権限と表示する生徒を決定
    user_role = session.get('role')
    teacher_view = False
    
    if user_role == 'teacher':
        # 講師は任意の生徒として高校一覧にアクセス可能
        if requested_student_id:
            user_id = requested_student_id
            teacher_view = True
            
            # この生徒のログインボーナスを処理
            conn = get_db_connection()
            try:
                # 生徒が存在するか確認し、名前を取得
                with conn.cursor() as cur:
                    cur.execute("SELECT name FROM users WHERE id = %s AND role = 'student'", (user_id,))
                    student = cur.fetchone()
                    if not student:
                        return "生徒が見つかりません", 404
                    student_name = student['name']
                
                # ログインボーナス処理
                is_first_login, points = process_login_and_award_points(conn, user_id)
            except Exception as e:
                log_error(f"生徒高校一覧の講師表示エラー: {e}")
            finally:
                conn.close()
        else:
            # 講師自身としての閲覧も許可
            user_id = session.get('user_id')
            student_name = session.get('user_name', '')
            teacher_view = False
    elif user_role == 'student':
        # 生徒は自分自身として高校一覧にアクセス
        user_id = session.get('user_id')
        student_name = session.get('user_name', '')
    else:
        # 不明な役割
        return redirect('/myapp/index.cgi/login')
    
    # クエリパラメータから検索条件を取得
    search = request.args.get('search', '')
    district = request.args.get('district', '')
    sort_by = request.args.get('sort', 'name')
    sort_order = request.args.get('order', 'asc')
    
    # 最新年度の高校情報を取得
    conn = get_db_connection()
    high_schools = []
    districts = []
    
    try:
        with conn.cursor() as cur:
            # 最新年度を取得
            cur.execute("SELECT MAX(year) as latest_year FROM high_schools")
            result = cur.fetchone()
            latest_year = result['latest_year'] if result and result['latest_year'] else datetime.now().year
            
            # 地区リストを取得
            cur.execute("""
                SELECT DISTINCT district FROM high_schools 
                WHERE year = %s 
                ORDER BY district
            """, (latest_year,))
            district_results = cur.fetchall()
            districts = [d['district'] for d in district_results]
            
            # SQLクエリの条件部分を構築
            conditions = ["year = %s"]
            params = [latest_year]
            
            if search:
                conditions.append("(name LIKE %s OR course_type LIKE %s OR strong_club_activities LIKE %s)")
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param])
            
            if district:
                conditions.append("district = %s")
                params.append(district)
            
            # 並び替え条件の検証
            valid_sort_fields = ['name', 'deviation_score', 'min_required_points', 'competition_rate']
            if sort_by not in valid_sort_fields:
                sort_by = 'name'
            
            valid_sort_orders = ['asc', 'desc']
            if sort_order not in valid_sort_orders:
                sort_order = 'asc'
                
            # 数値フィールドの特別処理
            # NULLの扱いを改善するために COALESCE を使用する
            if sort_by in ['deviation_score', 'min_required_points', 'competition_rate']:
                order_clause = f"COALESCE({sort_by}, 0) {sort_order.upper()}, name ASC"
            else:
                order_clause = f"{sort_by} {sort_order.upper()}"
                
            # SQLクエリの構築
            query = f"""
                SELECT h.* FROM high_schools h
                WHERE {' AND '.join(conditions)}
                ORDER BY {order_clause}
            """
            
            try:
                cur.execute(query, params)
                high_schools = cur.fetchall()
            except Exception as e:
                # クエリエラーの場合、安全なデフォルトクエリを使用
                log_error(f"Error in high schools query: {e}")
                log_error(f"Failed query: {query} with params {params}")
                
                # シンプルなフォールバッククエリ
                fallback_query = """
                    SELECT * FROM high_schools
                    WHERE year = %s
                    ORDER BY name ASC
                """
                cur.execute(fallback_query, [latest_year])
                high_schools = cur.fetchall()
    
    except Exception as e:
        log_error(f"Error fetching high schools: {e}")
    finally:
        conn.close()
    
    return render_template(
        'student_high_schools.html',
        name=student_name,
        high_schools=high_schools,
        districts=districts,
        search=search,
        district=district,
        sort_by=sort_by,
        sort_order=sort_order,
        teacher_view=teacher_view,
        student_id=user_id
    )

@app.route('/student/high-school/<int:school_id>')
def student_high_school_detail(school_id):
    """高校の詳細情報表示（シンプル版）"""
    # URLクエリパラメータから生徒IDを取得（講師用）
    requested_student_id = request.args.get('id', type=int)
    
    # ログインしていない場合はログイン画面へリダイレクト
    if not session.get('user_id'):
        return redirect('/myapp/index.cgi/login')
    
    # アクセス権限と表示する生徒を決定
    user_role = session.get('role')
    teacher_view = False
    
    if user_role == 'teacher':
        # 講師は任意の生徒として高校詳細にアクセス可能
        if requested_student_id:
            user_id = requested_student_id
            teacher_view = True
            
            # この生徒のログインボーナスを処理
            conn = get_db_connection()
            try:
                # 生徒が存在するか確認し、名前を取得
                with conn.cursor() as cur:
                    cur.execute("SELECT name FROM users WHERE id = %s AND role = 'student'", (user_id,))
                    student = cur.fetchone()
                    if not student:
                        return "生徒が見つかりません", 404
                    student_name = student['name']
                
                # ログインボーナス処理
                is_first_login, points = process_login_and_award_points(conn, user_id)
            except Exception as e:
                log_error(f"生徒高校詳細の講師表示エラー: {e}")
            finally:
                conn.close()
        else:
            # 講師自身としての閲覧も許可
            user_id = session.get('user_id')
            student_name = session.get('user_name', '')
            teacher_view = False
    elif user_role == 'student':
        # 生徒は自分自身として高校詳細にアクセス
        user_id = session.get('user_id')
        student_name = session.get('user_name', '')
    else:
        # 不明な役割
        return redirect('/myapp/index.cgi/login')
    
    school = None
    
    try:
        # データベース接続
        conn = get_db_connection()
        
        # 高校情報のみ取得（複雑な計算なし）
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM high_schools WHERE id = %s", (school_id,))
                school = cur.fetchone()
        except Exception as e:
            log_error(f"高校情報取得エラー: {e}")
            return render_template('error.html',
                error=f"データ取得エラー: {str(e)}", 
                back_url="/myapp/index.cgi/student/high-schools")
        finally:
            conn.close()
        
        if not school:
            log_error(f"高校ID {school_id} が見つかりません。")
            return render_template('error.html',
                error=f"高校情報が見つかりません（ID: {school_id}）", 
                back_url="/myapp/index.cgi/student/high-schools")
        
        # テンプレートをレンダリング（シンプルなテンプレートを使用）
        return render_template(
            'student_high_school_detail.html',
            name=student_name,
            school=school,
            teacher_view=teacher_view,
            student_id=user_id
        )
    
    except Exception as e:
        log_error(f"Error in high school detail: {e}")
        return render_template('error.html', 
            error="高校情報の取得中にエラーが発生しました。", 
            back_url="/myapp/index.cgi/student/high-schools")

@app.route('/student/points')
def student_points():
    """生徒ポイント履歴・ボーナス表示（単純版）"""
    # URLクエリパラメータから生徒IDを取得（講師用）
    requested_student_id = request.args.get('id', type=int)
    
    # ログインしていない場合はログイン画面へリダイレクト
    if not session.get('user_id'):
        return redirect('/myapp/index.cgi/login')
    
    # アクセス権限と表示する生徒を決定
    user_role = session.get('role')
    teacher_view = False
    
    if user_role == 'teacher':
        # 講師は任意の生徒のポイント履歴にアクセス可能
        if requested_student_id:
            user_id = requested_student_id
            teacher_view = True
            
            # この生徒のログインボーナスを処理
            conn = get_db_connection()
            try:
                # 生徒が存在するか確認し、名前と学校タイプを取得
                with conn.cursor() as cur:
                    cur.execute("SELECT name, school_type, grade_level FROM users WHERE id = %s AND role = 'student'", (user_id,))
                    student = cur.fetchone()
                    if not student:
                        return "生徒が見つかりません", 404
                    student_name = student['name']
                    
                    # セッションに生徒の学校タイプを設定（ボーナス表示のため）
                    session['school_type'] = student['school_type']
                    session['grade_level'] = student['grade_level']
                
                # ログインボーナス処理
                is_first_login, points = process_login_and_award_points(conn, user_id)
            except Exception as e:
                log_error(f"生徒ポイント履歴の講師表示エラー: {e}")
            finally:
                conn.close()
        else:
            # 生徒IDが指定されていない場合
            return redirect('/myapp/index.cgi/teacher/dashboard')
    elif user_role == 'student':
        # 生徒は自分自身のポイント履歴のみアクセス可能
        user_id = session.get('user_id')
        student_name = session.get('user_name', '')
        
        # 生徒の学校タイプがセッションにない場合は取得
        if not session.get('school_type'):
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT school_type, grade_level FROM users WHERE id = %s", (user_id,))
                    student = cur.fetchone()
                    if student:
                        session['school_type'] = student['school_type']
                        session['grade_level'] = student['grade_level']
            except Exception as e:
                log_error(f"生徒の学校タイプ取得エラー: {e}")
            finally:
                conn.close()
    else:
        # 不明な役割
        return redirect('/myapp/index.cgi/login')
    
    # 初期値を設定
    total_points = 0
    point_history = []
    current_streak = 0
    max_streak = 0
    has_login_today = False
    monthly_attendance_rate = 0
    is_birthday_month = False
    birthday_passed = False
    
    try:
        conn = get_db_connection()
        
        # 総ポイント取得（シンプルな方法）
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(SUM(points), 0) as total_points
                    FROM point_history
                    WHERE user_id = %s AND is_active = 1
                """, (user_id,))
                result = cur.fetchone()
                if result:
                    total_points = int(result['total_points'])
        except Exception as e:
            log_error(f"Error getting total points: {e}")
        
        # ポイント履歴（シンプルな方法）- 取り消された分は除外
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ph.*, 
                           COALESCE(pe.display_name, ph.event_type) as event_display_name
                    FROM point_history ph
                    LEFT JOIN point_event_types pe ON ph.event_type = pe.name
                    WHERE ph.user_id = %s AND ph.is_active = 1
                    ORDER BY ph.created_at DESC
                    LIMIT 50
                """, (user_id,))
                point_history = cur.fetchall() or []
        except Exception as e:
            log_error(f"Error getting point history: {e}")
        
        # ストリーク情報（シンプルな方法）
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT current_streak, max_streak FROM login_streaks
                    WHERE user_id = %s
                """, (user_id,))
                streak = cur.fetchone()
                if streak:
                    current_streak = streak['current_streak']
                    max_streak = streak['max_streak']
        except Exception as e:
            log_error(f"Error getting streak info: {e}")
        
        # 今日のログイン確認（シンプルな方法）
        try:
            with conn.cursor() as cur:
                today = datetime.now().date()
                cur.execute("""
                    SELECT id FROM login_history
                    WHERE user_id = %s AND login_date = %s
                """, (user_id, today))
                login_result = cur.fetchone()
                has_login_today = True if login_result else False
        except Exception as e:
            log_error(f"Error checking today's login: {e}")
            
        # 誕生日チェック
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT birthday FROM users WHERE id = %s", (user_id,))
                user_info = cur.fetchone()
                if user_info and user_info['birthday']:
                    today = datetime.now()
                    birthday = user_info['birthday']
                    # 同じ月ならば誕生日月
                    is_birthday_month = (birthday.month == today.month)
                    # 今年の誕生日が過ぎているかチェック
                    if today.month > birthday.month or (today.month == birthday.month and today.day >= birthday.day):
                        birthday_passed = True
        except Exception as e:
            log_error(f"Error checking birthday: {e}")
    except Exception as e:
        log_error(f"Database connection error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    
    # テンプレートをレンダリング
    return render_template(
        'student_points.html',
        name=student_name,
        total_points=total_points,
        point_history=point_history,
        current_streak=current_streak,
        max_streak=max_streak,
        has_login_today=has_login_today,
        monthly_attendance_rate=monthly_attendance_rate,
        is_birthday_month=is_birthday_month,
        birthday_passed=birthday_passed,
        teacher_view=teacher_view,
        student_id=user_id
    )

@app.route('/student/crane-game')
def student_crane_game():
    """生徒クレーンゲームプレイ権獲得画面"""
    # URLクエリパラメータから生徒IDを取得（講師用）
    requested_student_id = request.args.get('id', type=int)
    
    # ログインしていない場合はログイン画面へリダイレクト
    if not session.get('user_id'):
        return redirect('/myapp/index.cgi/login')
    
    # アクセス権限と表示する生徒を決定
    user_role = session.get('role')
    teacher_view = False
    
    if user_role == 'teacher':
        # 講師は任意の生徒のクレーンゲーム情報にアクセス可能
        if requested_student_id:
            user_id = requested_student_id
            teacher_view = True
            
            # この生徒のログインボーナスを処理
            conn = get_db_connection()
            try:
                # 生徒が存在するか確認し、名前を取得
                with conn.cursor() as cur:
                    cur.execute("SELECT name FROM users WHERE id = %s AND role = 'student'", (user_id,))
                    student = cur.fetchone()
                    if not student:
                        return "生徒が見つかりません", 404
                    student_name = student['name']
                
                # ログインボーナス処理
                is_first_login, points = process_login_and_award_points(conn, user_id)
            except Exception as e:
                log_error(f"生徒クレーンゲームの講師表示エラー: {e}")
            finally:
                conn.close()
        else:
            # 生徒IDが指定されていない場合
            return redirect('/myapp/index.cgi/teacher/dashboard')
    elif user_role == 'student':
        # 生徒は自分自身のクレーンゲーム情報のみアクセス可能
        user_id = session.get('user_id')
        student_name = session.get('user_name', '')
    else:
        # 不明な役割
        return redirect('/myapp/index.cgi/login')
    
    # 初期値を設定
    total_points = 0
    credits_history = []
    unused_credits = 0
    
    try:
        conn = get_db_connection()
        
        # 総ポイント取得
        try:
            total_points = get_user_total_points(conn, user_id)
        except Exception as e:
            log_error(f"Error getting total points: {e}")
        
        # クレジット履歴取得
        try:
            with conn.cursor() as cur:
                # クレーンゲームクレジットテーブルの存在確認
                cur.execute("SHOW TABLES LIKE 'crane_game_credits'")
                if not cur.fetchone():
                    # テーブルが存在しない場合は作成
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS crane_game_credits (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT NOT NULL,
                            point_history_id INT,
                            is_used TINYINT(1) NOT NULL DEFAULT 0,
                            used_at TIMESTAMP NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            INDEX(user_id),
                            INDEX(is_used)
                        )
                    """)
                    conn.commit()
                
                # 履歴を取得
                cur.execute("""
                    SELECT * FROM crane_game_credits
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 20
                """, (user_id,))
                credits_history = cur.fetchall() or []
                
                # 未使用のプレイ権数を取得
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM crane_game_credits
                    WHERE user_id = %s AND is_used = 0
                """, (user_id,))
                result = cur.fetchone()
                unused_credits = result['count'] if result else 0
        except Exception as e:
            log_error(f"Error getting credits history: {e}")
    except Exception as e:
        log_error(f"Database connection error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    
    # テンプレートをレンダリング
    return render_template(
        'student_crane_game.html',
        name=student_name,
        total_points=total_points,
        credits_history=credits_history,
        unused_credits=unused_credits,
        teacher_view=teacher_view,
        student_id=user_id
    )

# クレジット使用処理API
@app.route('/api/teacher/use-crane-game-credit', methods=['POST'])
def use_crane_game_credit():
    """クレーンゲームプレイ権を使用するAPI（講師用）"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'データが送信されていません'}), 400
    
    student_id = data.get('student_id')
    
    if not student_id:
        return jsonify({'success': False, 'message': '生徒IDが指定されていません'}), 400
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 未使用のクレジットを検索
            cur.execute("""
                SELECT id FROM crane_game_credits
                WHERE user_id = %s AND is_used = 0
                ORDER BY created_at ASC
                LIMIT 1
            """, (student_id,))
            
            credit = cur.fetchone()
            
            if not credit:
                return jsonify({'success': False, 'message': 'この生徒には未使用のプレイ権がありません'})
            
            # クレジットを使用済みに更新
            cur.execute("""
                UPDATE crane_game_credits
                SET is_used = 1, used_at = NOW()
                WHERE id = %s
            """, (credit['id'],))
            
            # 残りの未使用クレジット数を取得
            cur.execute("""
                SELECT COUNT(*) as count
                FROM crane_game_credits
                WHERE user_id = %s AND is_used = 0
            """, (student_id,))
            
            remaining = cur.fetchone()['count']
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'プレイ権を使用しました',
                'remaining_credits': remaining
            })
    
    except Exception as e:
        log_error(f"Error using crane game credit: {e}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({'success': False, 'message': 'エラーが発生しました: ' + str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# クレーンゲームプレイ権取得API
@app.route('/api/student/get-crane-game-credit', methods=['POST'])
def get_crane_game_credit():
    """クレーンゲームのプレイ権を取得するAPI"""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    user_id = request.json.get('student_id') if session.get('role') == 'teacher' else session.get('user_id')
    
    try:
        conn = get_db_connection()
        
        # 現在のポイントを確認
        total_points = get_user_total_points(conn, user_id)
        
        if total_points < 100:
            return jsonify({'success': False, 'message': 'ポイントが足りません'}), 400
        
        # ポイント消費記録を追加
        point_history_id = consume_points(
            conn, 
            user_id, 
            100, 
            'crane_game', 
            f"クレーンゲーム: プレイ権を獲得"
        )[1]  # 返り値の2番目の要素が history_id
        
        # クレーンゲームクレジット履歴に記録
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO crane_game_credits
                (user_id, point_history_id, is_used)
                VALUES (%s, %s, %s)
            """, (user_id, point_history_id, 0))  # 0 = 未使用
        
            conn.commit()
            
            # 未使用のプレイ権数を取得
            cur.execute("""
                SELECT COUNT(*) as count
                FROM crane_game_credits
                WHERE user_id = %s AND is_used = 0
            """, (user_id,))
            unused_credits = cur.fetchone()['count']
        
        # 残りのポイントを再計算
        remaining_points = get_user_total_points(conn, user_id)
        
        return jsonify({
            'success': True,
            'remaining_points': remaining_points,
            'unused_credits': unused_credits,
            'message': "クレーンゲームのプレイ権を獲得しました"
        })
    
    except Exception as e:
        log_error(f"Error in get_crane_game_credit: {e}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({'success': False, 'message': 'エラーが発生しました: ' + str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 講師用のクレーンゲームプレイ権管理画面
@app.route('/teacher/crane-game-credits')
def teacher_crane_game_credits():
    """講師用クレーンゲームプレイ権管理画面"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    # 検索パラメータ取得
    search_query = request.args.get('search', '')
    
    # 生徒一覧と未使用クレジット情報を取得
    students = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 検索条件に基づいて生徒を取得
            if search_query:
                query = """
                    SELECT u.id, u.name, u.grade_level, 
                           (SELECT COUNT(*) FROM crane_game_credits 
                            WHERE user_id = u.id AND is_used = 0) as unused_credits
                    FROM users u
                    WHERE u.role = 'student' AND u.name LIKE %s
                    ORDER BY u.grade_level, u.name
                """
                cur.execute(query, (f"%{search_query}%",))
            else:
                query = """
                    SELECT u.id, u.name, u.grade_level, 
                           (SELECT COUNT(*) FROM crane_game_credits 
                            WHERE user_id = u.id AND is_used = 0) as unused_credits
                    FROM users u
                    WHERE u.role = 'student'
                    ORDER BY u.grade_level, u.name
                """
                cur.execute(query)
            
            students = cur.fetchall() or []
    except Exception as e:
        log_error(f"Error getting students with credits: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    
    return render_template(
        'teacher_crane_game_credits.html',
        name=session.get('user_name', ''),
        students=students,
        search_query=search_query
    )

# クレーンゲーム景品交換API
@app.route('/api/student/redeem-prize', methods=['POST'])
def redeem_prize():
    """クレーンゲーム景品交換API"""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
        
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'データが送信されていません'}), 400
    
    user_id = data.get('student_id') if session.get('role') == 'teacher' else session.get('user_id')
    prize_id = data.get('prize_id')
    comments = data.get('comments', '')
    
    if not prize_id:
        return jsonify({'success': False, 'message': '景品IDが指定されていません'}), 400
    
    try:
        conn = get_db_connection()
        
        # 景品情報を取得
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM crane_game_prizes WHERE id = %s", (prize_id,))
            prize = cur.fetchone()
            
            if not prize:
                return jsonify({'success': False, 'message': '指定された景品が見つかりません'})
            
            if prize['stock'] <= 0:
                return jsonify({'success': False, 'message': 'この景品は在庫切れです'})
            
            point_cost = prize['point_cost']
            
            # 現在のポイント残高を確認
            cur.execute("""
                SELECT COALESCE(SUM(points), 0) as total_points
                FROM point_history
                WHERE user_id = %s AND is_active = 1
            """, (user_id,))
            
            result = cur.fetchone()
            total_points = int(result['total_points']) if result else 0
            
            if total_points < point_cost:
                return jsonify({'success': False, 'message': 'ポイントが不足しています'})
            
            # ポイント消費記録を追加
            cur.execute("""
                INSERT INTO point_history (user_id, points, event_type, comment)
                VALUES (%s, %s, %s, %s)
            """, (user_id, -point_cost, 'crane_game', f"クレーンゲーム: {prize['name']}を獲得"))
            
            point_history_id = cur.lastrowid
            
            # 景品履歴に記録
            cur.execute("""
                INSERT INTO crane_game_history (user_id, prize_id, point_history_id, comments)
                VALUES (%s, %s, %s, %s)
            """, (user_id, prize_id, point_history_id, comments))
            
            # 在庫を減らす
            cur.execute("""
                UPDATE crane_game_prizes
                SET stock = stock - 1
                WHERE id = %s
            """, (prize_id,))
            
            # 更新後のポイント残高を取得
            cur.execute("""
                SELECT COALESCE(SUM(points), 0) as total_points
                FROM point_history
                WHERE user_id = %s AND is_active = 1
            """, (user_id,))
            
            result = cur.fetchone()
            new_total_points = int(result['total_points']) if result else 0
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f"{prize['name']}を獲得しました！",
                'total_points': new_total_points
            })
    
    except Exception as e:
        log_error(f"Error in redeem_prize: {e}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({'success': False, 'message': 'エラーが発生しました: ' + str(e)})
    
    finally:
        if 'conn' in locals():
            conn.close()

# イベントタイプテーブルを作成する関数
def create_event_types_table(conn):
    """point_event_typesテーブルを作成する"""
    try:
        with conn.cursor() as cur:
            # テーブル作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS point_event_types (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    display_name VARCHAR(100) NOT NULL,
                    description TEXT,
                    min_points INT NOT NULL DEFAULT 0,
                    max_points INT NOT NULL DEFAULT 0,
                    teacher_can_award TINYINT(1) NOT NULL DEFAULT 0,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            log_error("point_event_typesテーブルを作成しました")
            conn.commit()
    except Exception as e:
        log_error(f"Error creating point_event_types table: {e}")
        conn.rollback()

# デフォルトのイベントタイプを挿入する関数
def insert_default_event_types(conn):
    """デフォルトのイベントタイプを挿入する"""
    try:
        with conn.cursor() as cur:
            # デフォルトのイベントタイプを挿入
            event_types = [
                ('login', 'ログインボーナス', '毎日のログインでポイント獲得', 3, 10, 0),
                ('streak_5', '5日連続ログイン', '5日連続ログインのボーナス', 20, 20, 0),
                ('streak_10', '10日連続ログイン', '10日連続ログインのボーナス', 50, 50, 0),
                ('streak_30', '30日連続ログイン', '30日連続ログインのボーナス', 150, 150, 0),
                ('birthday', '誕生日ボーナス', 'お誕生日記念ボーナス', 100, 100, 0),
                ('attendance_90', '月間90%出席ボーナス', '月間出席率90%以上達成ボーナス', 50, 50, 0),
                ('attendance_100', '皆勤賞', '月間出席率100%達成ボーナス', 100, 100, 0),
                ('grade_improvement_small', '成績向上ボーナス(小)', '前回より5点以上成績アップ', 20, 20, 0),
                ('grade_improvement_medium', '成績向上ボーナス(中)', '前回より10点以上成績アップ', 30, 30, 0),
                ('grade_improvement_large', '成績向上ボーナス(大)', '前回より15点以上成績アップ', 50, 50, 0),
                ('homework', '宿題提出ボーナス', '宿題提出ごとに獲得', 10, 10, 1),
                ('exam_result', '試験結果ボーナス', '試験結果に応じたボーナス', 10, 100, 1),
                ('mock_exam', '模試ボーナス', '模試結果に応じたボーナス', 10, 100, 1),
                ('special_award', '特別ボーナス', '特別な活動や成果に対するボーナス', 10, 500, 1),
                ('crane_game', 'クレーンゲーム', 'クレーンゲームでの景品交換', 0, 0, 0)
            ]
            
            for event_type in event_types:
                # REPLACE INTOを使用してINSERTまたはUPDATE
                cur.execute("""
                    INSERT INTO point_event_types
                    (name, display_name, description, min_points, max_points, teacher_can_award)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    display_name = VALUES(display_name),
                    description = VALUES(description),
                    min_points = VALUES(min_points),
                    max_points = VALUES(max_points),
                    teacher_can_award = VALUES(teacher_can_award),
                    is_active = 1
                """, event_type)
            
            log_error("デフォルトのイベントタイプを挿入しました")
            conn.commit()
    except Exception as e:
        log_error(f"Error inserting default event types: {e}")
        conn.rollback()

@app.route('/teacher/points', methods=['GET', 'POST'])
def teacher_points():
    """講師ポイント管理ページ（修正版）"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    # 教師IDを取得
    teacher_id = session.get('user_id')
    error = None
    success = None
    
    # POSTリクエスト処理（ポイント付与）
    if request.method == 'POST':
        try:
            # リクエストデータ取得
            action = request.form.get('action')
            
            # デバッグログ
            app.logger.info(f"POSTリクエスト受信: action={action}")
            app.logger.info(f"フォームデータ: {request.form}")
            
            if action == 'award_points':
                # フォームデータ取得
                student_id = request.form.get('student_id')
                event_type = request.form.get('event_type')
                points = request.form.get('points', type=int)
                comment = request.form.get('comment', '')
                
                # 入力検証
                if not all([student_id, event_type, points]):
                    error = "必須項目が入力されていません"
                    app.logger.error(f"入力検証エラー: student_id={student_id}, event_type={event_type}, points={points}")
                else:
                    # データベース接続
                    conn = get_db_connection()
                    try:
                        # ポイント付与処理を明示的なトランザクションで実行
                        conn.begin()
                        
                        # points_utils.pyのteacher_award_points関数を呼び出し
                        award_success, message = teacher_award_points(
                            conn=conn,
                            teacher_id=teacher_id,
                            student_id=student_id,
                            event_type=event_type,
                            points=points,
                            comment=comment
                        )
                        
                        if award_success:
                            # 成功時はコミット
                            conn.commit()
                            success = f"ポイントを付与しました: {message}"
                            app.logger.info(f"ポイント付与成功: {message}")
                        else:
                            # 失敗時はロールバック
                            conn.rollback()
                            error = f"ポイント付与エラー: {message}"
                            app.logger.error(f"ポイント付与失敗: {message}")
                    except Exception as e:
                        # エラー時はロールバック
                        conn.rollback()
                        error = f"データベースエラー: {str(e)}"
                        app.logger.error(f"ポイント付与中のデータベースエラー: {e}")
                    finally:
                        conn.close()
                        
            # その他のアクション処理...
        except Exception as e:
            error = f"処理エラー: {str(e)}"
            app.logger.error(f"ポイント処理中の予期せぬエラー: {e}")
    
    # 生徒一覧を取得
    students = []
    event_types = []
    point_history = []
    
    try:
        conn = get_db_connection()
        
        # 生徒一覧を取得
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, grade_level
                    FROM users
                    WHERE role = 'student'
                    ORDER BY grade_level, name
                """)
                students = cur.fetchall() or []
        except Exception as e:
            app.logger.error(f"生徒情報取得エラー: {e}")
            error = "生徒情報の取得に失敗しました"
        
        # イベントタイプを取得（修正版）
        try:
            with conn.cursor() as cur:
                # イベントタイプテーブルの存在確認
                cur.execute("SHOW TABLES LIKE 'point_event_types'")
                if not cur.fetchone():
                    app.logger.error("point_event_typesテーブルが存在しません")
                    error = "イベントタイプテーブルが存在しません"
                else:
                    # is_activeカラムの存在確認
                    cur.execute("SHOW COLUMNS FROM point_event_types LIKE 'is_active'")
                    has_is_active = cur.fetchone() is not None
                    
                    # クエリ構築（is_activeカラムの有無に応じて変更）
                    if has_is_active:
                        query = """
                            SELECT name, display_name, min_points, max_points
                            FROM point_event_types
                            WHERE teacher_can_award = 1 AND is_active = 1
                            ORDER BY display_name
                        """
                    else:
                        query = """
                            SELECT name, display_name, min_points, max_points
                            FROM point_event_types
                            WHERE teacher_can_award = 1
                            ORDER BY display_name
                        """
                    
                    # クエリ実行
                    cur.execute(query)
                    event_types = cur.fetchall() or []
                    
                    # ログに記録
                    app.logger.info(f"取得したイベントタイプ: {len(event_types)}件")
                    
                    # イベントタイプが取得できなかった場合
                    if not event_types:
                        app.logger.warning("イベントタイプが取得できませんでした。デフォルト値を使用します。")
                        # デフォルト値を設定
                        event_types = [
                            {'name': 'homework', 'display_name': '宿題提出ボーナス', 'min_points': 10, 'max_points': 10},
                            {'name': 'exam_result', 'display_name': '試験結果ボーナス', 'min_points': 10, 'max_points': 100},
                            {'name': 'mock_exam', 'display_name': '模試ボーナス', 'min_points': 10, 'max_points': 100},
                            {'name': 'special_award', 'display_name': '特別ボーナス', 'min_points': 10, 'max_points': 500}
                        ]
        except Exception as e:
            app.logger.error(f"イベントタイプ取得エラー: {e}")
            error = "イベントタイプの取得に失敗しました"
            # エラーが発生した場合でもデフォルト値を設定
            event_types = [
                {'name': 'homework', 'display_name': '宿題提出ボーナス', 'min_points': 10, 'max_points': 10},
                {'name': 'exam_result', 'display_name': '試験結果ボーナス', 'min_points': 10, 'max_points': 100},
                {'name': 'mock_exam', 'display_name': '模試ボーナス', 'min_points': 10, 'max_points': 100},
                {'name': 'special_award', 'display_name': '特別ボーナス', 'min_points': 10, 'max_points': 500}
            ]
        
        # ポイント履歴を取得
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ph.*, u.name as user_name, 
                           COALESCE(pe.display_name, ph.event_type) as event_display_name, 
                           t.name as created_by_name
                    FROM point_history ph
                    JOIN users u ON ph.user_id = u.id
                    LEFT JOIN point_event_types pe ON ph.event_type = pe.name
                    LEFT JOIN users t ON ph.created_by = t.id
                    ORDER BY ph.created_at DESC
                    LIMIT 100
                """)
                point_history = cur.fetchall() or []
        except Exception as e:
            app.logger.error(f"ポイント履歴取得エラー: {e}")
            error = "ポイント履歴の取得に失敗しました"
    except Exception as e:
        app.logger.error(f"データベース接続エラー: {e}")
        error = "データベース接続エラー"
    finally:
        if 'conn' in locals():
            conn.close()
    
    # テンプレートをレンダリング
    return render_template(
        'teacher_points.html',
        name=session.get('user_name', ''),
        students=students,
        event_types=event_types,
        point_history=point_history,
        error=error,
        success=success
    )

@app.route('/api/student/points')
def get_student_points_api():
    """生徒のポイント情報を取得するAPI"""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    # クエリパラメータから生徒IDを取得（講師用）
    student_id = request.args.get('student_id', type=int)
    
    # ユーザーIDを決定
    if session.get('role') == 'teacher' and student_id:
        user_id = student_id
    else:
        user_id = session.get('user_id')
    
    try:
        conn = get_db_connection()
        total_points = get_user_total_points(conn, user_id)
        
        # 講師モードで生徒IDが指定されている場合、生徒名も取得
        student_name = None
        if session.get('role') == 'teacher' and student_id:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM users WHERE id = %s AND role = 'student'", (student_id,))
                student = cur.fetchone()
                if student:
                    student_name = student['name']
        
        result = {
            'success': True,
            'total_points': total_points
        }
        
        # 生徒名が取得できた場合は追加
        if student_name:
            result['student_name'] = student_name
        
        return jsonify(result)
    except Exception as e:
        log_error(f"Error getting points: {e}")
        return jsonify({'success': False, 'message': 'エラーが発生しました'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/debug/event-types')
def debug_event_types():
    """イベントタイプテーブルの状態を確認"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    debug_info = {
        'table_exists': False,
        'records': [],
        'error': None
    }
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # テーブルの存在確認
            try:
                cur.execute("SHOW TABLES LIKE 'point_event_types'")
                if cur.fetchone():
                    debug_info['table_exists'] = True
                else:
                    debug_info['error'] = "point_event_typesテーブルが存在しません"
                    return jsonify(debug_info)
            except Exception as e:
                debug_info['error'] = f"テーブル確認エラー: {str(e)}"
                return jsonify(debug_info)
            
            # レコード確認
            try:
                cur.execute("SELECT * FROM point_event_types")
                records = cur.fetchall()
                debug_info['records'] = [dict(r) for r in records]
                debug_info['record_count'] = len(records)
            except Exception as e:
                debug_info['error'] = f"レコード取得エラー: {str(e)}"
                return jsonify(debug_info)
            
            # 講師が付与可能なイベントタイプの確認
            try:
                cur.execute("SELECT * FROM point_event_types WHERE teacher_can_award = 1")
                teacher_records = cur.fetchall()
                debug_info['teacher_events'] = [dict(r) for r in teacher_records]
                debug_info['teacher_event_count'] = len(teacher_records)
            except Exception as e:
                debug_info['error'] = f"講師イベント取得エラー: {str(e)}"
                return jsonify(debug_info)
    except Exception as e:
        debug_info['error'] = f"データベース接続エラー: {str(e)}"
    finally:
        if 'conn' in locals():
            conn.close()
    
    return jsonify(debug_info)

# イベントタイプのデータを挿入・更新するエンドポイント
@app.route('/admin/reset-event-types')
def reset_event_types():
    """イベントタイプテーブルのデータをリセット"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    result = {
        'success': False,
        'message': '',
        'error': None,
        'records_added': 0
    }
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # テーブルの存在確認、なければ作成
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS point_event_types (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50) NOT NULL UNIQUE,
                        display_name VARCHAR(100) NOT NULL,
                        description TEXT,
                        min_points INT NOT NULL DEFAULT 0,
                        max_points INT NOT NULL DEFAULT 0,
                        teacher_can_award TINYINT(1) NOT NULL DEFAULT 0,
                        is_active TINYINT(1) NOT NULL DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
            except Exception as e:
                result['error'] = f"テーブル作成エラー: {str(e)}"
                return jsonify(result)
            
            # データを挿入（既存のレコードは更新）
            event_types = [
                ('login', 'ログインボーナス', '毎日のログインでポイント獲得', 3, 10, 0),
                ('streak_5', '5日連続ログイン', '5日連続ログインのボーナス', 20, 20, 0),
                ('streak_10', '10日連続ログイン', '10日連続ログインのボーナス', 50, 50, 0),
                ('streak_30', '30日連続ログイン', '30日連続ログインのボーナス', 150, 150, 0),
                ('birthday', '誕生日ボーナス', 'お誕生日記念ボーナス', 100, 100, 0),
                ('attendance_90', '月間90%出席ボーナス', '月間出席率90%以上達成ボーナス', 50, 50, 0),
                ('attendance_100', '皆勤賞', '月間出席率100%達成ボーナス', 100, 100, 0),
                ('grade_improvement_small', '成績向上ボーナス(小)', '前回より5点以上成績アップ', 20, 20, 0),
                ('grade_improvement_medium', '成績向上ボーナス(中)', '前回より10点以上成績アップ', 30, 30, 0),
                ('grade_improvement_large', '成績向上ボーナス(大)', '前回より15点以上成績アップ', 50, 50, 0),
                ('homework', '宿題提出ボーナス', '宿題提出ごとに獲得', 10, 10, 1),
                ('exam_result', '試験結果ボーナス', '試験結果に応じたボーナス', 10, 100, 1),
                ('mock_exam', '模試ボーナス', '模試結果に応じたボーナス', 10, 100, 1),
                ('special_award', '特別ボーナス', '特別な活動や成果に対するボーナス', 10, 500, 1),
                ('crane_game', 'クレーンゲーム', 'クレーンゲームでの景品交換', 0, 0, 0)
            ]
            
            count = 0
            for event_type in event_types:
                try:
                    # 既存のレコードをチェック
                    cur.execute("SELECT id FROM point_event_types WHERE name = %s", (event_type[0],))
                    existing = cur.fetchone()
                    
                    if existing:
                        # 更新
                        cur.execute("""
                            UPDATE point_event_types
                            SET display_name = %s,
                                description = %s,
                                min_points = %s,
                                max_points = %s,
                                teacher_can_award = %s,
                                is_active = 1
                            WHERE name = %s
                        """, (event_type[1], event_type[2], event_type[3], event_type[4], event_type[5], event_type[0]))
                    else:
                        # 挿入
                        cur.execute("""
                            INSERT INTO point_event_types
                            (name, display_name, description, min_points, max_points, teacher_can_award)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, event_type)
                    
                    count += 1
                except Exception as e:
                    result['error'] = f"レコード {event_type[0]} の処理中にエラー: {str(e)}"
                    # 続行する
            
            result['records_added'] = count
            result['success'] = True
            result['message'] = f"{count} 件のイベントタイプを正常に処理しました"
        
        conn.commit()
    except Exception as e:
        result['error'] = f"データベース処理エラー: {str(e)}"
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()
    
    return jsonify(result)

# 内部サーバーエラーのハンドラー
@app.errorhandler(500)
def internal_error(error):
    """内部サーバーエラーのハンドラー"""
    return render_template('error.html', 
        error="内部サーバーエラーが発生しました。管理者にお問い合わせください。", 
        back_url="/myapp/index.cgi/student/high-schools"), 500

# 特定の高校情報をデバッグ表示するルート
@app.route('/debug/high-school/<int:school_id>')
def debug_high_school(school_id):
    """高校情報のデバッグ表示"""
    if not session.get('user_id'):
        return "ログインが必要です", 401
    
    result = {
        'school_id': school_id,
        'db_info': {},
        'school_data': None,
        'errors': []
    }
    
    try:
        # データベース接続
        conn = get_db_connection()
        
        # データベース情報を取得
        with conn.cursor() as cur:
            # テーブル存在確認
            cur.execute("SHOW TABLES LIKE 'high_schools'")
            result['db_info']['high_schools_exists'] = cur.fetchone() is not None
            
            # カラム情報を取得
            if result['db_info']['high_schools_exists']:
                cur.execute("DESCRIBE high_schools")
                columns = cur.fetchall()
                result['db_info']['columns'] = [col['Field'] for col in columns]
                
                # 高校数を取得
                cur.execute("SELECT COUNT(*) as count FROM high_schools")
                count = cur.fetchone()
                result['db_info']['total_records'] = count['count'] if count else 0
        
        # 高校情報を取得
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM high_schools WHERE id = %s", (school_id,))
            school = cur.fetchone()
            
            if school:
                # 辞書に変換（JSONシリアライズ可能にする）
                school_dict = {}
                for key, value in school.items():
                    if isinstance(value, (int, float, str, bool, type(None))):
                        school_dict[key] = value
                    else:
                        # 非シリアライズ可能な型は文字列化
                        school_dict[key] = str(value)
                
                result['school_data'] = school_dict
            else:
                result['errors'].append(f"ID {school_id} の高校が見つかりません")
    except Exception as e:
        result['errors'].append(f"エラー: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()
    
    # デバッグ情報をHTML形式で表示
    debug_html = f"""
    <html>
    <head>
        <title>高校情報デバッグ</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; }}
            pre {{ background: #f5f5f5; padding: 10px; border-radius: 5px; overflow: auto; }}
            .error {{ color: red; }}
        </style>
    </head>
    <body>
        <h1>高校ID: {school_id} のデバッグ情報</h1>
        
        <h2>データベース情報</h2>
        <pre>{str(result['db_info'])}</pre>
        
        <h2>高校データ</h2>
        <pre>{str(result['school_data'])}</pre>
        
        <h2>エラー</h2>
        {'<p class="error">エラーなし</p>' if not result['errors'] else ''}
        {''.join([f'<p class="error">{error}</p>' for error in result['errors']])}
        
        <hr>
        <p><a href="/myapp/index.cgi/student/high-schools">高校一覧に戻る</a></p>
    </body>
    </html>
    """
    
    return debug_html

@app.route('/direct/high-school/<int:school_id>')
def direct_high_school_detail(school_id):
    """テンプレートを使わずに直接HTMLを返す高校詳細表示"""
    if not session.get('user_id'):
        return redirect('/myapp/index.cgi/login')
    
    try:
        # データベース接続
        conn = get_db_connection()
        school = None
        
        # 高校情報を取得
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM high_schools WHERE id = %s", (school_id,))
                school = cur.fetchone()
        except Exception as e:
            return f"""
            <html>
            <body>
                <h1>データ取得エラー</h1>
                <p>エラー: {str(e)}</p>
                <p><a href="/myapp/index.cgi/student/high-schools">戻る</a></p>
            </body>
            </html>
            """
        finally:
            conn.close()
        
        if not school:
            log_error(f"高校ID {school_id} が見つかりません。(direct route)")
            return render_template('error.html',
                error=f"高校情報が見つかりません（ID: {school_id}）", 
                back_url="/myapp/index.cgi/student/high-schools")
        
        # データを直接HTMLで表示
        school_html = f"""
        <html>
        <head>
            <title>{school['name']} 詳細</title>
            <style>
                body {{ font-family: sans-serif; padding: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>高校詳細: {school['name']}</h1>
            
            <table>
                <tr><th>ID</th><td>{school['id']}</td></tr>
                <tr><th>名称</th><td>{school['name']}</td></tr>
                <tr><th>地区</th><td>{school.get('district', '-')}</td></tr>
                <tr><th>コース</th><td>{school.get('course_type', '-')}</td></tr>
                <tr><th>偏差値</th><td>{school.get('deviation_score', '-')}</td></tr>
                <tr><th>最低必要内申点</th><td>{school.get('min_required_points', '-')}</td></tr>
                <tr><th>倍率</th><td>{school.get('competition_rate', '-')}</td></tr>
            </table>
            
            <p><a href="/myapp/index.cgi/student/high-schools">高校一覧に戻る</a></p>
        </body>
        </html>
        """
        
        return school_html
        
    except Exception as e:
        # 何らかの予期せぬエラーが発生した場合
        error_html = f"""
        <html>
        <body>
            <h1>エラーが発生しました</h1>
            <p>エラー: {str(e)}</p>
            <p><a href="/myapp/index.cgi/student/high-schools">戻る</a></p>
        </body>
        </html>
        """
        return error_html

# 超基本的なテスト用ルート（テンプレートもDBも使わないバージョン）

@app.route('/test/basic')
def test_basic():
    """最も基本的なテスト - 単純なテキスト応答を返すだけ"""
    return "基本機能テスト - 成功しました"

@app.route('/test/session')
def test_session():
    """セッションを使用するテスト"""
    if not session.get('test_count'):
        session['test_count'] = 1
    else:
        session['test_count'] += 1
    
    return f"セッションテスト - カウント: {session.get('test_count')}"

@app.route('/test/db')
def test_db():
    """データベース接続テスト"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 as test")
            result = cur.fetchone()
        conn.close()
        
        return f"データベース接続テスト - 成功: {result['test']}"
    except Exception as e:
        return f"データベース接続テスト - 失敗: {str(e)}"

@app.route('/test/high-schools')
def test_high_schools():
    """高校テーブルのテスト"""
    try:
        output = []
        
        conn = get_db_connection()
        # テーブル存在確認
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES LIKE 'high_schools'")
            if cur.fetchone():
                output.append("high_schoolsテーブルが存在します")
                
                # カラム確認
                cur.execute("DESCRIBE high_schools")
                columns = [row['Field'] for row in cur.fetchall()]
                output.append(f"カラム: {', '.join(columns)}")
                
                # データ件数確認
                cur.execute("SELECT COUNT(*) as count FROM high_schools")
                count = cur.fetchone()['count']
                output.append(f"データ件数: {count}")
                
                # サンプルデータ取得
                if count > 0:
                    cur.execute("SELECT id, name FROM high_schools LIMIT 5")
                    schools = cur.fetchall()
                    for school in schools:
                        output.append(f"ID: {school['id']}, 名前: {school['name']}")
            else:
                output.append("high_schoolsテーブルが存在しません")
        conn.close()
        
        return "<br>".join(output)
    except Exception as e:
        return f"高校テーブルテスト - 失敗: {str(e)}"

@app.route('/test/direct')
def test_direct():
    """単純なHTMLを直接出力するテスト"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>直接HTML出力テスト</title>
    </head>
    <body>
        <h1>直接HTML出力テスト</h1>
        <p>このページはテンプレートを使わずに直接HTMLを出力しています。</p>
        <ul>
            <li><a href="/myapp/index.cgi/test/basic">基本テスト</a></li>
            <li><a href="/myapp/index.cgi/test/session">セッションテスト</a></li>
            <li><a href="/myapp/index.cgi/test/db">データベーステスト</a></li>
            <li><a href="/myapp/index.cgi/test/high-schools">高校テーブルテスト</a></li>
        </ul>
    </body>
    </html>
    """
    return html

@app.route('/test/log-error')
def test_log_error():
    """エラーログテスト"""
    try:
        # 意図的にエラーを発生させる
        result = 1 / 0
    except Exception as e:
        log_error(f"テスト用エラー: {str(e)}")
        return "エラーログに書き込みました。ログファイルを確認してください。"

# データベース修復スクリプト
@app.route('/admin/db-repair')
def db_repair():
    """データベース修復ツール"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return "この機能は講師のみ使用できます", 403
    
    results = []
    
    try:
        conn = get_db_connection()
        
        # 1. user_high_school_preferences テーブルの修復
        try:
            with conn.cursor() as cur:
                # テーブル存在確認
                cur.execute("SHOW TABLES LIKE 'user_high_school_preferences'")
                if not cur.fetchone():
                    # テーブルがなければ作成
                    cur.execute("""
                        CREATE TABLE user_high_school_preferences (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT NOT NULL,
                            high_school_id INT NOT NULL,
                            preference_order INT NOT NULL DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            UNIQUE KEY(user_id, high_school_id)
                        )
                    """)
                    results.append("user_high_school_preferences テーブルを作成しました")
                else:
                    results.append("user_high_school_preferences テーブルは既に存在します")
        except Exception as e:
            results.append(f"user_high_school_preferences テーブルの修復中にエラー: {str(e)}")
        
        # 2. subjects テーブルの修復
        try:
            with conn.cursor() as cur:
                # テーブル存在確認
                cur.execute("SHOW TABLES LIKE 'subjects'")
                if not cur.fetchone():
                    # テーブルがなければ作成
                    cur.execute("""
                        CREATE TABLE subjects (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            name VARCHAR(50) NOT NULL,
                            is_main TINYINT(1) NOT NULL DEFAULT 0,
                            display_order INT NOT NULL DEFAULT 0,
                            is_active TINYINT(1) NOT NULL DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # 基本データ挿入
                    cur.execute("""
                        INSERT INTO subjects (id, name, is_main, display_order) VALUES 
                        (1, '国語', 1, 1),
                        (2, '数学', 1, 2),
                        (3, '英語', 1, 3),
                        (4, '理科', 1, 4),
                        (5, '社会', 1, 5),
                        (6, '音楽', 0, 6),
                        (7, '美術', 0, 7),
                        (8, '体育', 0, 8),
                        (9, '技家', 0, 9)
                    """)
                    
                    results.append("subjects テーブルを作成し、基本データを挿入しました")
                else:
                    results.append("subjects テーブルは既に存在します")
        except Exception as e:
            results.append(f"subjects テーブルの修復中にエラー: {str(e)}")
        
        
        try:
            with conn.cursor() as cur:
                # テーブル存在確認
                cur.execute("SHOW TABLES LIKE 'internal_points'")
                if not cur.fetchone():
                    # テーブルがなければ作成
                    cur.execute("""
                        CREATE TABLE internal_points (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            student_id INT NOT NULL,
                            grade_year INT NOT NULL,
                            subject INT NOT NULL,
                            term INT NOT NULL,
                            point INT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            UNIQUE KEY(student_id, grade_year, subject, term)
                        )
                    """)
                    results.append("internal_points テーブルを作成しました")
                else:
                    results.append("internal_points テーブルは既に存在します")
        except Exception as e:
            results.append(f"internal_points テーブルの修復中にエラー: {str(e)}")
        
        # 4. high_schools テーブルのサンプルデータ
        try:
            with conn.cursor() as cur:
                # データ件数確認
                cur.execute("SELECT COUNT(*) as count FROM high_schools")
                count = cur.fetchone()['count']
                
                if count == 0:
                    # サンプルデータを挿入
                    cur.execute("""
                        INSERT INTO high_schools 
                        (name, district, course_type, min_required_points, deviation_score, competition_rate, year) 
                        VALUES 
                        ('サンプル高校1', '神奈川県', '普通科', 40.0, 60.0, 1.2, 2025),
                        ('サンプル高校2', '神奈川県', '普通科', 35.0, 55.0, 1.1, 2025)
                    """)
                    results.append("high_schools テーブルにサンプルデータを追加しました")
                else:
                    results.append(f"high_schools テーブルには既にデータがあります（{count}件）")
        except Exception as e:
            results.append(f"high_schools テーブルのデータ追加中にエラー: {str(e)}")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        results.append(f"データベース接続エラー: {str(e)}")
    
    # 結果をHTMLで表示
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>データベース修復結果</title>
        <style>
            body { font-family: sans-serif; padding: 20px; }
            .success { color: green; }
            .error { color: red; }
            h1 { color: #333; }
            ul { line-height: 1.6; }
            a { color: blue; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>データベース修復結果</h1>
        <ul>
    """
    
    for result in results:
        error = "エラー" in result
        html += f'<li class="{"error" if error else "success"}">{result}</li>'
    
    html += """
        </ul>
        <p><a href="/myapp/index.cgi/test/direct">テストページに戻る</a></p>
        <p><a href="/myapp/index.cgi/teacher/dashboard">ダッシュボードに戻る</a></p>
    </body>
    </html>
    """
    
    return html

@app.route('/student/points-basic')
def student_points_basic():
    """超シンプルなポイント表示（エラー診断用）"""
    html = (
        "<html>"
        "<head><title>ポイント</title></head>"
        "<body>"
        "<h1>ポイント情報 - シンプル版</h1>"
        "<p>シンプル表示テスト</p>"
        "<a href='/myapp/index.cgi/student/dashboard'>ダッシュボードに戻る</a>"
        "</body>"
        "</html>"
    )
    return html

@app.route('/student/crane-game-basic')
def student_crane_game_basic():
    """超シンプルなクレーンゲーム表示（エラー診断用）"""
    return """
    <html>
    <head><title>クレーンゲーム</title></head>
    <body>
        <h1>クレーンゲーム - シンプル版</h1>
        <p>シンプル表示テスト</p>
        <a href="/myapp/index.cgi/student/dashboard">ダッシュボードに戻る</a>
    </body>
    </html>
    """

@app.route('/api/teacher/notification-count')
def teacher_notification_count():
    """未処理の成績向上通知数を取得するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        count = 0
        
        with conn.cursor() as cur:
            # 通知テーブルの存在確認
            cur.execute("SHOW TABLES LIKE 'grade_improvement_notifications'")
            if cur.fetchone():
                # 未処理の通知数を取得
                cur.execute("""
                    SELECT COUNT(*) as count 
                    FROM grade_improvement_notifications 
                    WHERE is_processed = 0
                """)
                result = cur.fetchone()
                count = result['count'] if result else 0
        
        conn.close()
        return jsonify({'count': count})
    
    except Exception as e:
        log_error(f"Error getting notification count: {e}")
        return jsonify({'error': str(e)}), 500

# 成績向上通知ページ
@app.route('/teacher/grade-notifications', methods=['GET', 'POST'])
def teacher_grade_notifications():
    """講師用の成績向上通知ページ"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    teacher_id = session.get('user_id')
    error = None
    success = None
    
    # POSTリクエスト処理（ポイント付与）
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'award_points':
            notification_id = request.form.get('notification_id')
            student_id = request.form.get('student_id')
            points = request.form.get('points', type=int)
            
            if not all([notification_id, student_id, points]):
                error = "必要な情報が不足しています"
            else:
                try:
                    conn = get_db_connection()
                    
                    # 通知情報の取得
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT n.*, s.name as subject_name
                            FROM grade_improvement_notifications n
                            JOIN subjects s ON n.subject_id = s.id
                            WHERE n.id = %s AND n.is_processed = 0
                        """, (notification_id,))
                        
                        notification = cur.fetchone()
                        
                        if not notification:
                            error = "通知が見つからないか、既に処理されています"
                        else:
                            # ポイント付与
                            level = notification['improvement_level']
                            event_type = f"grade_improvement_{level.lower()}"
                            comment = f"成績向上ボーナス（{level}）: {notification['subject_name']}が{notification['previous_score']}点から{notification['new_score']}点に向上"
                            
                            # teacher_award_points関数を呼び出し
                            success, message = teacher_award_points(
                                conn,
                                teacher_id,
                                student_id,
                                event_type,
                                points,
                                comment
                            )
                            
                            if success:
                                # 通知を処理済みに更新
                                cur.execute("""
                                    UPDATE grade_improvement_notifications
                                    SET is_processed = 1,
                                        processed_by = %s,
                                        processed_at = NOW()
                                    WHERE id = %s
                                """, (teacher_id, notification_id))
                                
                                conn.commit()
                                success = "ポイントを付与し、通知を処理済みにしました"
                            else:
                                error = f"ポイント付与エラー: {message}"
                except Exception as e:
                    log_error(f"Error processing grade notification: {e}")
                    error = f"処理エラー: {str(e)}"
                finally:
                    if 'conn' in locals():
                        conn.close()
    
    # 成績向上通知の取得
    notifications = []
    unprocessed_count = 0
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 通知テーブルの存在確認
            cur.execute("SHOW TABLES LIKE 'grade_improvement_notifications'")
            if not cur.fetchone():
                # テーブルが存在しない場合は作成
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS grade_improvement_notifications (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        student_id INT NOT NULL,
                        grade_year INT NOT NULL,
                        subject_id INT NOT NULL,
                        term INT NOT NULL,
                        previous_score INT NOT NULL,
                        new_score INT NOT NULL,
                        improvement_level VARCHAR(10) NOT NULL,
                        potential_points INT NOT NULL,
                        is_processed TINYINT(1) NOT NULL DEFAULT 0,
                        processed_by INT NULL,
                        processed_at TIMESTAMP NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX(student_id),
                        INDEX(is_processed)
                    )
                """)
                conn.commit()
            
            # 通知データを取得
            cur.execute("""
                SELECT n.*, 
                       u.name as student_name, 
                       s.name as subject_name,
                       t.name as teacher_name
                FROM grade_improvement_notifications n
                JOIN users u ON n.student_id = u.id
                JOIN subjects s ON n.subject_id = s.id
                LEFT JOIN users t ON n.processed_by = t.id
                ORDER BY n.is_processed ASC, n.created_at DESC
            """)
            
            notifications = cur.fetchall() or []
            
            # 未処理の通知数を取得
            cur.execute("""
                SELECT COUNT(*) as count
                FROM grade_improvement_notifications
                WHERE is_processed = 0
            """)
            
            result = cur.fetchone()
            unprocessed_count = result['count'] if result else 0
    except Exception as e:
        log_error(f"Error fetching grade notifications: {e}")
        error = f"通知の取得エラー: {str(e)}"
    finally:
        if 'conn' in locals():
            conn.close()
    
    # データがない場合はテスト用データを生成
    if not notifications:
        notifications = generate_sample_notifications()
        unprocessed_count = sum(1 for n in notifications if not n['is_processed'])
    
    return render_template(
        'teacher_grade_notifications.html',
        name=session.get('user_name', ''),
        notifications=notifications,
        unprocessed_count=unprocessed_count,
        error=error,
        success=success
    )

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

# 出席管理ページ
@app.route('/teacher/attendance', methods=['GET', 'POST'])
def teacher_attendance():
    """出席管理ページ"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    # 実装は省略
    return "出席管理ページ（実装予定）"

# 模試点数取得API
@app.route('/api/teacher/mock-exam-scores', methods=['GET'])
def get_teacher_mock_exam_scores():
    """模試の点数データを取得するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 401
    
    student_id = request.args.get('student_id')
    exam_type = request.args.get('exam_type')
    
    try:
        conn = get_db_connection()
        success, result = get_mock_exam_scores(conn, student_id, exam_type)
        conn.close()
        
        if success:
            return jsonify({
                'success': True,
                'scores': result
            })
        else:
            return jsonify({
                'success': False,
                'message': result
            }), 500
    except Exception as e:
        log_error(f"Error in get_teacher_mock_exam_scores: {e}")
        return jsonify({
            'success': False,
            'message': 'データ取得中にエラーが発生しました'
        }), 500

# 模試点数保存API
@app.route('/api/teacher/mock-exam-score', methods=['POST'])
def save_teacher_mock_exam_score():
    """模試の点数を保存するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 401
    
    teacher_id = session.get('user_id')
    data = request.json
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'データが送信されていません'
        }), 400
    
    try:
        conn = get_db_connection()
        success, result = save_mock_exam_score(conn, data, teacher_id)
        conn.close()
        
        if success:
            return jsonify({
                'success': True,
                'score_id': result['score_id'],
                'points_awarded': result['points_awarded'],
                'message': '模試点数を保存しました'
            })
        else:
            return jsonify({
                'success': False,
                'message': result
            }), 500
    except Exception as e:
        log_error(f"Error in save_teacher_mock_exam_score: {e}")
        return jsonify({
            'success': False,
            'message': 'データ保存中にエラーが発生しました'
        }), 500

# 模試点数削除API
@app.route('/api/teacher/mock-exam-score/<int:score_id>', methods=['DELETE'])
def delete_teacher_mock_exam_score(score_id):
    """模試の点数を削除するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 401
    
    teacher_id = session.get('user_id')
    
    try:
        conn = get_db_connection()
        success, message = delete_mock_exam_score(conn, score_id, teacher_id)
        conn.close()
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
    except Exception as e:
        log_error(f"Error in delete_teacher_mock_exam_score: {e}")
        return jsonify({
            'success': False,
            'message': 'データ削除中にエラーが発生しました'
        }), 500

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
        action = request.form.get('action')
        
        if action == 'award_points':
            notification_id = request.form.get('notification_id')
            notification_type = request.form.get('notification_type')
            student_id = request.form.get('student_id')
            points = request.form.get('points', type=int)
            
            if not all([notification_id, notification_type, student_id, points]):
                error = "必要な情報が不足しています"
            else:
                try:
                    conn = get_db_connection()
                    
                    # 通知処理を実行
                    success_process, message = process_notification(
                        conn, notification_id, notification_type, student_id, points, teacher_id
                    )
                    
                    if success_process:
                        success = message
                    else:
                        error = message
                    
                    conn.close()
                except Exception as e:
                    log_error(f"Error processing improvement notification: {e}")
                    error = f"処理エラー: {str(e)}"
    
    # 全ての通知を取得
    notifications = []
    unprocessed_count = 0
    
    try:
        conn = get_db_connection()
        
        # 各通知テーブルの存在確認・作成
        ensure_notification_tables(conn)
        
        # 未処理の通知数を取得
        counts = get_notification_counts(conn)
        unprocessed_count = counts['total_count']
        
        # 全ての通知を取得
        notifications = get_all_improvement_notifications(conn)
        
        conn.close()
    except Exception as e:
        log_error(f"Error fetching improvement notifications: {e}")
        error = f"通知の取得エラー: {str(e)}"
    
    # データがない場合はテスト用データ生成
    if not notifications:
        notifications = generate_sample_improvement_notifications()
        unprocessed_count = sum(1 for n in notifications if not n['is_processed'])
    
    return render_template(
        'teacher_improvement_notifications.html',
        name=session.get('user_name', ''),
        notifications=notifications,
        unprocessed_count=unprocessed_count,
        error=error,
        success=success
    )

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

# API: 未処理の通知数を取得
@app.route('/api/teacher/improvement-notification-count')
def improvement_notification_count():
    """未処理の成績・内申向上通知数を取得するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        
        # 各通知テーブルの存在確認・作成
        ensure_notification_tables(conn)
        
        # 通知数を取得
        counts = get_notification_counts(conn)
        conn.close()
        
        return jsonify(counts)
    except Exception as e:
        log_error(f"Error getting improvement notification count: {e}")
        return jsonify({
            'elementary_count': 0,
            'middle_count': 0,
            'high_count': 0,
            'internal_count': 0,
            'total_count': 0,
            'error': str(e)
        })

# 小学生模試点数管理ページ
@app.route('/teacher/manual-score', methods=['GET', 'POST'])
def teacher_manual_score():
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    students = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, grade_level, role 
                FROM users 
                WHERE role = 'student'
                ORDER BY grade_level, name
            """)
            students = cur.fetchall()
    except Exception as e:
        log_error(f"Error fetching students: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    
    # テンプレート名が正しいか確認
    return render_template('teacher_mock_exam.html', 
                          name=session.get('user_name', ''),
                          students=students)

@app.route('/api/teacher/students')
def get_teacher_students():
    """生徒データと出席情報を取得するAPI - 改善版"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # フィルターパラメータ
    grade = request.args.get('grade', 'all')
    day = request.args.get('day')  # 曜日フィルター
    grade_level = request.args.get('grade_level')  # 詳細な学年レベル
    school_type = request.args.get('school_type')  # 学校種別
    student_id = request.args.get('student_id')  # 個別生徒ID
    
    try:
        conn = get_db_connection()
        students = []
        
        with conn.cursor() as cur:
            # 基本クエリを構築
            query = """
                SELECT u.id, u.name, u.grade_level, u.school_type, u.attendance_days
                FROM users u
                WHERE u.role = 'student'
            """
            
            params = []
            
            # IDフィルター
            if student_id:
                query += " AND u.id = %s"
                params.append(int(student_id))
            
            # 学年/学校種別フィルター
            if grade_level and school_type:
                # カンマ区切りの学年レベルをサポート（例: grade_level=5,6）
                if ',' in str(grade_level):
                    levels = [int(x.strip()) for x in str(grade_level).split(',')]
                    placeholders = ','.join(['%s'] * len(levels))
                    query += f" AND u.grade_level IN ({placeholders}) AND u.school_type = %s"
                    params.extend(levels)
                    params.append(school_type)
                else:
                    # 単一学年の場合
                    query += " AND u.grade_level = %s AND u.school_type = %s"
                    params.append(int(grade_level))
                    params.append(school_type)
            elif grade and grade != 'all':
                if grade in ['elementary', 'middle', 'high']:
                    query += " AND u.school_type = %s"
                    params.append(grade)
                else:
                    # 数値学年での検索の場合
                    query += " AND u.grade_level = %s"
                    try:
                        params.append(int(grade))
                    except ValueError:
                        # 数値でない場合、これは school_type かもしれない
                        query = query.replace("u.grade_level = %s", "u.school_type = %s")
                        params.append(grade)
            
            # 並び順 - 学校種別の順序を明示的に制御し、次に学年、名前でソート
            query += """
                ORDER BY 
                CASE u.school_type 
                    WHEN 'elementary' THEN 1 
                    WHEN 'middle' THEN 2 
                    WHEN 'high' THEN 3 
                    ELSE 4 
                END, 
                u.grade_level, 
                u.name
            """
            
            # クエリを記録（デバッグ用）- アプリケーションログに記録
            app.logger.debug(f"SQL Query: {query}")
            app.logger.debug(f"SQL Params: {params}")
            
            # クエリ実行
            cur.execute(query, params)
            student_rows = cur.fetchall()
            
            # 生徒データにログイン・出席情報を追加
            today = datetime.now().date()
            for student in student_rows:
                student_id = student['id']
                
                # 今日のログイン確認
                cur.execute("""
                    SELECT id FROM login_history
                    WHERE user_id = %s AND login_date = %s
                """, (student_id, today))
                has_logged_in_today = cur.fetchone() is not None
                
                # 最終ログイン時間取得
                cur.execute("""
                    SELECT login_time FROM login_history
                    WHERE user_id = %s
                    ORDER BY login_time DESC LIMIT 1
                """, (student_id,))
                last_login_row = cur.fetchone()
                last_login = last_login_row['login_time'] if last_login_row else None
                
                # 出席状態確認
                cur.execute("""
                    SELECT status FROM attendance_records
                    WHERE user_id = %s AND attendance_date = %s
                """, (student_id, today))
                attendance_row = cur.fetchone()
                attendance_today = attendance_row['status'] if attendance_row else None
                
                # 名前を分割（姓名が含まれている場合）
                name_parts = student['name'].split(' ', 1) if student['name'] else ['', '']
                last_name = name_parts[0] if len(name_parts) > 0 else ''
                first_name = name_parts[1] if len(name_parts) > 1 else ''
                
                # 学年フォーマットを統一
                school_type_jp = {
                    'elementary': '小学',
                    'middle': '中学',
                    'high': '高校'
                }.get(student['school_type'], student['school_type'])
                
                grade = f"{school_type_jp}{student['grade_level']}年"
                
                students.append({
                    'id': student_id,
                    'name': student['name'],
                    'last_name': last_name,
                    'first_name': first_name,
                    'grade': grade,
                    'grade_level': student['grade_level'],
                    'school_type': student['school_type'],
                    'attendance_days': student['attendance_days'],
                    'lastLogin': last_login,
                    'hasLoggedInToday': has_logged_in_today,
                    'attendanceToday': attendance_today
                })
        
        conn.close()
        
        # データがない場合でもダミーデータは使用せず、空の配列を返す
        return jsonify({'success': True, 'students': students})
    
    except Exception as e:
        log_error(f"Error fetching students: {e}")
        if 'conn' in locals():
            conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

# app.pyに追加するAPIデバッグ用エンドポイント





@app.route('/api/teacher/attendance', methods=['POST'])
def update_student_attendance():
    """生徒の出席状況を更新するAPI"""
    log_error("=== 出席記録API開始 ===")
    
    if not session.get('user_id') or session.get('role') != 'teacher':
        log_error("認証エラー: 教師でない、またはログインしていない")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    teacher_id = session.get('user_id')
    data = request.json
    log_error(f"受信データ: {data}")
    log_error(f"受信データ内のdate: {data.get('date') if data else 'データなし'}")
    log_error(f"現在のサーバー時刻: {datetime.now()}")
    log_error(f"現在のサーバー日付文字列: {datetime.now().strftime('%Y-%m-%d')}")
    
    if not data or ('attendance_data' not in data and 'attendance' not in data):
        log_error("エラー: 出席データなし")
        return jsonify({'success': False, 'message': '出席データがありません'}), 400
    
    try:
        conn = get_db_connection()
        log_error("データベース接続成功")
        updated_count = 0
        points_awarded_count = 0
        award_points_flag = data.get('award_points', True)
        
        # 現在の日付を強制的に使用（クライアントからの日付は無視）
        attendance_date = datetime.now().strftime('%Y-%m-%d')
        client_date = data.get('date', 'なし')
        
        errors = []
        
        log_error(f"処理パラメータ: teacher_id={teacher_id}, award_points={award_points_flag}")
        log_error(f"日付設定: クライアント送信日付={client_date}, 実際使用日付={attendance_date}")
        
        # 出席ポイント設定（デフォルト10ポイント）
        attendance_points = 10
        
        # attendance_recordsテーブルの確認（必要に応じて）
        from attendance_utils import ensure_attendance_records_table
        ensure_attendance_records_table(conn)
        log_error("attendance_recordsテーブル確認完了")
        
        # テーブル構造の追加確認と修正
        try:
            with conn.cursor() as cur:
                # attendance_recordsテーブルの構造を確認
                cur.execute("DESCRIBE attendance_records")
                columns = {row['Field']: row for row in cur.fetchall()}
                log_error(f"attendance_recordsテーブルの現在の構造: {columns}")
                
                # 必要なカラムが足りない場合は追加
                needed_columns = [
                    'user_id', 'attendance_date', 'status', 'recorded_at', 'recorded_by', 'comments'
                ]
                
                for column in needed_columns:
                    if column not in columns:
                        log_error(f"カラム {column} が不足しています。追加します。")
                        if column == 'user_id':
                            cur.execute("ALTER TABLE attendance_records ADD COLUMN user_id INT NOT NULL")
                        elif column == 'attendance_date':
                            cur.execute("ALTER TABLE attendance_records ADD COLUMN attendance_date DATE NOT NULL")
                        elif column == 'status':
                            cur.execute("ALTER TABLE attendance_records ADD COLUMN status ENUM('present', 'absent', 'late', 'excused') NOT NULL DEFAULT 'present'")
                        elif column == 'recorded_at':
                            cur.execute("ALTER TABLE attendance_records ADD COLUMN recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                        elif column == 'recorded_by':
                            cur.execute("ALTER TABLE attendance_records ADD COLUMN recorded_by INT NOT NULL")
                        elif column == 'comments':
                            cur.execute("ALTER TABLE attendance_records ADD COLUMN comments TEXT")
                        conn.commit()
                        log_error(f"カラム {column} を追加しました")
        except Exception as e:
            log_error(f"テーブル構造確認/修正エラー: {e}")
            # 処理は継続する
        
        # クライアントの互換性のため、attendance_dataとattendanceの両方に対応
        attendance_data = data.get('attendance_data', data.get('attendance', {}))
        log_error(f"処理対象出席データ: {attendance_data}")
        
        # 各生徒の出席状況を処理
        log_error(f"開始: 出席データ処理 - 対象生徒数: {len(attendance_data)}")
        
        for student_id, status in attendance_data.items():
            attendance_saved = False
            try:
                student_id = int(student_id)
                log_error(f"処理中: 生徒ID {student_id}, ステータス: {status}")
                
                if not student_id or not status:
                    log_error(f"スキップ: 生徒ID {student_id} - 無効なデータ")
                    continue
                
                # ステップ1: 出席記録の保存（独立したトランザクション）
                try:
                    with conn.cursor() as cur:
                        # 既存の出席記録を確認
                        log_error(f"既存記録確認: 生徒ID {student_id}, 日付: {attendance_date}")
                        cur.execute("""
                            SELECT id, status FROM attendance_records
                            WHERE user_id = %s AND attendance_date = %s
                        """, (student_id, attendance_date))
                        
                        existing_record = cur.fetchone()
                        log_error(f"既存記録: {existing_record}")
                        
                        if existing_record:
                            # 既存レコードの更新
                            log_error(f"UPDATE実行: ID {existing_record['id']}, 新ステータス: {status}")
                            
                            # 強制的に更新するために、recorded_atも更新する
                            cur.execute("""
                                UPDATE attendance_records
                                SET status = %s, recorded_by = %s, recorded_at = NOW()
                                WHERE id = %s
                            """, (status, teacher_id, existing_record['id']))
                            log_error(f"UPDATE完了: affected rows = {cur.rowcount}")
                            
                            # 更新が反映されなかった場合の追加チェック
                            if cur.rowcount == 0:
                                log_error(f"警告: 更新の影響行数が0です。強制的に更新を再試行します。")
                                # コメントを追加して強制的に変更を発生させる
                                cur.execute("""
                                    UPDATE attendance_records
                                    SET status = %s, recorded_by = %s, recorded_at = NOW(), 
                                        comments = CONCAT(IFNULL(comments, ''), ' [更新: ', NOW(), ']')
                                    WHERE id = %s
                                """, (status, teacher_id, existing_record['id']))
                                log_error(f"強制UPDATE完了: affected rows = {cur.rowcount}")
                        else:
                            # 新規レコードの挿入
                            log_error(f"INSERT実行: 生徒ID {student_id}, ステータス: {status}")
                            try:
                                # 出席記録データを直接ログに出力して確認
                                log_error(f"挿入するデータ確認: student_id={student_id}, date={attendance_date}, status={status}, teacher_id={teacher_id}")
                                
                                # パラメータの型を明示的に確認
                                log_error(f"パラメータ型: student_id={type(student_id)}, date={type(attendance_date)}, status={type(status)}, teacher_id={type(teacher_id)}")
                                
                                # 型変換を明示的に行う
                                try:
                                    student_id_int = int(student_id)
                                    teacher_id_int = int(teacher_id)
                                    date_str = str(attendance_date)
                                    status_str = str(status)
                                    
                                    cur.execute("""
                                        INSERT INTO attendance_records
                                        (user_id, attendance_date, status, recorded_by)
                                        VALUES (%s, %s, %s, %s)
                                    """, (student_id_int, date_str, status_str, teacher_id_int))
                                    log_error(f"INSERT完了: inserted ID = {cur.lastrowid}")
                                except ValueError as type_error:
                                    log_error(f"型変換エラー: {type_error}")
                                    raise
                            except Exception as insert_error:
                                log_error(f"INSERT詳細エラー: {insert_error}")
                                # テーブル構造を確認
                                try:
                                    cur.execute("DESCRIBE attendance_records")
                                    columns = cur.fetchall()
                                    log_error(f"テーブル構造確認: {columns}")
                                    
                                    # ユニーク制約のチェック
                                    cur.execute("SHOW INDEX FROM attendance_records WHERE Key_name = 'idx_user_date' OR Key_name = 'user_id_attendance_date'")
                                    indexes = cur.fetchall()
                                    log_error(f"ユニーク制約確認: {indexes}")
                                    
                                    # 既存データの確認（デバッグ用）
                                    cur.execute("SELECT * FROM attendance_records WHERE user_id = %s LIMIT 3", (student_id,))
                                    existing_data = cur.fetchall()
                                    log_error(f"既存データサンプル: {existing_data}")
                                except Exception as desc_error:
                                    log_error(f"テーブル構造確認エラー: {desc_error}")
                                raise
                        
                        conn.commit()  # 出席記録を確実に保存
                        attendance_saved = True
                        log_error(f"出席記録保存成功: 生徒ID {student_id}")
                        updated_count += 1
                        
                        # 念のためデータが本当に保存されたか確認
                        cur.execute("""
                            SELECT id, status, attendance_date FROM attendance_records
                            WHERE user_id = %s AND attendance_date = %s
                        """, (student_id, attendance_date))
                        check_record = cur.fetchone()
                        if check_record:
                            log_error(f"データ保存確認: ID={check_record['id']}, status={check_record['status']}, date={check_record['attendance_date']}")
                        else:
                            log_error(f"警告: データが見つかりません。処理は続行します。")
                            # この場合でも処理は続行する
                        
                except Exception as attendance_error:
                    log_error(f"出席記録保存エラー: 生徒ID {student_id}, {attendance_error}")
                    conn.rollback()
                    errors.append(f"生徒ID {student_id} 出席記録: {str(attendance_error)}")
                
                # ステップ2: ポイント付与（出席記録が成功した場合のみ、独立したトランザクション）
                if attendance_saved and status == 'present' and award_points_flag:
                    try:
                        log_error(f"ポイント付与開始: 生徒ID {student_id}")
                        from points_utils import award_attendance_points
                        success, message = award_attendance_points(
                            conn, 
                            student_id, 
                            datetime.strptime(attendance_date, '%Y-%m-%d').date(),
                            teacher_id  # 教師IDを渡す
                        )
                        log_error(f"ポイント付与結果: success={success}, message={message}")
                        if success:
                            points_awarded_count += 1
                            conn.commit()  # ポイント付与も確実に保存
                            log_error(f"ポイント付与成功: 生徒ID {student_id}")
                        else:
                            log_error(f"ポイント付与失敗: 生徒ID {student_id}, {message}")
                            errors.append(f"生徒ID {student_id} ポイント: {message}")
                            # ポイント付与失敗でもrollbackしない（出席記録は保持）
                    except Exception as points_error:
                        log_error(f"ポイント付与エラー: 生徒ID {student_id}, {points_error}")
                        errors.append(f"生徒ID {student_id} ポイント: {str(points_error)}")
                        # ポイント付与エラーでもrollbackしない（出席記録は保持）
            
            except Exception as e:
                log_error(f"Error processing student {student_id}: {e}")
                log_error(f"トレースバック: {traceback.format_exc()}")
                errors.append(f"生徒ID {student_id}: {str(e)}")
                # 出席記録が未保存の場合のみrollback
                if not attendance_saved:
                    conn.rollback()
        
        # 成功結果を返す
        result = {
            'success': True, 
            'message': f'{updated_count}件の出席記録を更新しました',
            'updated_count': updated_count
        }
        
        log_error(f"処理完了: updated_count={updated_count}, points_awarded_count={points_awarded_count}")
        
        # ポイント付与があれば追加情報
        if points_awarded_count > 0:
            result['awarded_points'] = attendance_points
            result['awarded_points_count'] = points_awarded_count
            result['points_awarded'] = f'{points_awarded_count}名に{attendance_points}ポイント付与'
            result['message'] = f'{updated_count}件の出席記録を更新し、{points_awarded_count}名に{attendance_points}ポイントずつ付与しました'
        
        # エラーがあれば追加
        if errors:
            result['errors'] = errors
            log_error(f"エラー詳細: {errors}")
            
        log_error(f"最終結果: {result}")
        log_error("=== 出席記録API完了 ===")
        return jsonify(result)
    
    except Exception as e:
        log_error(f"Error updating attendance: {e}")
        log_error(f"トレースバック: {traceback.format_exc()}")
        if 'conn' in locals():
            conn.rollback()
        log_error("=== 出席記録API異常終了 ===")
        return jsonify({'success': False, 'message': str(e)}), 500

# app.pyに追加
@app.route('/api/teacher/class-schedule', methods=['GET', 'POST'])
def manage_class_schedule():
    """学年別曜日設定の取得・更新API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # GETリクエスト: 設定取得
    if request.method == 'GET':
        try:
            conn = get_db_connection()
            
            # テーブルが存在するか確認し、なければ作成
            create_class_schedule_master_table(conn)
            
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT grade_level, school_type, day_of_week 
                    FROM class_schedule_master
                    WHERE is_active = 1
                """)
                schedule = cur.fetchall()
            conn.close()
            return jsonify({'success': True, 'schedule': schedule})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # POSTリクエスト: 設定更新
    else:
        data = request.json
        if not data or 'schedule' not in data:
            return jsonify({'success': False, 'message': '設定データがありません'}), 400
        
        try:
            conn = get_db_connection()
            
            # テーブルが存在するか確認し、なければ作成
            create_class_schedule_master_table(conn)
            
            with conn.cursor() as cur:
                # 既存設定を無効化
                cur.execute("UPDATE class_schedule_master SET is_active = 0")
                
                # 新しい設定を挿入
                for item in data['schedule']:
                    grade_level = item.get('grade_level')
                    school_type = item.get('school_type')
                    day_of_week = item.get('day_of_week')
                    
                    # 不正な値をスキップ
                    if grade_level is None or school_type is None or day_of_week is None:
                        continue
                    
                    # 値を整数に変換（文字列で来る可能性がある）
                    try:
                        grade_level = int(grade_level)
                        day_of_week = int(day_of_week)
                    except (ValueError, TypeError):
                        continue
                    
                    cur.execute("""
                        INSERT INTO class_schedule_master
                        (grade_level, school_type, day_of_week, is_active)
                        VALUES (%s, %s, %s, 1)
                        ON DUPLICATE KEY UPDATE is_active = 1
                    """, (grade_level, school_type, day_of_week))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': '設定を更新しました'})
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500

# 生徒の出席曜日を更新するAPI - 追加
@app.route('/api/teacher/update-student-attendance-days', methods=['POST'])
def update_student_attendance_days():
    """生徒の出席曜日設定を更新するAPI"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'データがありません'}), 400
    
    student_id = data.get('student_id')
    attendance_days = data.get('attendance_days')  # "0,1,3,5" のような形式
    
    if not student_id:
        return jsonify({'success': False, 'message': '生徒IDが指定されていません'}), 400
    
    try:
        conn = get_db_connection()
        
        # usersテーブルに attendance_days カラムが存在するか確認
        add_attendance_day_column_to_users(conn)
        
        with conn.cursor() as cur:
            # 生徒が存在するか確認
            cur.execute("SELECT id FROM users WHERE id = %s AND role = 'student'", (student_id,))
            if not cur.fetchone():
                return jsonify({'success': False, 'message': '指定された生徒が見つかりません'}), 404
            
            # 出席曜日を更新
            cur.execute("""
                UPDATE users
                SET attendance_days = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (attendance_days, student_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '出席曜日設定を更新しました'
        })
    
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
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
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT grade_level FROM users WHERE id = %s", (user_id,))
                result = cur.fetchone()
                grade_year = result['grade_level'] if result else 1
            conn.close()
        except Exception as e:
            log_error(f"Error getting user grade level: {e}")
            grade_year = 1
    
    try:
        conn = get_db_connection()
        
        # テーブルの存在確認
        ensure_monthly_test_comments_table(conn)
        
        # コメントデータを取得
        with conn.cursor() as cur:
            cur.execute("""
                SELECT subject, month, comment
                FROM monthly_test_comments
                WHERE student_id = %s AND grade_year = %s
            """, (user_id, grade_year))
            comments = cur.fetchall()
        
        # 科目と月ごとのコメントを整理
        result = {}
        for row in comments:
            subject_id = str(row['subject'])
            month = row['month']
            
            if subject_id not in result:
                result[subject_id] = {}
            
            result[subject_id][month] = row['comment']
        
        conn.close()
        return jsonify({
            'success': True,
            'comments': result
        })
    
    except Exception as e:
        log_error(f"Error getting test comments: {e}")
        return jsonify({
            'success': False,
            'message': 'コメントデータの取得に失敗しました'
        }), 500

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
            # 既存のコメントを検索
            cur.execute("""
                SELECT id FROM monthly_test_comments
                WHERE student_id = %s AND grade_year = %s AND subject = %s AND month = %s
            """, (student_id, grade_year, subject_id, month))
            
            existing = cur.fetchone()
            
            if existing:
                # 既存コメントを更新
                cur.execute("""
                    UPDATE monthly_test_comments
                    SET comment = %s, updated_at = NOW()
                    WHERE id = %s
                """, (comment, existing['id']))
                comment_id = existing['id']
            else:
                # 新規コメントを挿入
                cur.execute("""
                    INSERT INTO monthly_test_comments
                    (student_id, grade_year, subject, month, comment)
                    VALUES (%s, %s, %s, %s, %s)
                """, (student_id, grade_year, subject_id, month, comment))
                comment_id = cur.lastrowid
        
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
        return jsonify({
            'success': False,
            'message': f'コメントの保存に失敗しました: {str(e)}'
        }), 500

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
            if grade_id:  # 更新
                cur.execute("""
                    UPDATE elementary_grades
                    SET score = %s, comment = %s
                    WHERE id = %s AND student_id = %s
                """, (score, comment, grade_id, student_id))
            else:  # 新規追加
                # 同じ条件のデータが既にあるか確認
                cur.execute("""
                    SELECT id FROM elementary_grades
                    WHERE student_id = %s AND grade_year = %s AND subject = %s AND month = %s
                """, (student_id, grade_year, subject_id, month))
                
                existing = cur.fetchone()
                if existing:
                    # 既存レコードの更新
                    cur.execute("""
                        UPDATE elementary_grades
                        SET score = %s, comment = %s
                        WHERE id = %s
                    """, (score, comment, existing['id']))
                    grade_id = existing['id']
                else:
                    # 新規レコードの挿入
                    cur.execute("""
                        INSERT INTO elementary_grades (student_id, grade_year, subject, month, score, comment)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (student_id, grade_year, subject_id, month, score, comment))
                    grade_id = cur.lastrowid
        
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
        return jsonify({
            'success': False,
            'message': f'成績の保存に失敗しました: {str(e)}'
        }), 500

@app.route('/api/teacher/improved-students')
def get_improved_students():
    """成績向上生徒データ取得API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # クエリパラメータの取得
    school_type = request.args.get('type', 'elementary')
    
    try:
        conn = get_db_connection()
        
        if school_type == 'elementary':
            # 小学生向け成績向上データの取得
            start_month = request.args.get('start_month', 1, type=int)
            end_month = request.args.get('end_month', 12, type=int)
            subject_id = request.args.get('subject', 'all')
            min_improvement = request.args.get('min_improvement', 0, type=int)
            
            with conn.cursor() as cur:
                # 基本的なSQLクエリの構築
                query = """
                    SELECT 
                        s1.student_id, 
                        s1.grade_year, 
                        s1.subject, 
                        s1.month AS current_month, 
                        s1.score AS current_score, 
                        s2.month AS previous_month,
                        s2.score AS previous_score,
                        u.name AS student_name,
                        u.school_type,
                        u.grade_level,
                        sub.name AS subject_name,
                        (s1.score - s2.score) AS improvement
                    FROM elementary_grades s1
                    JOIN elementary_grades s2 ON 
                        s1.student_id = s2.student_id AND 
                        s1.grade_year = s2.grade_year AND 
                        s1.subject = s2.subject AND
                        s1.month != s2.month
                    JOIN users u ON s1.student_id = u.id
                    JOIN subjects sub ON s1.subject = sub.id
                    WHERE 
                        u.school_type = 'elementary' AND
                        s1.month = %s AND 
                        s2.month = %s AND 
                        (s1.score - s2.score) >= %s
                """
                
                params = [end_month, start_month, min_improvement]
                
                # 科目フィルターが指定されている場合はWHERE句に追加
                if subject_id != 'all':
                    query += " AND s1.subject = %s"
                    params.append(int(subject_id))
                    
                # 向上幅でソート
                query += " ORDER BY (s1.score - s2.score) DESC"
                
                # クエリを実行
                log_error(f"SQL Query: {query}")
                log_error(f"SQL Params: {params}")
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                # 結果をリスト形式に整形
                students = []
                for row in results:
                    # JavaScriptで使いやすい形式に変換
                    student = {
                        'id': row['student_id'],
                        'name': row['student_name'],
                        'grade_level': row['grade_level'],
                        'school_type': row['school_type'],
                        'subject_id': row['subject'],
                        'subject_name': row['subject_name'],
                        'previous_month': row['previous_month'],
                        'current_month': row['current_month'],
                        'previous_score': row['previous_score'],
                        'current_score': row['current_score'],
                        'improvement': row['improvement']
                    }
                    
                    students.append(student)
        
        else:
            # 中学生向け内申点向上データの取得
            start_year = request.args.get('start_year', 1, type=int)
            start_term = request.args.get('start_term', 1, type=int)
            end_year = request.args.get('end_year', 3, type=int)
            end_term = request.args.get('end_term', 3, type=int)
            subject_id = request.args.get('subject', 'all')
            
            with conn.cursor() as cur:
                # 基本的なSQLクエリの構築
                query = """
                    SELECT 
                        p1.student_id, 
                        p1.grade_year AS current_year,
                        p1.term AS current_term,
                        p1.point AS current_point, 
                        p2.grade_year AS previous_year,
                        p2.term AS previous_term,
                        p2.point AS previous_point,
                        u.name AS student_name,
                        u.school_type,
                        u.grade_level,
                        p1.subject,
                        sub.name AS subject_name,
                        (p1.point - p2.point) AS improvement
                    FROM internal_points p1
                    JOIN internal_points p2 ON 
                        p1.student_id = p2.student_id AND 
                        p1.subject = p2.subject
                    JOIN users u ON p1.student_id = u.id
                    JOIN subjects sub ON p1.subject = sub.id
                    WHERE 
                        u.school_type = 'middle' AND
                        p1.grade_year = %s AND 
                        p1.term = %s AND 
                        p2.grade_year = %s AND 
                        p2.term = %s AND
                        (p1.point - p2.point) > 0
                """
                
                params = [end_year, end_term, start_year, start_term]
                
                # 科目フィルターが指定されている場合はWHERE句に追加
                if subject_id != 'all':
                    query += " AND p1.subject = %s"
                    params.append(int(subject_id))
                    
                # 向上幅でソート
                query += " ORDER BY (p1.point - p2.point) DESC"
                
                # クエリを実行
                log_error(f"SQL Query: {query}")
                log_error(f"SQL Params: {params}")
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                # 結果をリスト形式に整形
                students = []
                for row in results:
                    # JavaScriptで使いやすい形式に変換
                    student = {
                        'id': row['student_id'],
                        'name': row['student_name'],
                        'grade_level': row['grade_level'],
                        'school_type': row['school_type'],
                        'subject_id': row['subject'],
                        'subject_name': row['subject_name'],
                        'previous_year': row['previous_year'],
                        'previous_term': row['previous_term'],
                        'current_year': row['current_year'],
                        'current_term': row['current_term'],
                        'previous_point': row['previous_point'],
                        'current_point': row['current_point'],
                        'improvement': row['improvement']
                    }
                    
                    students.append(student)
        
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
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
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
        improvement_type = data.get('improvement_type', 'general')
        
        if not all([student_id, points, event_type]):
            return jsonify({'success': False, 'message': '必要なデータが不足しています'}), 400
        
        conn = get_db_connection()
        
        # 重複チェック: 同じ学生・成績向上種別で既にポイントが付与されているかチェック
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, points, comment, created_at 
                FROM point_history 
                WHERE user_id = %s 
                AND event_type LIKE '%improvement%'
                AND comment LIKE %s
                AND is_active = 1
                ORDER BY created_at DESC 
                LIMIT 1
            """, (student_id, f"%{improvement_type}%"))
            
            existing_award = cur.fetchone()
            
            if existing_award:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': f'この生徒には既に{improvement_type}の成績向上ポイントが付与されています（{existing_award["created_at"]}）',
                    'points': 0,
                    'student_id': student_id,
                    'already_awarded': True,
                    'existing_points': existing_award['points'],
                    'awarded_date': existing_award['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                })
        
        # 重複がない場合、ポイント付与実行
        success, message = teacher_award_points(
            conn,
            teacher_id,
            student_id,
            event_type,
            points,
            f"{comment} ({improvement_type})"
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

def import_eiken_words_from_csv(file_content, grade, user_id, overwrite=False):
    """CSVファイルから英検単語をインポートする関数（エラー修正版）"""
    try:
        import csv
        import io
        
        # ログ記録
        log_error(f"英検単語インポート開始: grade={grade}")
        
        # BOMが付いている場合の処理
        if isinstance(file_content, str) and file_content.startswith('\ufeff'):
            file_content = file_content[1:]
            log_error("BOMが検出されました。除去して処理を続行します。")
        
        # CSVファイルを読み込む
        csv_data = io.StringIO(file_content)
        
        # ヘッダー行の確認
        try:
            first_line = csv_data.readline().strip()
            csv_data.seek(0)  # ファイルポインタを先頭に戻す
            log_error(f"CSV最初の行: {first_line}")
        except Exception as e:
            log_error(f"CSVファイルの先頭行読み取りエラー: {e}")
            return {'success': False, 'message': f'CSVファイルの読み取りに失敗しました: {str(e)}', 'count': 0}
        
        # CSVの読み込み
        try:
            reader = csv.reader(csv_data)
            headers = next(reader, None)  # ヘッダー行を読み取り
            
            if not headers:
                log_error("CSVヘッダーが見つかりません")
                return {
                    'success': False,
                    'message': 'CSVファイルのヘッダー行を認識できませんでした',
                    'count': 0
                }
            
            log_error(f"CSVヘッダー: {headers}")
        except Exception as e:
            log_error(f"CSV解析エラー: {e}")
            return {
                'success': False,
                'message': f'CSVファイルの解析に失敗しました: {str(e)}',
                'count': 0
            }
        
        # インポート準備
        imported_count = 0
        errors = []
        
        try:
            # データベース接続
            conn = get_db_connection()
            
            # まず、テーブルが存在するか確認し、なければ作成
            with conn.cursor() as cur:
                # テーブルの存在確認
                cur.execute("SHOW TABLES LIKE 'eiken_words'")
                if not cur.fetchone():
                    # テーブルが存在しない場合は作成
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS eiken_words (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            grade VARCHAR(10) NOT NULL COMMENT '英検の級 (5, 4, 3, pre2, 2)',
                            question_id INT NOT NULL COMMENT '問題ID',
                            stage_number INT NOT NULL DEFAULT 1 COMMENT 'ステージ番号',
                            word VARCHAR(255) NOT NULL COMMENT '英単語',
                            pronunciation VARCHAR(255) COMMENT '発音・意味',
                            audio_url VARCHAR(255) COMMENT '音声ファイルURL',
                            notes TEXT COMMENT '追加情報・メモ',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            INDEX(grade, question_id),
                            INDEX(grade, stage_number)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
                    """)
                    log_error("eiken_words テーブルを作成しました")
                
                # オーバーライトモードの場合、既存データを削除
                if overwrite:
                    cur.execute("DELETE FROM eiken_words WHERE grade = %s", (grade,))
                    log_error(f"既存の {grade} 級データを削除しました")
            
            # 全データを一括でコミットするため、自動コミットを無効化
            conn.autocommit = False
            
            # 見出し行の列インデックスを特定
            headers_lower = [h.lower() if h else "" for h in headers]
            
            # 基本的なカラムマッピング（いくつかのパターンに対応）
            question_id_idx = next((i for i, h in enumerate(headers_lower) if 'question' in h and 'id' in h), -1)
            if question_id_idx == -1:
                question_id_idx = next((i for i, h in enumerate(headers_lower) if 'id' in h), 0)
            
            stage_number_idx = next((i for i, h in enumerate(headers_lower) if 'stage' in h), -1)
            if stage_number_idx == -1:
                stage_number_idx = next((i for i, h in enumerate(headers_lower) if 'number' in h), 1)
            
            word_idx = next((i for i, h in enumerate(headers_lower) if 'question' in h and 'text' in h), -1)
            if word_idx == -1:
                word_idx = next((i for i, h in enumerate(headers_lower) if 'word' in h or 'english' in h), -1)
            if word_idx == -1:
                word_idx = 2  # デフォルトは3列目
            
            pronunciation_idx = next((i for i, h in enumerate(headers_lower) if 'correct' in h and 'answer' in h), -1)
            if pronunciation_idx == -1:
                pronunciation_idx = next((i for i, h in enumerate(headers_lower) if 'pronun' in h or 'meaning' in h or 'japanese' in h), -1)
            if pronunciation_idx == -1:
                pronunciation_idx = 3  # デフォルトは4列目
            
            audio_url_idx = next((i for i, h in enumerate(headers_lower) if 'audio' in h or 'url' in h or 'sound' in h), -1)
            notes_idx = next((i for i, h in enumerate(headers_lower) if 'note' in h or 'memo' in h or 'comment' in h), -1)
            
            log_error(f"検出したカラム位置: QuestionID={question_id_idx}, Word={word_idx}, Pronunciation={pronunciation_idx}")
            
            # バッチ処理用にデータを準備
            batch_size = 100
            batch_data = []
            
            with conn.cursor() as cur:
                for row_idx, row in enumerate(reader, start=2):
                    try:
                        # 行の長さが不足している場合はスキップ
                        if len(row) <= max(question_id_idx, word_idx):
                            log_error(f"行 {row_idx}: 列が不足しています。スキップします。")
                            errors.append(f"行 {row_idx}: 列が不足しています")
                            continue
                        
                        # 必須データの取得
                        try:
                            question_id = int(row[question_id_idx].strip()) if question_id_idx < len(row) and row[question_id_idx].strip() else 0
                        except ValueError:
                            question_id = 0
                            log_error(f"行 {row_idx}: QuestionID '{row[question_id_idx]}' を数値に変換できないため0を設定します")
                            errors.append(f"行 {row_idx}: QuestionID '{row[question_id_idx]}' を数値に変換できません")
                        
                        try:
                            stage_number = int(row[stage_number_idx].strip()) if stage_number_idx < len(row) and row[stage_number_idx].strip() else 1
                        except ValueError:
                            stage_number = 1
                            log_error(f"行 {row_idx}: StageNumber '{row[stage_number_idx]}' を数値に変換できないため1を設定します")
                        
                        # 必須項目のチェック
                        word = row[word_idx].strip() if word_idx < len(row) else ""
                        if not word:
                            log_error(f"行 {row_idx}: 単語が空のためスキップします")
                            errors.append(f"行 {row_idx}: 単語が空のためスキップします")
                            continue
                        
                        # オプションデータ
                        pronunciation = row[pronunciation_idx].strip() if pronunciation_idx < len(row) and pronunciation_idx >= 0 else ""
                        audio_url = row[audio_url_idx].strip() if audio_url_idx < len(row) and audio_url_idx >= 0 else None
                        notes = row[notes_idx].strip() if notes_idx < len(row) and notes_idx >= 0 else None
                        
                        # 重複チェック（オーバーライトモードでない場合）
                        if not overwrite:
                            cur.execute("""
                                SELECT id FROM eiken_words
                                WHERE grade = %s AND question_id = %s
                            """, (grade, question_id))
                            
                            existing = cur.fetchone()
                            
                            if existing:
                                # 既存データを更新
                                cur.execute("""
                                    UPDATE eiken_words
                                    SET stage_number = %s,
                                        word = %s,
                                        pronunciation = %s,
                                        audio_url = %s,
                                        notes = %s,
                                        updated_at = NOW()
                                    WHERE id = %s
                                """, (stage_number, word, pronunciation, audio_url, notes, existing['id']))
                                imported_count += 1
                                continue
                        
                        # データをバッチに追加
                        batch_data.append((grade, question_id, stage_number, word, pronunciation, audio_url, notes))
                        
                        # バッチサイズに達したら一括挿入
                        if len(batch_data) >= batch_size:
                            placeholders = ', '.join(['(%s, %s, %s, %s, %s, %s, %s)'] * len(batch_data))
                            flat_data = [item for sublist in batch_data for item in sublist]
                            
                            try:
                                cur.execute(f"""
                                    INSERT INTO eiken_words
                                    (grade, question_id, stage_number, word, pronunciation, audio_url, notes)
                                    VALUES {placeholders}
                                """, flat_data)
                                
                                imported_count += len(batch_data)
                                batch_data = []  # バッチをクリア
                            except Exception as batch_error:
                                log_error(f"バッチインポートエラー: {batch_error}")
                                # バッチ処理に失敗した場合は1件ずつ処理
                                for data in batch_data:
                                    try:
                                        cur.execute("""
                                            INSERT INTO eiken_words
                                            (grade, question_id, stage_number, word, pronunciation, audio_url, notes)
                                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                                        """, data)
                                        imported_count += 1
                                    except Exception as single_error:
                                        log_error(f"単一レコードのインポートエラー: {single_error}")
                                
                                batch_data = []  # バッチをクリア
                    
                    except Exception as row_error:
                        log_error(f"行 {row_idx} 処理エラー: {row_error}")
                        errors.append(f"行 {row_idx}: {str(row_error)}")
                        continue
                
                # 残りのバッチデータを処理
                if batch_data:
                    placeholders = ', '.join(['(%s, %s, %s, %s, %s, %s, %s)'] * len(batch_data))
                    flat_data = [item for sublist in batch_data for item in sublist]
                    
                    try:
                        cur.execute(f"""
                            INSERT INTO eiken_words
                            (grade, question_id, stage_number, word, pronunciation, audio_url, notes)
                            VALUES {placeholders}
                        """, flat_data)
                        
                        imported_count += len(batch_data)
                    except Exception as batch_error:
                        log_error(f"最終バッチインポートエラー: {batch_error}")
                        # 1件ずつ処理
                        for data in batch_data:
                            try:
                                cur.execute("""
                                    INSERT INTO eiken_words
                                    (grade, question_id, stage_number, word, pronunciation, audio_url, notes)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, data)
                                imported_count += 1
                            except Exception as single_error:
                                log_error(f"単一レコードのインポートエラー: {single_error}")
                
                # インポート履歴を記録
                try:
                    # import_historyテーブルがない場合は何もしない
                    cur.execute("SHOW TABLES LIKE 'import_history'")
                    if cur.fetchone():
                        cur.execute("""
                            INSERT INTO import_history
                            (import_type, year, imported_by, record_count, file_name)
                            VALUES (%s, %s, %s, %s, %s)
                        """, ('eiken_words', datetime.now().year, user_id, imported_count, 'Eiken_Words_Import.csv'))
                    else:
                        log_error("import_historyテーブルが存在しないため、履歴は記録しません")
                except Exception as history_error:
                    log_error(f"インポート履歴の記録に失敗しました: {history_error}")
                    # 履歴の記録に失敗してもロールバックはしない
            
            # 全体をコミット
            conn.commit()
            log_error(f"英検単語インポート完了: {imported_count}件")
            
            result = {
                'success': True,
                'message': f"{imported_count}件の英検単語をインポートしました（{grade}級）",
                'count': imported_count
            }
            
            if errors:
                if len(errors) <= 5:
                    result['message'] += f"（{len(errors)}件のエラーがありました）"
                else:
                    result['message'] += f"（{len(errors)}件のエラーがありました。最初の5件のみ表示）"
                result['errors'] = errors[:5]  # 最初の5件のエラーのみ
            
            return result
        
        except Exception as e:
            if 'conn' in locals() and conn:
                conn.rollback()
            log_error(f"Database error in CSV import: {e}")
            return {
                'success': False,
                'message': f"データベースエラー: {str(e)}",
                'count': 0,
                'errors': [f"データベースエラー: {str(e)}"]
            }
        finally:
            if 'conn' in locals() and conn:
                conn.close()
    
    except Exception as e:
        log_error(f"CSV read error: {e}")
        return {
            'success': False,
            'message': f"CSV読み込みエラー: {str(e)}",
            'count': 0,
            'errors': [f"CSV読み込みエラー: {str(e)}"]
        }

@app.route('/student/eiken-words')
def student_eiken_words():
    """英検単語学習ページ"""
    if not session.get('user_id'):
        return redirect('/myapp/index.cgi/login')
    
    # 講師モードの判定
    teacher_view = request.args.get('teacher_view') == 'true'
    is_teacher_login = session.get('is_teacher_login', False)
    
    # 表示する生徒IDの決定
    if teacher_view and session.get('role') == 'teacher':
        # URLパラメータから生徒IDを取得
        student_id = request.args.get('id')
        if student_id:
            try:
                student_id = int(student_id)
            except ValueError:
                student_id = session.get('user_id')
        else:
            student_id = session.get('user_id')
    elif is_teacher_login:
        student_id = session.get('viewing_student_id', session.get('user_id'))
    else:
        student_id = session.get('user_id')
    
    return render_template(
        'eiken_words.html',
        name=session.get('user_name', ''),
        teacher_view=teacher_view or is_teacher_login,
        is_teacher_login=is_teacher_login,
        student_id=student_id
    )

@app.route('/api/eiken-words')
def get_eiken_words():
    """英検単語データを取得するAPI（改善版）"""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    # クエリパラメータの取得
    grade = str(request.args.get('grade', '5'))  # デフォルトは5級、常に文字列化
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)  # 1ページあたりの単語数
    get_all = request.args.get('all', 0, type=int) == 1  # 全データ取得フラグ
    
    # デバッグ用ログ出力
    try:
        print(f"英検単語データリクエスト: grade={grade}, page={page}, get_all={get_all}", file=sys.stderr)
    except:
        pass
    
    # 追加の検索フィルター
    search_term = request.args.get('search', '')        # 単語検索
    stage = request.args.get('stage', type=int)         # ステージ番号検索
    has_audio = request.args.get('has_audio', type=int) # 音声ありのみ (1=あり, 0=なし)
    sort_by = request.args.get('sort', 'id')            # ソート項目
    sort_order = request.args.get('order', 'asc')       # ソート順序
    
    try:
        conn = get_db_connection()
        
        # テーブル存在確認
        ensure_eiken_words_table(conn)
        
        with conn.cursor() as cur:
            # 基本的なクエリ構築
            query_conditions = ["grade = %s"]
            query_params = [grade]
            
            # デバッグ情報をログに出力
            try:
                print(f"英検単語クエリ条件: grade={grade}(型:{type(grade).__name__}), 検索条件={search_term}", file=sys.stderr)
            except:
                pass
            
            # 検索条件を追加
            if search_term:
                query_conditions.append("(english LIKE %s OR japanese LIKE %s OR pronunciation LIKE %s)")
                search_pattern = f"%{search_term}%"
                query_params.extend([search_pattern, search_pattern, search_pattern])
            
            if stage is not None:
                query_conditions.append("stage_number = %s")
                query_params.append(stage)
            
            if has_audio is not None:
                if has_audio == 1:
                    query_conditions.append("audio_url IS NOT NULL AND audio_url != ''")
                else:
                    query_conditions.append("(audio_url IS NULL OR audio_url = '')")
            
            # 総件数を取得
            count_query = f"""
                SELECT COUNT(*) as count FROM eiken_words
                WHERE {' AND '.join(query_conditions)}
            """
            cur.execute(count_query, query_params)
            result = cur.fetchone()
            total_count = result['count'] if result else 0
            
            # ソート条件を検証
            valid_sort_fields = ['id', 'english', 'japanese', 'stage_number', 'question_id']
            if sort_by not in valid_sort_fields:
                sort_by = 'id'
                
            valid_sort_orders = ['asc', 'desc']
            if sort_order not in valid_sort_orders:
                sort_order = 'asc'
            
            # ページネーション計算
            offset = (page - 1) * per_page
            
            # メインクエリ構築
            if get_all:
                # 全データを取得する場合はLIMITとOFFSETを使用しない
                main_query = f"""
                    SELECT id, 
                           english as word, 
                           japanese, 
                           pronunciation, 
                           audio_url, 
                           stage_number, 
                           question_id, 
                           notes, 
                           grade
                    FROM eiken_words
                    WHERE {' AND '.join(query_conditions)}
                    ORDER BY {sort_by} {sort_order}
                """
                main_params = query_params
                # ログにデバッグ情報を出力
                try:
                    print(f"英検単語の全データ取得: grade={grade}, 条件数={len(query_conditions)}", file=sys.stderr)
                except:
                    pass
            else:
                # 通常のページネーション
                main_query = f"""
                    SELECT id, 
                           english as word, 
                           japanese, 
                           pronunciation, 
                           audio_url, 
                           stage_number, 
                           question_id, 
                           notes, 
                           grade
                    FROM eiken_words
                    WHERE {' AND '.join(query_conditions)}
                    ORDER BY {sort_by} {sort_order}
                    LIMIT %s OFFSET %s
                """
                main_params = query_params + [per_page, offset]
            
            # クエリ実行
            cur.execute(main_query, main_params)
            words = cur.fetchall()
            
            # 学習進捗データを取得（オプション、将来的な機能）
            if words and session.get('role') == 'student':
                student_id = session.get('user_id')
                word_ids = [word['id'] for word in words]
                
                # 進捗データを取得するクエリ（テーブルが存在する場合）
                try:
                    cur.execute("""
                        SHOW TABLES LIKE 'eiken_word_progress'
                    """)
                    if cur.fetchone():
                        placeholders = ', '.join(['%s'] * len(word_ids))
                        cur.execute(f"""
                            SELECT word_id, status, last_reviewed_at
                            FROM eiken_word_progress
                            WHERE student_id = %s AND word_id IN ({placeholders})
                        """, [student_id] + word_ids)
                        
                        progress_data = cur.fetchall()
                        progress_by_word = {p['word_id']: p for p in progress_data}
                        
                        # 単語データに進捗情報を追加
                        for word in words:
                            if word['id'] in progress_by_word:
                                word['progress'] = {
                                    'status': progress_by_word[word['id']]['status'],
                                    'last_reviewed': progress_by_word[word['id']]['last_reviewed_at']
                                }
                except Exception as e:
                    log_error(f"進捗データ取得エラー: {e}")
        
        conn.close()
        
        # ページ総数を計算
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        
        return jsonify({
            'success': True,
            'words': words,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_count': total_count,
                'per_page': per_page
            },
            'filters': {
                'grade': grade,
                'search': search_term,
                'stage': stage,
                'has_audio': has_audio
            }
        })
    
    except Exception as e:
        log_error(f"Error getting eiken words: {e}")
        try:
            # 詳細なエラー情報をログに出力
            log_error(f"Details: grade={grade}, page={page}, all={get_all}, params={request.args}")
        except:
            pass
        
        if 'conn' in locals():
            conn.close()
        return jsonify({
            'success': False,
            'message': f'単語データの取得に失敗しました: {str(e)}'
        }), 500

@app.route('/admin/fetch-high-schools', methods=['GET', 'POST'])
def admin_fetch_high_schools():
    """神奈川県公立高校情報取得機能"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    success = None
    error = None
    high_schools_data = []
    import_history = []
    
    # 現在の年度を取得
    current_year = datetime.now().year
    
    if request.method == 'POST':
        try:
            # フォームから取得する操作タイプ
            action = request.form.get('action', 'web_scrape')
            year = request.form.get('year', current_year)
            
            if action == 'web_scrape':
                # 高校データを取得（ダミーデータを使用）
                high_schools_data = [
                    {'name': '横浜翠嵐高等学校', 'type': '普通科', 'location': '横浜市神奈川区', 'deviation': 73},
                    {'name': '湘南高等学校', 'type': '普通科', 'location': '藤沢市', 'deviation': 71},
                    {'name': '厚木高等学校', 'type': '普通科', 'location': '厚木市', 'deviation': 67},
                    {'name': '小田原高等学校', 'type': '普通科', 'location': '小田原市', 'deviation': 64},
                    {'name': '平塚江南高等学校', 'type': '普通科', 'location': '平塚市', 'deviation': 63},
                    {'name': '茅ヶ崎北陵高等学校', 'type': '普通科', 'location': '茅ヶ崎市', 'deviation': 61},
                    {'name': '大和高等学校', 'type': '普通科', 'location': '大和市', 'deviation': 60},
                    {'name': '横浜緑ヶ丘高等学校', 'type': '普通科', 'location': '横浜市中区', 'deviation': 59},
                    {'name': '希望ヶ丘高等学校', 'type': '普通科', 'location': '横浜市旭区', 'deviation': 58},
                    {'name': '鎌倉高等学校', 'type': '普通科', 'location': '鎌倉市', 'deviation': 57}
                ]
                success = f"{year}年度の高校情報 {len(high_schools_data)}校を取得しました。"
                
            elif action == 'manual_entry':
                # 手動登録処理
                school_name = request.form.get('school_name')
                if school_name:
                    success = f"高校「{school_name}」を登録しました。"
                else:
                    error = "学校名を入力してください。"
                
        except Exception as e:
            log_error(f"Error in fetch high schools: {e}")
            error = f"高校情報の取得中にエラーが発生しました: {str(e)}"
    
    # ダミーの取得履歴データ
    import_history = [
        {
            'import_date': datetime(2024, 4, 15, 10, 30),
            'year': 2024,
            'record_count': 150,
            'file_name': 'ウェブ取得',
            'teacher_name': session.get('name', '不明')
        },
        {
            'import_date': datetime(2024, 3, 10, 14, 20),
            'year': 2024,
            'record_count': 142,
            'file_name': 'kanagawa_schools.csv',
            'teacher_name': session.get('name', '不明')
        }
    ]
    
    # テンプレートをレンダリング
    return render_template('fetch_high_schools.html', 
                         success=success, 
                         error=error, 
                         high_schools=high_schools_data,
                         current_year=current_year,
                         import_history=import_history)

@app.route('/admin/import-eiken-words', methods=['GET', 'POST'])
def admin_import_eiken_words():
    """英検単語インポート機能（エラー修正版・テンプレート不要版）"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    success = None
    error = None
    
    if request.method == 'POST':
        try:
            grade = request.form.get('grade')
            overwrite = request.form.get('overwrite') == '1'
            
            if 'csv_file' not in request.files:
                error = "ファイルがアップロードされていません"
            else:
                file = request.files['csv_file']
                if file.filename == '':
                    error = "ファイルが選択されていません"
                elif not file.filename.lower().endswith('.csv'):
                    error = "CSV形式のファイル（.csv）をアップロードしてください"
                else:
                    try:
                        # ファイル内容を読み込む
                        file_content = file.read().decode('utf-8')
                        
                        # CSVからデータをインポート
                        result = import_eiken_words_from_csv(file_content, grade, session.get('user_id'), overwrite)
                        
                        if result['success']:
                            success = result['message']
                        else:
                            error = result['message']
                    
                    except UnicodeDecodeError:
                        # UTF-8としてデコードできない場合、他のエンコーディングを試す
                        try:
                            file.seek(0)  # ファイルポインタをリセット
                            file_content = file.read().decode('shift-jis')
                            
                            result = import_eiken_words_from_csv(file_content, grade, session.get('user_id'), overwrite)
                            
                            if result['success']:
                                success = result['message'] + "（注：Shift-JISエンコーディングとして処理しました）"
                            else:
                                error = result['message']
                        except Exception as e:
                            log_error(f"Error importing with shift-jis encoding: {e}")
                            error = f"ファイルのエンコーディングを認識できません。UTF-8またはShift-JISでエンコードされたCSVファイルを使用してください。"
                    
                    except Exception as e:
                        log_error(f"Error importing eiken words: {e}")
                        error = f"CSVファイルの処理中にエラーが発生しました: {str(e)}"
        except Exception as outer_e:
            log_error(f"Outer exception in admin_import_eiken_words: {outer_e}")
            error = f"処理中にエラーが発生しました: {str(outer_e)}"
    
    # テンプレートの代わりに直接HTMLを返す
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>英検単語インポート</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }}
            .container {{ background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            .form-group {{ margin-bottom: 15px; }}
            label {{ display: block; margin-bottom: 5px; font-weight: 500; }}
            input, select {{ padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }}
            button {{ background: #4285f4; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; font-size: 14px; }}
            button:hover {{ background: #3367d6; }}
            .alert-success {{ background-color: #d4edda; color: #155724; padding: 10px; border-radius: 4px; margin-bottom: 15px; }}
            .alert-danger {{ background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin-bottom: 15px; }}
            .nav {{ margin-bottom: 20px; }}
            .nav a {{ display: inline-block; margin-right: 10px; color: #1a73e8; text-decoration: none; }}
            .nav a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/myapp/index.cgi/teacher/dashboard">ダッシュボードに戻る</a>
        </div>
        
        <div class="container">
            <h1>英検単語インポートツール</h1>
            
            {f'<div class="alert-success">{success}</div>' if success else ''}
            {f'<div class="alert-danger">{error}</div>' if error else ''}
            
            <form method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="grade">英検級:</label>
                    <select name="grade" id="grade" required>
                        <option value="5">5級</option>
                        <option value="4">4級</option>
                        <option value="3">3級</option>
                        <option value="準2級">準2級</option>
                        <option value="2">2級</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="csv_file">CSVファイル:</label>
                    <input type="file" name="csv_file" id="csv_file" required accept=".csv">
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" name="overwrite" value="1">
                        既存のデータを上書きする
                    </label>
                </div>
                
                <div class="form-group">
                    <button type="submit">インポート開始</button>
                </div>
            </form>
            
            <div>
                <h3>CSVファイル形式</h3>
                <p>以下の列を含むCSVファイルを準備してください:</p>
                <ul>
                    <li>QuestionID（問題ID）: 数値</li>
                    <li>StageNumber（ステージ番号）: 数値</li>
                    <li>QuestionText（英単語）: テキスト</li>
                    <li>CorrectAnswer（発音・意味）: テキスト</li>
                    <li>AudioURL（音声ファイルURL）: URL (オプション)</li>
                </ul>
                <p>CSVファイルはUTF-8またはShift-JISエンコーディングで保存してください。</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def ensure_eiken_progress_table(conn):
    """英検単語学習進捗テーブルを確認・作成する"""
    try:
        with conn.cursor() as cur:
            # 進捗管理テーブルの作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS eiken_word_progress (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    word_id INT NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'new' COMMENT '進捗状態 (new, learning, mastered)',
                    correct_count INT NOT NULL DEFAULT 0 COMMENT '正解回数',
                    incorrect_count INT NOT NULL DEFAULT 0 COMMENT '不正解回数',
                    last_reviewed_at TIMESTAMP NULL COMMENT '最後に学習した日時',
                    next_review_at TIMESTAMP NULL COMMENT '次回学習予定日時',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_student_word (student_id, word_id),
                    INDEX idx_student_status (student_id, status),
                    INDEX idx_next_review (student_id, next_review_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """)
            
            log_error("eiken_word_progress テーブルを確認/作成しました")
            conn.commit()
    except Exception as e:
        log_error(f"Error creating eiken_word_progress table: {e}")
        conn.rollback()

@app.route('/api/eiken-progress/update', methods=['POST'])
def update_eiken_progress():
    """英検単語学習進捗を更新するAPI"""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    student_id = session.get('user_id')
    data = request.json
    
    if not data or 'word_id' not in data:
        return jsonify({'success': False, 'message': '必要なデータが不足しています'}), 400
    
    word_id = data.get('word_id')
    is_correct = data.get('is_correct', True)  # デフォルトはTrue
    status = data.get('status')  # 新しいステータス（任意）
    
    try:
        conn = get_db_connection()
        
        # テーブルの存在確認と作成
        ensure_eiken_progress_table(conn)
        
        with conn.cursor() as cur:
            # 現在の進捗データを取得
            cur.execute("""
                SELECT * FROM eiken_word_progress
                WHERE student_id = %s AND word_id = %s
            """, (student_id, word_id))
            
            progress = cur.fetchone()
            
            current_timestamp = datetime.now()
            
            if progress:
                # 既存データを更新
                correct_count = progress['correct_count']
                incorrect_count = progress['incorrect_count']
                
                if is_correct:
                    correct_count += 1
                else:
                    incorrect_count += 1
                
                # ステータスの自動決定（ユーザー指定がない場合）
                if not status:
                    total_attempts = correct_count + incorrect_count
                    correct_rate = correct_count / total_attempts if total_attempts > 0 else 0
                    
                    if total_attempts >= 5 and correct_rate >= 0.8:
                        status = 'mastered'  # 5回以上挑戦して正解率80%以上なら習得済み
                    elif total_attempts >= 2:
                        status = 'learning'  # 2回以上挑戦していれば学習中
                    else:
                        status = 'new'       # それ以外は新規
                
                # 次回学習日の計算（間隔反復学習の原理に基づく）
                next_review_at = None
                if status == 'mastered':
                    # 習得済みの場合は1週間後
                    next_review_at = current_timestamp + timedelta(days=7)
                elif status == 'learning':
                    # 学習中の場合は1〜3日後（正解率に応じて）
                    days = 1 + int(correct_rate * 2)  # 正解率に応じて1〜3日
                    next_review_at = current_timestamp + timedelta(days=days)
                else:
                    # 新規の場合は1日後
                    next_review_at = current_timestamp + timedelta(days=1)
                
                # データ更新
                cur.execute("""
                    UPDATE eiken_word_progress
                    SET correct_count = %s,
                        incorrect_count = %s,
                        status = %s,
                        last_reviewed_at = %s,
                        next_review_at = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    correct_count, 
                    incorrect_count, 
                    status, 
                    current_timestamp, 
                    next_review_at, 
                    progress['id']
                ))
                
                progress_id = progress['id']
            else:
                # 新規データの作成
                correct_count = 1 if is_correct else 0
                incorrect_count = 0 if is_correct else 1
                
                # ステータスの初期設定
                if not status:
                    status = 'new'
                
                # 次回学習日（初回は翌日）
                next_review_at = current_timestamp + timedelta(days=1)
                
                # データ挿入
                cur.execute("""
                    INSERT INTO eiken_word_progress
                    (student_id, word_id, status, correct_count, incorrect_count, 
                     last_reviewed_at, next_review_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    student_id, 
                    word_id, 
                    status, 
                    correct_count, 
                    incorrect_count, 
                    current_timestamp, 
                    next_review_at
                ))
                
                progress_id = cur.lastrowid
        
        conn.commit()
        
        # 応答データを作成
        result = {
            'success': True,
            'progress_id': progress_id,
            'status': status,
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'is_correct': is_correct,
            'message': '進捗を更新しました'
        }
        
        return jsonify(result)
    
    except Exception as e:
        log_error(f"Error updating eiken progress: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/eiken-progress/stats')
def get_eiken_progress_stats():
    """英検単語学習進捗の統計情報を取得するAPI"""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': '認証エラーです'}), 401
    
    student_id = session.get('user_id')
    grade = request.args.get('grade', '5')  # デフォルトは5級
    
    try:
        conn = get_db_connection()
        
        # テーブルの存在確認と作成
        ensure_eiken_progress_table(conn)
        
        with conn.cursor() as cur:
            # 単語の総数を取得
            cur.execute("""
                SELECT COUNT(*) as total FROM eiken_words
                WHERE grade = %s
            """, (grade,))
            
            total_result = cur.fetchone()
            total_words = total_result['total'] if total_result else 0
            
            # 進捗状態別の単語数を取得
            cur.execute("""
                SELECT p.status, COUNT(*) as count
                FROM eiken_word_progress p
                JOIN eiken_words w ON p.word_id = w.id
                WHERE p.student_id = %s AND w.grade = %s
                GROUP BY p.status
            """, (student_id, grade))
            
            status_counts = {row['status']: row['count'] for row in cur.fetchall()}
            
            # 今日学習すべき単語数を取得（次回学習日が今日以前のもの）
            today = datetime.now().date()
            cur.execute("""
                SELECT COUNT(*) as count
                FROM eiken_word_progress p
                JOIN eiken_words w ON p.word_id = w.id
                WHERE p.student_id = %s 
                  AND w.grade = %s
                  AND (p.next_review_at IS NULL OR DATE(p.next_review_at) <= %s)
            """, (student_id, grade, today))
            
            due_result = cur.fetchone()
            due_words = due_result['count'] if due_result else 0
            
            # 進捗率の計算
            mastered_count = status_counts.get('mastered', 0)
            learning_count = status_counts.get('learning', 0)
            new_count = status_counts.get('new', 0)
            studied_count = mastered_count + learning_count + new_count
            
            # 未学習の単語数
            not_studied = total_words - studied_count
            
            # 習得率の計算（総単語数に対する習得済み単語の割合）
            mastery_rate = (mastered_count / total_words) * 100 if total_words > 0 else 0
            
            # 開始率の計算（何らかの形で学習を開始した単語の割合）
            started_rate = (studied_count / total_words) * 100 if total_words > 0 else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'grade': grade,
            'total_words': total_words,
            'stats': {
                'mastered': mastered_count,
                'learning': learning_count,
                'new': new_count,
                'not_studied': not_studied,
                'due_today': due_words
            },
            'rates': {
                'mastery_rate': round(mastery_rate, 1),
                'started_rate': round(started_rate, 1)
            }
        })
    
    except Exception as e:
        log_error(f"Error getting eiken progress stats: {e}")
        if 'conn' in locals():
            conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/student/eiken-words-tts')
def student_eiken_words_tts():
    """英検単語学習ページ（TTS音声機能付き）"""
    if not session.get('user_id'):
        return redirect('/myapp/index.cgi/login')
    
    # 講師モードの判定
    teacher_view = request.args.get('teacher_view') == 'true'
    is_teacher_login = session.get('is_teacher_login', False)
    
    # 表示対象の生徒IDを決定
    if teacher_view and is_teacher_login:
        # 講師モードの場合
        student_id = request.args.get('id', session.get('viewing_student_id', session.get('user_id')))
    else:
        # 通常の生徒モードの場合
        student_id = session.get('user_id')
        teacher_view = False
    
    user_id = session.get('user_id')
    user_name = session.get('user_name', '')
    
    # 直接HTMLを返す
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>英検単語学習</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; padding: 20px; margin: 0; background-color: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .card {{ background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            .word-container {{ display: flex; flex-wrap: wrap; gap: 15px; }}
            .word-card {{ background: white; border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 10px; width: calc(33% - 15px); }}
            .word {{ font-size: 1.5em; font-weight: bold; margin-bottom: 10px; color: #1a73e8; }}
            .pronunciation {{ color: #666; }}
            .katakana-pronunciation {{ color: #e67c73; font-size: 0.9em; margin: 5px 0; }}
            .audio-btn {{ background: #4285f4; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; margin-right: 5px; }}
            .settings-btn {{ background: #f5f5f5; color: #333; border: 1px solid #ddd; padding: 5px 10px; border-radius: 4px; cursor: pointer; }}
            .filters {{ margin-bottom: 20px; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            .filter-group {{ display: flex; gap: 10px; align-items: center; margin-bottom: 10px; }}
            .filter-label {{ font-weight: bold; width: 80px; }}
            select, input {{ padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
            button {{ background: #4285f4; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; }}
            button:hover {{ background: #3367d6; }}
            .pagination {{ display: flex; justify-content: center; gap: 5px; margin-top: 20px; }}
            .pagination button {{ padding: 5px 10px; background: #f1f1f1; color: #333; }}
            .pagination button.active {{ background: #4285f4; color: white; }}
            .loading {{ text-align: center; padding: 20px; }}
            .stats {{ display: flex; gap: 15px; margin-bottom: 20px; }}
            .stat-card {{ flex: 1; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; }}
            .stat-value {{ font-size: 1.8em; font-weight: bold; color: #1a73e8; }}
            .stat-label {{ color: #666; }}
            .nav {{ margin-bottom: 20px; }}
            .nav a {{ display: inline-block; margin-right: 10px; color: #1a73e8; text-decoration: none; }}
            .nav a:hover {{ text-decoration: underline; }}
            
            /* モーダル用スタイル */
            .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 1000; }}
            .modal-content {{ background-color: white; margin: 15% auto; padding: 20px; border-radius: 8px; width: 80%; max-width: 500px; }}
            .close {{ float: right; cursor: pointer; font-size: 24px; }}
            .close:hover {{ color: #777; }}
            .settings-group {{ margin-bottom: 15px; }}
            .settings-title {{ font-weight: bold; margin-bottom: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="nav">
                <a href="/myapp/index.cgi/student/dashboard{"?teacher_view=true&id=" + str(student_id) if teacher_view else ""}">ダッシュボードに戻る</a>
            </div>
            
            <h1>英検単語学習</h1>
            
            <div class="stats">
                <div class="stat-card">
                    <div id="mastered-count" class="stat-value">-</div>
                    <div class="stat-label">習得済み</div>
                </div>
                <div class="stat-card">
                    <div id="learning-count" class="stat-value">-</div>
                    <div class="stat-label">学習中</div>
                </div>
                <div class="stat-card">
                    <div id="total-count" class="stat-value">-</div>
                    <div class="stat-label">全単語数</div>
                </div>
                <div class="stat-card">
                    <div id="mastery-rate" class="stat-value">-</div>
                    <div class="stat-label">習得率</div>
                </div>
            </div>
            
            <div class="filters card">
                <h3>検索フィルター</h3>
                <div class="filter-group">
                    <div class="filter-label">英検級:</div>
                    <select id="grade-filter">
                        <option value="5">5級</option>
                        <option value="4">4級</option>
                        <option value="3">3級</option>
                        <option value="準2級">準2級</option>
                        <option value="2">2級</option>
                    </select>
                </div>
                <div class="filter-group">
                    <div class="filter-label">検索:</div>
                    <input type="text" id="search-input" placeholder="単語を検索...">
                </div>
                <div class="filter-group">
                    <div class="filter-label">ステージ:</div>
                    <select id="stage-filter">
                        <option value="">すべて</option>
                        <option value="1">ステージ1</option>
                        <option value="2">ステージ2</option>
                        <option value="3">ステージ3</option>
                    </select>
                </div>
                <div class="filter-group">
                    <button id="apply-filters">フィルター適用</button>
                    <button id="reset-filters">リセット</button>
                    <button id="voice-settings-btn" class="settings-btn">🔊 音声設定</button>
                </div>
            </div>
            
            <div id="words-container" class="card">
                <div id="loading" class="loading">単語データを読み込み中...</div>
                <div id="word-list" class="word-container"></div>
                <div id="pagination" class="pagination"></div>
            </div>
        </div>
        
        <!-- 音声設定モーダル -->
        <div id="voice-settings-modal" class="modal">
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2>音声設定</h2>
                
                <div class="settings-group">
                    <div class="settings-title">音声選択:</div>
                    <select id="voice-select">
                        <option value="">読み込み中...</option>
                    </select>
                </div>
                
                <div class="settings-group">
                    <div class="settings-title">速度:</div>
                    <input type="range" id="rate-range" min="0.5" max="2" step="0.1" value="1">
                    <span id="rate-value">1</span>
                </div>
                
                <div class="settings-group">
                    <div class="settings-title">ピッチ:</div>
                    <input type="range" id="pitch-range" min="0.5" max="2" step="0.1" value="1">
                    <span id="pitch-value">1</span>
                </div>
                
                <div class="settings-group">
                    <div class="settings-title">テスト:</div>
                    <input type="text" id="test-text" value="Hello, this is a test.">
                    <button id="test-voice-btn">テスト再生</button>
                </div>
                
                <button id="save-settings-btn">設定を保存</button>
            </div>
        </div>
        
        <script>
            // 状態管理
            const state = {{
                grade: '5',
                page: 1,
                search: '',
                stage: '',
                totalPages: 1,
                words: [],
                voiceSettings: {{
                    voice: null,
                    rate: 1,
                    pitch: 1
                }}
            }};
            
            // 音声合成初期化
            let synth = window.speechSynthesis;
            let voices = [];
            
            // 音声一覧が読み込まれたときのイベント
            function loadVoices() {{
                voices = synth.getVoices();
            }}
            
            // 音声一覧の読み込み
            loadVoices();
            if (synth.onvoiceschanged !== undefined) {{
                synth.onvoiceschanged = loadVoices;
            }}
            
            // DOM要素
            const gradeFilter = document.getElementById('grade-filter');
            const searchInput = document.getElementById('search-input');
            const stageFilter = document.getElementById('stage-filter');
            const applyFiltersBtn = document.getElementById('apply-filters');
            const resetFiltersBtn = document.getElementById('reset-filters');
            const wordList = document.getElementById('word-list');
            const loading = document.getElementById('loading');
            const pagination = document.getElementById('pagination');
            
            // 音声設定モーダル要素
            const voiceSettingsBtn = document.getElementById('voice-settings-btn');
            const voiceSettingsModal = document.getElementById('voice-settings-modal');
            const closeModalBtn = document.querySelector('.close');
            const voiceSelect = document.getElementById('voice-select');
            const rateRange = document.getElementById('rate-range');
            const rateValue = document.getElementById('rate-value');
            const pitchRange = document.getElementById('pitch-range');
            const pitchValue = document.getElementById('pitch-value');
            const testTextInput = document.getElementById('test-text');
            const testVoiceBtn = document.getElementById('test-voice-btn');
            const saveSettingsBtn = document.getElementById('save-settings-btn');
            
            // 単語データの取得
            async function fetchWords() {{
                loading.style.display = 'block';
                wordList.innerHTML = '';
                pagination.innerHTML = '';
                
                try {{
                    // クエリパラメータの構築
                    const params = new URLSearchParams();
                    params.append('grade', state.grade);
                    params.append('page', state.page);
                    params.append('per_page', 20);
                    
                    if (state.search) {{
                        params.append('search', state.search);
                    }}
                    
                    if (state.stage) {{
                        params.append('stage', state.stage);
                    }}
                    
                    // APIリクエスト
                    const response = await fetch(`/api/eiken-words?${{params.toString()}}`);
                    const data = await response.json();
                    
                    if (data.success) {{
                        state.words = data.words || [];
                        state.totalPages = data.pagination.total_pages || 1;
                        
                        // 単語リストの表示
                        renderWords();
                        // ページネーションの表示
                        renderPagination();
                    }} else {{
                        wordList.innerHTML = `<p>データの取得に失敗しました: ${{data.message || 'エラーが発生しました'}}</p>`;
                    }}
                }} catch (error) {{
                    wordList.innerHTML = `<p>エラー: ${{error.message || 'データの取得中にエラーが発生しました'}}</p>`;
                }} finally {{
                    loading.style.display = 'none';
                }}
            }}
            
            // 統計情報の取得
            async function fetchStats() {{
                try {{
                    const response = await fetch(`/myapp/index.cgi/api/eiken-progress/stats?grade=${{state.grade}}`);
                    const data = await response.json();
                    
                    if (data.success) {{
                        document.getElementById('mastered-count').textContent = data.stats?.mastered || 0;
                        document.getElementById('learning-count').textContent = data.stats?.learning || 0;
                        document.getElementById('total-count').textContent = data.total_words || 0;
                        document.getElementById('mastery-rate').textContent = `${{data.rates?.mastery_rate || 0}}%`;
                    }}
                }} catch (error) {{
                    console.error('統計情報の取得に失敗しました:', error);
                }}
            }}
            
            // 単語リストの表示
            function renderWords() {{
                if (state.words.length === 0) {{
                    wordList.innerHTML = '<p>条件に一致する単語がありません</p>';
                    return;
                }}
                
                wordList.innerHTML = state.words.map(word => {{
                    // 英単語のカタカナ発音を取得
                    const katakana = englishToKatakana(word.pronunciation || '');
                    
                    return `
                    <div class="word-card" data-id="${{word.id}}">
                        <div class="word">${{word.word}}</div>
                        <div class="pronunciation">${{word.pronunciation || ''}}</div>
                        <div class="katakana-pronunciation">${{katakana}}</div>
                        <div>
                            <button class="audio-btn" onclick="speakWord('${{word.word}}', null, '${{word.pronunciation || ''}}')">▶ 音声</button>
                            <button class="audio-btn" onclick="speakSlow('${{word.word}}', '${{word.pronunciation || ''}}')">🐢 ゆっくり</button>
                        </div>
                        <div>ステージ: ${{word.stage_number || 1}}</div>
                    </div>
                `).join('');
            }}
            
            // ページネーションの表示
            function renderPagination() {{
                if (state.totalPages <= 1) return;
                
                let paginationHtml = '';
                
                // 前へボタン
                paginationHtml += `
                    <button ${{state.page === 1 ? 'disabled' : ''}} 
                            onclick="changePage(${{state.page - 1}})">前へ</button>
                `;
                
                // ページ番号
                for (let i = 1; i <= state.totalPages; i++) {{
                    if (
                        i === 1 || 
                        i === state.totalPages || 
                        (i >= state.page - 2 && i <= state.page + 2)
                    ) {{
                        paginationHtml += `
                            <button class="${{i === state.page ? 'active' : ''}}" 
                                    onclick="changePage(${{i}})">${{i}}</button>
                        `;
                    }} else if (
                        i === state.page - 3 || 
                        i === state.page + 3
                    ) {{
                        paginationHtml += `<span>...</span>`;
                    }}
                }}
                
                // 次へボタン
                paginationHtml += `
                    <button ${{state.page === state.totalPages ? 'disabled' : ''}} 
                            onclick="changePage(${{state.page + 1}})">次へ</button>
                `;
                
                pagination.innerHTML = paginationHtml;
            }}
            
            // 単語読み上げ機能（英単語のみ発音）
            function speakWord(text, audioUrl, pronunciation) {{
                // 再生中の音声をすべて停止
                synth.cancel();
                
                // 英単語を読み上げる（日本語部分はスキップ）
                if (pronunciation) {{
                    // 日本語文字（ひらがな、カタカナ、漢字）を除去
                    const englishOnly = pronunciation.replace(/[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u3400-\u4dbf]/g, "").trim();
                    
                    // 英単語を読み上げるための設定
                    const utteranceEng = new SpeechSynthesisUtterance(englishOnly);
                    
                    // 音声設定を適用
                    if (state.voiceSettings.voice) {{
                        utteranceEng.voice = state.voiceSettings.voice;
                    }}
                    utteranceEng.lang = 'en-US'; // 英語設定
                    utteranceEng.rate = state.voiceSettings.rate;
                    utteranceEng.pitch = state.voiceSettings.pitch;
                    
                    synth.speak(utteranceEng);
                }}
            }}
            
            // ゆっくり読み上げ機能（英単語のみ発音）
            function speakSlow(text, pronunciation) {{
                // 再生中の音声をすべて停止
                synth.cancel();
                
                // 英単語をゆっくり発音（日本語部分はスキップ）
                if (pronunciation) {{
                    // 日本語文字（ひらがな、カタカナ、漢字）を除去
                    const englishOnly = pronunciation.replace(/[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u3400-\u4dbf]/g, "").trim();
                    
                    // 英単語を読み上げるための設定
                    const utteranceEng = new SpeechSynthesisUtterance(englishOnly);
                    
                    // 音声設定を適用（速度を半分に）
                    if (state.voiceSettings.voice) {{
                        utteranceEng.voice = state.voiceSettings.voice;
                    }}
                    utteranceEng.lang = 'en-US'; // 英語設定
                    utteranceEng.rate = state.voiceSettings.rate * 0.5; // 半分の速さ
                    utteranceEng.pitch = state.voiceSettings.pitch;
                    
                    synth.speak(utteranceEng);
                }}
            }}
            
            // 音声設定モーダルを開く
            function openVoiceSettingsModal() {{
                voiceSettingsModal.style.display = 'block';
                loadVoices();
            }}
            
            // 音声設定モーダルを閉じる
            function closeVoiceSettingsModal() {{
                voiceSettingsModal.style.display = 'none';
            }}
            
            // 音声リストの読み込み
            function loadVoices() {{
                voices = synth.getVoices();
                
                // 英語の音声のみをフィルタリング
                const englishVoices = voices.filter(voice => voice.lang.includes('en'));
                
                voiceSelect.innerHTML = englishVoices.map(voice =>
                    `<option value="${{voice.name}}" ${{
                        state.voiceSettings.voice && state.voiceSettings.voice.name === voice.name ? 'selected' : ''
                    }}>${{voice.name}} (${{voice.lang}})</option>`
                ).join('');
                
                if (!state.voiceSettings.voice && englishVoices.length > 0) {{
                    state.voiceSettings.voice = englishVoices[0];
                }}
            }}
            
            // テスト音声の再生
            function testVoice() {{
                const selectedVoiceName = voiceSelect.value;
                const selectedVoice = voices.find(voice => voice.name === selectedVoiceName);
                
                const rate = parseFloat(rateRange.value);
                const pitch = parseFloat(pitchRange.value);
                const text = testTextInput.value;
                
                synth.cancel();
                
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.voice = selectedVoice;
                utterance.rate = rate;
                utterance.pitch = pitch;
                
                synth.speak(utterance);
            }}
            
            // 音声設定の保存
            function saveVoiceSettings() {{
                const selectedVoiceName = voiceSelect.value;
                const selectedVoice = voices.find(voice => voice.name === selectedVoiceName);
                
                state.voiceSettings.voice = selectedVoice;
                state.voiceSettings.rate = parseFloat(rateRange.value);
                state.voiceSettings.pitch = parseFloat(pitchRange.value);
                
                // ローカルストレージに保存
                try {{
                    localStorage.setItem('eiken_voice_settings', JSON.stringify({{
                        voiceName: selectedVoice.name,
                        rate: state.voiceSettings.rate,
                        pitch: state.voiceSettings.pitch
                    }}));
                }} catch (e) {{
                    console.error('設定の保存に失敗しました:', e);
                }}
                
                closeVoiceSettingsModal();
            }}
            
            // ページ変更
            function changePage(page) {{
                state.page = page;
                fetchWords();
                window.scrollTo(0, 0);
            }}
            
            // イベントリスナー
            applyFiltersBtn.addEventListener('click', () => {{
                state.grade = gradeFilter.value;
                state.search = searchInput.value;
                state.stage = stageFilter.value;
                state.page = 1;
                fetchWords();
                fetchStats();
            }});
            
            resetFiltersBtn.addEventListener('click', () => {{
                gradeFilter.value = '5';
                searchInput.value = '';
                stageFilter.value = '';
                state.grade = '5';
                state.search = '';
                state.stage = '';
                state.page = 1;
                fetchWords();
                fetchStats();
            }});
            
            voiceSettingsBtn.addEventListener('click', openVoiceSettingsModal);
            closeModalBtn.addEventListener('click', closeVoiceSettingsModal);
            testVoiceBtn.addEventListener('click', testVoice);
            saveSettingsBtn.addEventListener('click', saveVoiceSettings);
            
            // レンジの値表示
            rateRange.addEventListener('input', () => {{
                rateValue.textContent = rateRange.value;
            }});
            
            pitchRange.addEventListener('input', () => {{
                pitchValue.textContent = pitchRange.value;
            }});
            
            // 音声リストの読み込み
            if (synth.onvoiceschanged !== undefined) {{
                synth.onvoiceschanged = loadVoices;
            }}
            
            // 保存された設定を読み込む
            function loadSavedSettings() {{
                try {{
                    const savedSettings = localStorage.getItem('eiken_voice_settings');
                    if (savedSettings) {{
                        const settings = JSON.parse(savedSettings);
                        rateRange.value = settings.rate;
                        rateValue.textContent = settings.rate;
                        pitchRange.value = settings.pitch;
                        pitchValue.textContent = settings.pitch;
                        
                        state.voiceSettings.rate = settings.rate;
                        state.voiceSettings.pitch = settings.pitch;
                        
                        // 音声は後で設定
                        setTimeout(() => {{
                            if (voices.length > 0) {{
                                const voice = voices.find(v => v.name === settings.voiceName);
                                if (voice) {{
                                    state.voiceSettings.voice = voice;
                                    voiceSelect.value = voice.name;
                                }}
                            }}
                        }}, 100);
                    }}
                }} catch (e) {{
                    console.error('設定の読み込みに失敗しました:', e);
                }}
            }}
            
            // 初期データ読み込み
            document.addEventListener('DOMContentLoaded', () => {{
                fetchWords();
                fetchStats();
                loadSavedSettings();
                setTimeout(loadVoices, 100); // 少し遅延させて音声を読み込む
            }});
            
            // グローバルに関数を公開
            window.speakWord = speakWord;
            window.speakSlow = speakSlow;
            window.changePage = changePage;
        </script>
    </body>
    </html>
    """
    
    return html



# フロントエンド用デバッグツール
@app.route('/debug/api-tester')
def debug_api_tester():
    """APIテスト用のフロントエンドページ"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return redirect('/myapp/index.cgi/login')
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Debug Tester</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                padding: 20px;
                max-width: 1200px;
                margin: 0 auto;
                line-height: 1.5;
            }
            .card {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 20px;
                margin-bottom: 20px;
            }
            h1, h2, h3 {
                color: #333;
            }
            pre {
                background: #f5f5f5;
                padding: 10px;
                border-radius: 5px;
                overflow: auto;
                max-height: 400px;
            }
            button {
                background: #4285f4;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }
            button:hover {
                background: #3367d6;
            }
            input, select {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
                margin-bottom: 10px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: 500;
            }
            .form-group {
                margin-bottom: 15px;
            }
            .result {
                margin-top: 20px;
            }
            .error {
                color: #d32f2f;
                background: #ffebee;
                padding: 10px;
                border-radius: 4px;
                border-left: 4px solid #d32f2f;
            }
            .nav {
                margin-bottom: 20px;
            }
            .nav a {
                display: inline-block;
                margin-right: 10px;
                color: #1a73e8;
                text-decoration: none;
            }
            .nav a:hover {
                text-decoration: underline;
            }
            .tab-content > div {
                display: none;
            }
            .tab-content > div.active {
                display: block;
            }
            .tabs {
                display: flex;
                border-bottom: 1px solid #ddd;
                margin-bottom: 15px;
            }
            .tab {
                padding: 8px 16px;
                cursor: pointer;
                border-bottom: 2px solid transparent;
            }
            .tab.active {
                border-bottom-color: #4285f4;
                color: #4285f4;
                font-weight: 500;
            }
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/myapp/index.cgi/teacher/dashboard">ダッシュボードに戻る</a>
        </div>
        <h1>APIデバッグツール</h1>
        
        <div class="tabs">
            <div class="tab active" data-tab="info">システム情報</div>
            <div class="tab" data-tab="students">生徒API</div>
            <div class="tab" data-tab="homework">宿題API</div>
            <div class="tab" data-tab="query">SQLクエリ</div>
            <div class="tab" data-tab="attendance">出席API</div>
        </div>
        
        <div class="tab-content">
            <div id="info-tab" class="active">
                <div class="card">
                    <h2>システム情報</h2>
                    <button id="load-debug-info">デバッグ情報を読み込む</button>
                    <div class="result" id="debug-info-result"></div>
                </div>
            </div>
            
            <div id="students-tab">
                <div class="card">
                    <h2>生徒API テスト</h2>
                    <div class="form-group">
                        <label for="grade-filter">学年フィルター:</label>
                        <select id="grade-filter">
                            <option value="all">全て</option>
                            <option value="elementary">小学生</option>
                            <option value="middle">中学生</option>
                            <option value="high">高校生</option>
                            <option value="1">1年生</option>
                            <option value="2">2年生</option>
                            <option value="3">3年生</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="day-filter">曜日フィルター:</label>
                        <select id="day-filter">
                            <option value="all">全て</option>
                            <option value="0">日曜日</option>
                            <option value="1">月曜日</option>
                            <option value="2">火曜日</option>
                            <option value="3">水曜日</option>
                            <option value="4">木曜日</option>
                            <option value="5">金曜日</option>
                            <option value="6">土曜日</option>
                            <option value="today">今日</option>
                        </select>
                    </div>
                    <button id="test-students-api">生徒APIをテスト</button>
                    <div class="result" id="students-api-result"></div>
                </div>
            </div>
            
            <div id="homework-tab">
                <div class="card">
                    <h2>宿題API テスト</h2>
                    <div class="form-group">
                        <label for="homework-student-id">生徒ID:</label>
                        <input type="number" id="homework-student-id" value="1">
                    </div>
                    <div class="form-group">
                        <label for="homework-year">年:</label>
                        <input type="number" id="homework-year" value="">
                    </div>
                    <div class="form-group">
                        <label for="homework-month">月:</label>
                        <input type="number" id="homework-month" value="" min="1" max="12">
                    </div>
                    <button id="test-homework-calendar">カレンダーAPIをテスト</button>
                    <button id="test-homework-list">宿題リストAPIをテスト</button>
                    <button id="test-homework-stats">統計APIをテスト</button>
                    <div class="result" id="homework-api-result"></div>
                </div>
            </div>
            
            <div id="query-tab">
                <div class="card">
                    <h2>SQLクエリ実行</h2>
                    <div class="form-group">
                        <label for="query-input">SQL:</label>
                        <textarea id="query-input" style="width: 100%; height: 100px;">SELECT * FROM users WHERE role = 'student' LIMIT 10</textarea>
                    </div>
                    <div class="form-group">
                        <label for="params-input">パラメータ (JSON形式):</label>
                        <input type="text" id="params-input" value="[]" style="width: 100%;">
                    </div>
                    <button id="run-query">クエリ実行</button>
                    <div class="result" id="query-result"></div>
                </div>
            </div>
            
            <div id="attendance-tab">
                <div class="card">
                    <h2>出席API テスト</h2>
                    <div class="form-group">
                        <label for="student-id">生徒ID:</label>
                        <input type="number" id="student-id" value="1">
                    </div>
                    <div class="form-group">
                        <label for="attendance-date">日付:</label>
                        <input type="date" id="attendance-date" value="">
                    </div>
                    <div class="form-group">
                        <label for="attendance-status">出席状態:</label>
                        <select id="attendance-status">
                            <option value="present">出席</option>
                            <option value="absent">欠席</option>
                            <option value="late">遅刻</option>
                            <option value="excused">欠席（届出あり）</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="award-points" checked>
                            ポイント付与（出席の場合）
                        </label>
                    </div>
                    <button id="test-attendance-api">出席記録をテスト</button>
                    <div class="result" id="attendance-api-result"></div>
                </div>
            </div>
        </div>
        
        <script>
            // タブ切り替え
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', function() {
                    // アクティブタブを変更
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    this.classList.add('active');
                    
                    // タブコンテンツを切り替え
                    const tabId = this.dataset.tab;
                    document.querySelectorAll('.tab-content > div').forEach(content => {
                        content.classList.remove('active');
                    });
                    document.getElementById(tabId + '-tab').classList.add('active');
                });
            });
            
            // 今日の日付をセット
            document.getElementById('attendance-date').value = new Date().toISOString().split('T')[0];
            
            // 宿題APIテスト用の現在年月をセット
            const now = new Date();
            document.getElementById('homework-year').value = now.getFullYear();
            document.getElementById('homework-month').value = now.getMonth() + 1;
            
            // デバッグ情報を取得
            document.getElementById('load-debug-info').addEventListener('click', function() {
                const resultDiv = document.getElementById('debug-info-result');
                resultDiv.innerHTML = '<p>読み込み中...</p>';
                
                fetch('/myapp/index.cgi/api/debug/info')
                    .then(response => response.json())
                    .then(data => {
                        resultDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    })
                    .catch(error => {
                        resultDiv.innerHTML = '<div class="error">エラー: ' + error.message + '</div>';
                    });
            });
            
            // 宿題APIテスト
            document.getElementById('test-homework-calendar').addEventListener('click', function() {
                const resultDiv = document.getElementById('homework-api-result');
                resultDiv.innerHTML = '<p>読み込み中...</p>';
                
                const studentId = document.getElementById('homework-student-id').value;
                const year = document.getElementById('homework-year').value;
                const month = document.getElementById('homework-month').value;
                
                const url = `/myapp/index.cgi/api/teacher/homework/calendar?student_id=${studentId}&year=${year}&month=${month}`;
                
                fetch(url)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('APIエラー: ' + response.status + ' ' + response.statusText);
                        }
                        return response.json();
                    })
                    .then(data => {
                        resultDiv.innerHTML = '<h3>カレンダーAPI結果:</h3>';
                        if (data.success) {
                            resultDiv.innerHTML += '<p>宿題件数: ' + (data.homework ? data.homework.length : 0) + '件</p>';
                            if (data.homework && data.homework.length > 0) {
                                resultDiv.innerHTML += '<pre>' + JSON.stringify(data.homework, null, 2) + '</pre>';
                            } else {
                                resultDiv.innerHTML += '<p>該当する宿題がありません</p>';
                            }
                        } else {
                            resultDiv.innerHTML += '<div class="error">エラー: ' + data.message + '</div>';
                        }
                    })
                    .catch(error => {
                        resultDiv.innerHTML = '<div class="error">エラー: ' + error.message + '</div>';
                    });
            });
            
            document.getElementById('test-homework-list').addEventListener('click', function() {
                const resultDiv = document.getElementById('homework-api-result');
                resultDiv.innerHTML = '<p>読み込み中...</p>';
                
                const studentId = document.getElementById('homework-student-id').value;
                const url = `/myapp/index.cgi/api/teacher/homework/list?student_id=${studentId}`;
                
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        resultDiv.innerHTML = '<h3>宿題リストAPI結果:</h3>';
                        if (data.success) {
                            resultDiv.innerHTML += '<p>宿題件数: ' + (data.homework ? data.homework.length : 0) + '件</p>';
                            if (data.homework && data.homework.length > 0) {
                                resultDiv.innerHTML += '<pre>' + JSON.stringify(data.homework.slice(0, 3), null, 2) + '</pre>';
                                if (data.homework.length > 3) {
                                    resultDiv.innerHTML += '<p>... 他 ' + (data.homework.length - 3) + ' 件</p>';
                                }
                            }
                        } else {
                            resultDiv.innerHTML += '<div class="error">エラー: ' + data.message + '</div>';
                        }
                    })
                    .catch(error => {
                        resultDiv.innerHTML = '<div class="error">エラー: ' + error.message + '</div>';
                    });
            });
            
            document.getElementById('test-homework-stats').addEventListener('click', function() {
                const resultDiv = document.getElementById('homework-api-result');
                resultDiv.innerHTML = '<p>読み込み中...</p>';
                
                fetch('/myapp/index.cgi/api/teacher/homework/statistics')
                    .then(response => response.json())
                    .then(data => {
                        resultDiv.innerHTML = '<h3>統計API結果:</h3>';
                        if (data.success) {
                            resultDiv.innerHTML += '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                        } else {
                            resultDiv.innerHTML += '<div class="error">エラー: ' + data.message + '</div>';
                        }
                    })
                    .catch(error => {
                        resultDiv.innerHTML = '<div class="error">エラー: ' + error.message + '</div>';
                    });
            });
            // 生徒APIテスト
            document.getElementById('test-students-api').addEventListener('click', function() {
                const resultDiv = document.getElementById('students-api-result');
                resultDiv.innerHTML = '<p>読み込み中...</p>';
                
                const grade = document.getElementById('grade-filter').value;
                const day = document.getElementById('day-filter').value;
                
                let url = '/myapp/index.cgi/api/teacher/students?';
                if (grade !== 'all') url += 'grade=' + grade + '&';
                if (day !== 'all') url += 'day=' + day;
                
                fetch(url)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('APIエラー: ' + response.status + ' ' + response.statusText);
                        }
                        return response.json();
                    })
                    .then(data => {
                        resultDiv.innerHTML = '<h3>結果:</h3>';
                        if (data.success) {
                            resultDiv.innerHTML += '<p>生徒数: ' + data.students.length + '件</p>';
                            if (data.students.length > 0) {
                                resultDiv.innerHTML += '<pre>' + JSON.stringify(data.students[0], null, 2) + '</pre>';
                                resultDiv.innerHTML += '<p>... 他 ' + (data.students.length - 1) + ' 件</p>';
                            }
                        } else {
                            resultDiv.innerHTML += '<div class="error">エラー: ' + data.message + '</div>';
                        }
                    })
                    .catch(error => {
                        resultDiv.innerHTML = '<div class="error">エラー: ' + error.message + '</div>';
                    });
            });
            
            // SQLクエリ実行
            document.getElementById('run-query').addEventListener('click', function() {
                const resultDiv = document.getElementById('query-result');
                resultDiv.innerHTML = '<p>実行中...</p>';
                
                const query = document.getElementById('query-input').value;
                const params = document.getElementById('params-input').value;
                
                const url = '/myapp/index.cgi/api/debug/test-query?query=' + 
                    encodeURIComponent(query) + '&params=' + encodeURIComponent(params);
                
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            resultDiv.innerHTML = '<div class="error">エラー: ' + data.error + '</div>';
                        } else {
                            resultDiv.innerHTML = '<h3>結果:</h3>';
                            resultDiv.innerHTML += '<p>レコード数: ' + data.row_count + '件</p>';
                            resultDiv.innerHTML += '<pre>' + JSON.stringify(data.results, null, 2) + '</pre>';
                        }
                    })
                    .catch(error => {
                        resultDiv.innerHTML = '<div class="error">エラー: ' + error.message + '</div>';
                    });
            });
            
            // 出席APIテスト
            document.getElementById('test-attendance-api').addEventListener('click', function() {
                const resultDiv = document.getElementById('attendance-api-result');
                resultDiv.innerHTML = '<p>実行中...</p>';
                
                const studentId = document.getElementById('student-id').value;
                const date = document.getElementById('attendance-date').value;
                const status = document.getElementById('attendance-status').value;
                const awardPoints = document.getElementById('award-points').checked;
                
                // 出席データを作成
                const attendanceData = [{
                    student_id: studentId,
                    status: status,
                    date: date,
                    award_points: awardPoints && status === 'present'
                }];
                
                fetch('/myapp/index.cgi/api/teacher/attendance', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ attendance_records: attendanceData })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        resultDiv.innerHTML = '<div style="color: green; padding: 10px;">' + data.message + '</div>';
                        resultDiv.innerHTML += '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    } else {
                        resultDiv.innerHTML = '<div class="error">エラー: ' + data.message + '</div>';
                    }
                })
                .catch(error => {
                    resultDiv.innerHTML = '<div class="error">エラー: ' + error.message + '</div>';
                });
            });
        </script>
    </body>
    </html>
    """
    return html

# 宿題管理関連のAPIエンドポイント
@app.route('/api/teacher/homework/assign', methods=['POST'])
def assign_homework():
    """宿題一括登録API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = None
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'JSONデータが無効です'}), 400
            
        # 一括配布用の student_ids 配列を取得（後方互換性のため student_id も対応）
        student_ids = data.get('student_ids', [])
        if not student_ids and data.get('student_id'):
            # 単一生徒IDが指定された場合は配列に変換
            student_ids = [data.get('student_id')]
        
        assigned_date = data.get('assigned_date')
        subject = data.get('subject')
        textbook = data.get('textbook')
        topic = data.get('topic')
        pages = data.get('pages')
        
        # 必須項目の検証
        if not all([student_ids, assigned_date, subject, textbook, topic]):
            return jsonify({'success': False, 'message': '必要な項目が入力されていません'}), 400
        
        # student_ids が配列でない場合のエラー処理
        if not isinstance(student_ids, list) or len(student_ids) == 0:
            return jsonify({'success': False, 'message': '生徒を選択してください'}), 400
        
        # 生徒IDsを整数に変換（文字列で送信される場合があるため）
        try:
            student_ids = [int(sid) for sid in student_ids]
        except (ValueError, TypeError) as e:
            return jsonify({'success': False, 'message': '生徒IDの形式が正しくありません'}), 400
        
        # 日付形式の検証
        try:
            from datetime import datetime
            datetime.strptime(assigned_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({'success': False, 'message': '日付形式が正しくありません'}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 生徒IDの妥当性をまとめて確認
            placeholders = ','.join(['%s'] * len(student_ids))
            cur.execute(f"""
                SELECT id FROM users 
                WHERE id IN ({placeholders}) AND role = 'student'
                AND school_type = 'elementary' AND grade_level IN (5, 6)
            """, student_ids)
            
            valid_student_ids = [row['id'] for row in cur.fetchall()]
            
            # 無効な生徒IDがないかチェック
            invalid_ids = set(student_ids) - set(valid_student_ids)
            if invalid_ids:
                return jsonify({
                    'success': False, 
                    'message': f'無効な生徒ID、または対象外の生徒が含まれています: {list(invalid_ids)}'
                }), 400
            
            # 宿題テーブルがない場合は作成
            cur.execute("""
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
                    FOREIGN KEY (student_id) REFERENCES users(id),
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            """)
            
            # 既存テーブルに created_by カラムがない場合は追加
            try:
                cur.execute("""
                    ALTER TABLE homework_assignments 
                    ADD COLUMN created_by INT NOT NULL DEFAULT 1
                """)
                cur.execute("""
                    ALTER TABLE homework_assignments 
                    ADD FOREIGN KEY (created_by) REFERENCES users(id)
                """)
            except Exception:
                # カラムが既に存在する場合はスキップ
                pass
                
            # teacher_id が存在する場合は created_by にデータを移行
            try:
                cur.execute("""
                    UPDATE homework_assignments 
                    SET created_by = teacher_id 
                    WHERE created_by = 1 AND teacher_id IS NOT NULL
                """)
            except Exception:
                # teacher_id カラムが存在しない場合はスキップ
                pass
                
            # 宿題完了テーブルがない場合は作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS homework_completions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    assignment_id INT NOT NULL,
                    student_id INT NOT NULL,
                    completed_date DATE NOT NULL,
                    points_awarded INT NOT NULL DEFAULT 10,
                    checked_by INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (assignment_id) REFERENCES homework_assignments(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id) REFERENCES users(id),
                    FOREIGN KEY (checked_by) REFERENCES users(id)
                )
            """)
                
            # 一括宿題登録処理
            teacher_id = session.get('user_id')
            inserted_count = 0
            
            for student_id in valid_student_ids:
                try:
                    # 重複チェック（同じ生徒、同じ日付、同じ内容の宿題がないか）
                    cur.execute("""
                        SELECT id FROM homework_assignments 
                        WHERE student_id = %s AND assigned_date = %s 
                        AND subject = %s AND textbook = %s AND topic = %s
                        AND created_by = %s
                    """, (student_id, assigned_date, subject, textbook, topic, teacher_id))
                    
                    if cur.fetchone():
                        # 重複する宿題がある場合はスキップ
                        log_error(f"重複宿題をスキップ: student_id={student_id}")
                        continue
                    
                    # 宿題を登録
                    cur.execute("""
                        INSERT INTO homework_assignments 
                        (student_id, created_by, assigned_date, subject, textbook, topic, pages)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (student_id, teacher_id, assigned_date, subject, textbook, topic, pages))
                    
                    inserted_count += 1
                    
                except Exception as e:
                    log_error(f"生徒ID {student_id} への宿題登録エラー: {e}")
                    continue
                
            conn.commit()
            
            if inserted_count == 0:
                return jsonify({'success': False, 'message': '宿題を登録できませんでした（重複または他のエラー）'}), 400
            elif inserted_count == len(valid_student_ids):
                return jsonify({
                    'success': True, 
                    'message': f'{inserted_count}人の生徒に宿題を一括登録しました',
                    'assigned_count': inserted_count
                })
            else:
                return jsonify({
                    'success': True, 
                    'message': f'{inserted_count}/{len(valid_student_ids)}人の生徒に宿題を登録しました（一部スキップ）',
                    'assigned_count': inserted_count
                })
                
    except Exception as e:
        if conn:
            conn.rollback()
        log_error(f"Error assigning homework: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/teacher/homework/list')
def get_homework_list():
    """宿題リスト取得API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = None
    try:
        student_id = request.args.get('student_id')
        status = request.args.get('status', 'all')  # all, completed, pending
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # パラメータの検証
        if status not in ['all', 'completed', 'pending']:
            return jsonify({'success': False, 'message': '無効なステータスです'}), 400
            
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 小学5・6年生の確認
            if student_id:
                cur.execute("""
                    SELECT id FROM users 
                    WHERE id = %s AND role = 'student' 
                    AND school_type = 'elementary' AND grade_level IN (5, 6)
                """, (student_id,))
                if not cur.fetchone():
                    return jsonify({'success': False, 'message': '対象は小学5・6年生のみです'}), 400
            
            # homework_completionsテーブルと結合して完了状態を正確に取得
            base_query = """
                SELECT h.*, u.name as student_name, u.grade_level,
                       CASE WHEN hc.id IS NOT NULL THEN 1 ELSE 0 END as completed,
                       hc.completed_date, hc.points_awarded,
                       DATE_FORMAT(h.assigned_date, '%%%%Y-%%%%m-%%%%d') as assigned_date_formatted,
                       DATE_FORMAT(hc.completed_date, '%%%%Y-%%%%m-%%%%d') as completed_date_formatted
                FROM homework_assignments h
                JOIN users u ON h.student_id = u.id
                LEFT JOIN homework_completions hc ON h.id = hc.assignment_id
                WHERE h.created_by = %s
                  AND u.school_type = 'elementary' 
                  AND u.grade_level IN (5, 6)
            """
            params = [session.get('user_id')]
            
            if student_id:
                base_query += " AND h.student_id = %s"
                params.append(student_id)
            
            if status == 'completed':
                base_query += " AND hc.id IS NOT NULL"
            elif status == 'pending':
                base_query += " AND hc.id IS NULL"
            
            if date_from:
                base_query += " AND h.assigned_date >= %s"
                params.append(date_from)
            
            if date_to:
                base_query += " AND h.assigned_date <= %s"
                params.append(date_to)
            
            base_query += " ORDER BY h.assigned_date DESC, h.id DESC"
            
            cur.execute(base_query, params)
            homework_list = cur.fetchall()
            
            return jsonify({
                'success': True, 
                'homework': homework_list,
                'total_count': len(homework_list),
                'completed_count': sum(1 for h in homework_list if h['completed']),
                'pending_count': sum(1 for h in homework_list if not h['completed'])
            })
                
    except Exception as e:
        log_error(f"Error in get_homework_list: {e}")
        return jsonify({'success': False, 'message': 'データの取得に失敗しました'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/teacher/homework/complete', methods=['POST'])
def complete_homework():
    """宿題完了処理API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.json
        assignment_id = data.get('assignment_id')
        student_id = data.get('student_id')
        points = data.get('points', 10)
        
        if not assignment_id or not student_id:
            return jsonify({'success': False, 'message': 'assignment_idとstudent_idが必要です'}), 400
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # 既に完了済みかチェック
                cur.execute("""
                    SELECT hc.id FROM homework_completions hc
                    JOIN homework_assignments ha ON hc.assignment_id = ha.id
                    WHERE ha.id = %s AND ha.created_by = %s AND hc.student_id = %s
                """, (assignment_id, session.get('user_id'), student_id))
                
                if cur.fetchone():
                    return jsonify({'success': False, 'message': 'この宿題は既に完了済みです'}), 400
                
                # 宿題の存在確認
                cur.execute("""
                    SELECT id FROM homework_assignments 
                    WHERE id = %s AND created_by = %s
                """, (assignment_id, session.get('user_id')))
                
                if not cur.fetchone():
                    return jsonify({'success': False, 'message': '宿題が見つかりません'}), 404
                
                # homework_completionsテーブルに完了記録を追加
                cur.execute("""
                    INSERT INTO homework_completions (assignment_id, student_id, completed_date, points_awarded, checked_by)
                    VALUES (%s, %s, CURDATE(), %s, %s)
                """, (assignment_id, student_id, points, session.get('user_id')))
                
                # ポイントを付与
                if student_id and points > 0:
                    cur.execute("""
                        INSERT INTO point_history (user_id, points, event_type, comment, created_by)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (student_id, points, 'homework', f"宿題完了ボーナス", session.get('user_id')))
                
                conn.commit()
                
                return jsonify({'success': True, 'message': '宿題を完了としてマークし、ポイントを付与しました'})
                
        except Exception as e:
            conn.rollback()
            log_error(f"Error completing homework: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        log_error(f"Error in complete_homework: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/teacher/homework/undo-complete/<int:assignment_id>', methods=['DELETE'])
def undo_homework_completion(assignment_id):
    """宿題完了取消API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # 宿題の完了状態を確認
                cur.execute("""
                    SELECT hc.id as completion_id, hc.points_awarded, ha.student_id 
                    FROM homework_assignments ha
                    LEFT JOIN homework_completions hc ON ha.id = hc.assignment_id
                    WHERE ha.id = %s AND ha.created_by = %s
                """, (assignment_id, session.get('user_id')))
                
                result = cur.fetchone()
                if not result:
                    return jsonify({'success': False, 'message': '宿題が見つかりません'}), 404
                
                if not result['completion_id']:
                    return jsonify({'success': False, 'message': 'この宿題は完了状態ではありません'}), 400
                
                # homework_completionsテーブルから削除
                cur.execute("DELETE FROM homework_completions WHERE id = %s", (result['completion_id'],))
                
                # 付与されたポイントを取り消し（is_active = 0で履歴に表示されないようにする）
                if result['points_awarded'] and result['student_id']:
                    cur.execute("""
                        INSERT INTO point_history (user_id, points, event_type, comment, created_by, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (result['student_id'], -result['points_awarded'], 'homework', f"宿題完了取消", session.get('user_id'), 0))
                
                conn.commit()
                
                return jsonify({'success': True, 'message': '宿題の完了状態を取り消し、ポイントを調整しました'})
                
        except Exception as e:
            conn.rollback()
            log_error(f"Error undoing homework completion: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        log_error(f"Error in undo_homework_completion: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/teacher/homework/delete/<int:assignment_id>', methods=['DELETE'])
def delete_homework_assignment(assignment_id):
    """宿題削除API（完了取り消しも含む）"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 宿題の存在確認と所有者確認
            cur.execute("""
                SELECT ha.id, ha.student_id, ha.subject, ha.topic,
                       hc.id as completion_id, hc.points_awarded,
                       u.name as student_name
                FROM homework_assignments ha
                LEFT JOIN homework_completions hc ON ha.id = hc.assignment_id
                LEFT JOIN users u ON ha.student_id = u.id
                WHERE ha.id = %s AND ha.created_by = %s
            """, (assignment_id, session.get('user_id')))
            
            homework = cur.fetchone()
            if not homework:
                return jsonify({'success': False, 'message': '宿題が見つかりません'}), 404
            
            # 完了状態の場合は先にポイントを取り消し（is_active = 0で履歴に表示されないようにする）
            if homework['completion_id'] and homework['points_awarded'] and homework['student_id']:
                cur.execute("""
                    INSERT INTO point_history (user_id, points, event_type, comment, created_by, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (homework['student_id'], -homework['points_awarded'], 'homework', 
                      f"宿題削除によるポイント取り消し: {homework['subject']} - {homework['topic']}", 
                      session.get('user_id'), 0))
                
                log_error(f"ポイント取り消し: 生徒={homework['student_name']}, ポイント=-{homework['points_awarded']}")
            
            # 完了記録を削除
            if homework['completion_id']:
                cur.execute("DELETE FROM homework_completions WHERE id = %s", (homework['completion_id'],))
                log_error(f"完了記録削除: completion_id={homework['completion_id']}")
            
            # 宿題自体を削除
            cur.execute("DELETE FROM homework_assignments WHERE id = %s", (assignment_id,))
            
            conn.commit()
            
            log_error(f"宿題削除完了: ID={assignment_id}, 生徒={homework['student_name']}, 科目={homework['subject']}")
            
            return jsonify({
                'success': True, 
                'message': f"{homework['student_name']}の宿題を削除しました"
            })
                
    except Exception as e:
        if conn:
            conn.rollback()
        log_error(f"Error deleting homework: {e}")
        return jsonify({'success': False, 'message': f'削除エラー: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/teacher/homework/calendar')
def get_homework_calendar():
    """宿題カレンダー表示用API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        log_error("❌ 宿題カレンダーAPI: 認証エラー")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = None
    try:
        student_id = request.args.get('student_id')
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        log_error(f"📊 宿題カレンダーAPI呼び出し: student_id={student_id}, year={year}, month={month}, teacher_id={session.get('user_id')}")
        
        # パラメータ検証
        if not student_id:
            return jsonify({'success': False, 'message': 'student_idが必要です'}), 400
        
        # 年月の妥当性チェック
        if not year or not month or year < 2020 or year > 2030 or month < 1 or month > 12:
            return jsonify({'success': False, 'message': '有効な年月を指定してください'}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 小学5・6年生の生徒かどうかを確認
            cur.execute("""
                SELECT grade_level, school_type, name FROM users 
                WHERE id = %s AND role = 'student'
            """, (student_id,))
            student_info = cur.fetchone()
            
            if not student_info:
                log_error(f"❌ 生徒が見つかりません: student_id={student_id}")
                return jsonify({'success': False, 'message': '生徒が見つかりません'}), 404
            
            if student_info['school_type'] != 'elementary' or student_info['grade_level'] not in [5, 6]:
                log_error(f"❌ 対象外の生徒: grade_level={student_info['grade_level']}, school_type={student_info['school_type']}")
                return jsonify({'success': False, 'message': '対象は小学5・6年生のみです'}), 400
            
            # 月の開始日と終了日を計算
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year+1}-01-01"
            else:
                end_date = f"{year}-{month+1:02d}-01"
            
            log_error(f"📊 宿題検索範囲: {start_date} から {end_date} (月: {month})")
            
            # homework_completionsテーブルと結合して正確な完了状態を取得
            cur.execute("""
                    SELECT h.id, h.student_id, h.assigned_date, h.subject, h.textbook, h.topic, h.pages,
                           CASE WHEN hc.id IS NOT NULL THEN 1 ELSE 0 END as completed,
                           hc.completed_date, hc.points_awarded, h.created_by
                    FROM homework_assignments h
                    LEFT JOIN homework_completions hc ON h.id = hc.assignment_id
                    WHERE h.student_id = %s AND h.created_by = %s
                    AND h.assigned_date >= %s AND h.assigned_date < %s
                    ORDER BY h.assigned_date
                """, (student_id, session.get('user_id'), start_date, end_date))
                
            homework_data = cur.fetchall()
            log_error(f"📊 宿題データ取得結果: {len(homework_data)}件")
            
            # 日付フォーマットを確認・統一し、日付別に整理
            homework_by_date = {}
            for hw in homework_data:
                if 'assigned_date' in hw and hw['assigned_date']:
                    # assigned_dateがdatetimeオブジェクトの場合は文字列に変換
                    if hasattr(hw['assigned_date'], 'strftime'):
                        assigned_date = hw['assigned_date'].strftime('%Y-%m-%d')
                    else:
                        assigned_date = str(hw['assigned_date'])
                    
                    # 日付別に宿題を整理
                    if assigned_date not in homework_by_date:
                        homework_by_date[assigned_date] = []
                    
                    homework_by_date[assigned_date].append({
                        'id': hw['id'],
                        'student_id': hw['student_id'],
                        'subject': hw['subject'],
                        'textbook': hw['textbook'],
                        'topic': hw['topic'],
                        'pages': hw['pages'],
                        'completed': bool(hw['completed']),
                        'completed_date': hw['completed_date'],
                        'points_awarded': hw['points_awarded']
                    })
                    
                    log_error(f"📝 宿題: ID={hw['id']}, 日付={assigned_date}, 科目={hw['subject']}, 完了={hw['completed']}")
            
            log_error(f"📊 整理済み宿題データ: {len(homework_by_date)}日分")
            return jsonify({'success': True, 'homework': homework_by_date})
            
    except Exception as e:
        log_error(f"❌ Error getting homework calendar: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/teacher/homework/templates')
def get_homework_templates():
    """宿題テンプレート取得API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # よく使用される宿題をテンプレートとして取得
                cur.execute("""
                    SELECT subject, textbook, topic, pages, COUNT(*) as usage_count
                    FROM homework_assignments 
                    WHERE created_by = %s
                    GROUP BY subject, textbook, topic, pages
                    ORDER BY usage_count DESC, subject, textbook, topic
                    LIMIT 10
                """, (session.get('user_id'),))
                
                templates = []
                for i, row in enumerate(cur.fetchall()):
                    templates.append({
                        'id': i + 1,
                        'subject': row['subject'],
                        'textbook': row['textbook'],
                        'topic': row['topic'],
                        'pages': row['pages'],
                        'usage_count': row['usage_count']
                    })
                
                # デフォルトテンプレートも追加（データがない場合）
                if not templates:
                    templates = [
                        {
                            'id': 1,
                            'subject': '算数',
                            'textbook': '教科書',
                            'topic': '計算練習',
                            'pages': 'p.20-25'
                        },
                        {
                            'id': 2,
                            'subject': '国語',
                            'textbook': '漢字ドリル',
                            'topic': '漢字練習',
                            'pages': 'p.10-15'
                        }
                    ]
                
                return jsonify({'success': True, 'templates': templates})
                
        except Exception as e:
            log_error(f"Error getting homework templates: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        log_error(f"Error in get_homework_templates: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/teacher/homework/statistics')
def get_homework_statistics():
    """宿題統計情報取得API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = None
    try:
        student_id = request.args.get('student_id')
        period = request.args.get('period', 'month')  # week, month, year
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 期間の設定
            if period == 'week':
                date_condition = "h.assigned_date >= DATE_SUB(CURDATE(), INTERVAL 1 WEEK)"
            elif period == 'month':
                date_condition = "h.assigned_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)"
            elif period == 'year':
                date_condition = "h.assigned_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)"
            else:
                date_condition = "h.assigned_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)"
            
            # 基本統計の取得
            base_query = f"""
                SELECT 
                    COUNT(h.id) as total_assignments,
                    COUNT(hc.id) as completed_assignments,
                    ROUND(COUNT(hc.id) * 100.0 / COUNT(h.id), 1) as completion_rate,
                    COALESCE(SUM(hc.points_awarded), 0) as total_points
                FROM homework_assignments h
                JOIN users u ON h.student_id = u.id
                LEFT JOIN homework_completions hc ON h.id = hc.assignment_id
                WHERE h.created_by = %s
                  AND u.school_type = 'elementary' 
                  AND u.grade_level IN (5, 6)
                  AND {date_condition}
            """
            
            params = [session.get('user_id')]
            
            if student_id:
                base_query += " AND h.student_id = %s"
                params.append(student_id)
                
            cur.execute(base_query, params)
            basic_stats = cur.fetchone()
            
            # 教科別統計
            subject_query = f"""
                SELECT 
                    h.subject,
                    COUNT(h.id) as total,
                    COUNT(hc.id) as completed,
                    ROUND(COUNT(hc.id) * 100.0 / COUNT(h.id), 1) as completion_rate
                FROM homework_assignments h
                JOIN users u ON h.student_id = u.id
                LEFT JOIN homework_completions hc ON h.id = hc.assignment_id
                WHERE h.created_by = %s
                  AND u.school_type = 'elementary' 
                  AND u.grade_level IN (5, 6)
                  AND {date_condition}
            """
            
            if student_id:
                subject_query += " AND h.student_id = %s"
                
            subject_query += " GROUP BY h.subject ORDER BY total DESC"
            
            cur.execute(subject_query, params)
            subject_stats = cur.fetchall()
            
            # 生徒別統計（student_idが指定されていない場合）
            student_stats = []
            if not student_id:
                student_query = f"""
                    SELECT 
                        u.id,
                        u.name,
                        u.grade_level,
                        COUNT(h.id) as total,
                        COUNT(hc.id) as completed,
                        ROUND(COUNT(hc.id) * 100.0 / COUNT(h.id), 1) as completion_rate,
                        COALESCE(SUM(hc.points_awarded), 0) as total_points
                    FROM users u
                    LEFT JOIN homework_assignments h ON u.id = h.student_id AND h.created_by = %s AND {date_condition}
                    LEFT JOIN homework_completions hc ON h.id = hc.assignment_id
                    WHERE u.role = 'student'
                      AND u.school_type = 'elementary' 
                      AND u.grade_level IN (5, 6)
                    GROUP BY u.id, u.name, u.grade_level
                    ORDER BY completion_rate DESC, total DESC
                """
                
                cur.execute(student_query, [session.get('user_id')])
                student_stats = cur.fetchall()
            
            return jsonify({
                'success': True,
                'period': period,
                'basic_stats': basic_stats or {
                    'total_assignments': 0,
                    'completed_assignments': 0,
                    'completion_rate': 0,
                    'total_points': 0
                },
                'subject_stats': subject_stats,
                'student_stats': student_stats
            })
            
    except Exception as e:
        log_error(f"Error getting homework statistics: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/teacher/homework/history')
def get_homework_history():
    """宿題履歴取得API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        student_id = request.args.get('student_id')
        period = request.args.get('period', 'month')  # week, month, year
        
        conn = get_db_connection()
        
        try:
            with conn.cursor() as cur:
                # 期間に基づいて日付範囲を計算
                from datetime import datetime, timedelta
                today = datetime.now().date()
                
                if period == 'week':
                    start_date = today - timedelta(days=7)
                elif period == 'month':
                    start_date = today - timedelta(days=30)
                elif period == 'year':
                    start_date = today - timedelta(days=365)
                else:
                    start_date = today - timedelta(days=30)  # デフォルトは月
                
                # 基本クエリ
                query = """
                    SELECT h.id, h.student_id, h.assigned_date, h.subject, h.textbook, h.topic, h.pages,
                           u.name as student_name,
                           CASE WHEN hc.id IS NOT NULL THEN 1 ELSE 0 END as completed,
                           hc.completed_date, hc.points_awarded
                    FROM homework_assignments h
                    LEFT JOIN homework_completions hc ON h.id = hc.assignment_id
                    LEFT JOIN users u ON h.student_id = u.id
                    WHERE h.created_by = %s AND h.assigned_date >= %s
                """
                
                params = [session.get('user_id'), start_date]
                
                # 生徒IDでフィルタリング
                if student_id:
                    query += " AND h.student_id = %s"
                    params.append(int(student_id))
                
                query += " ORDER BY h.assigned_date DESC, u.name"
                
                cur.execute(query, params)
                history_data = cur.fetchall()
                
                # データを整理
                history = []
                for row in history_data:
                    history.append({
                        'id': row['id'],
                        'student_id': row['student_id'],
                        'student_name': row['student_name'],
                        'assigned_date': row['assigned_date'].strftime('%Y-%m-%d') if row['assigned_date'] else None,
                        'subject': row['subject'],
                        'textbook': row['textbook'],
                        'topic': row['topic'],
                        'pages': row['pages'],
                        'completed': bool(row['completed']),
                        'completed_date': row['completed_date'].strftime('%Y-%m-%d') if row['completed_date'] else None,
                        'points_awarded': row['points_awarded']
                    })
                
                # 統計情報も計算
                total_assigned = len(history)
                total_completed = sum(1 for h in history if h['completed'])
                completion_rate = (total_completed / total_assigned * 100) if total_assigned > 0 else 0
                
                return jsonify({
                    'success': True, 
                    'history': history,
                    'statistics': {
                        'total_assigned': total_assigned,
                        'total_completed': total_completed,
                        'completion_rate': round(completion_rate, 1),
                        'period': period
                    }
                })
                
        except Exception as e:
            log_error(f"Error getting homework history: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        log_error(f"Error in get_homework_history: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/teacher/homework/textbooks')
def get_homework_textbooks():
    """教科書一覧取得API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        textbooks = ['教科書', '計算ドリル', '漢字ドリル', 'ワークブック', 'プリント']
        return jsonify({'success': True, 'textbooks': textbooks})
        
    except Exception as e:
        log_error(f"Error in get_homework_textbooks: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/teacher/homework/topics')
def get_homework_topics():
    """宿題トピック一覧取得API"""
    if not session.get('user_id') or session.get('role') != 'teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        topics = ['計算練習', '文章問題', '漢字練習', '読解問題', '作文', '図形問題']
        return jsonify({'success': True, 'topics': topics})
        
    except Exception as e:
        log_error(f"Error in get_homework_topics: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/student/homework/calendar')
def get_student_homework_calendar():
    """学生向け宿題カレンダー表示用API"""
    # リクエスト情報をログ出力
    log_error(f"🔍 API Request Path: {request.path}")
    log_error(f"🔍 API Request URL: {request.url}")
    log_error(f"🔍 API Request Args: {dict(request.args)}")
    log_error(f"🔍 Session User ID: {session.get('user_id')}")
    log_error(f"🔍 Session Role: {session.get('role')}")
    
    # 講師が生徒として閲覧している場合の認証を考慮
    user_id = session.get('user_id')
    user_role = session.get('role')
    teacher_view = request.args.get('teacher_view') == 'true'
    target_student_id = request.args.get('id', type=int)  # URL参数からstudent_idを取得
    
    # 認証チェック：学生本人またはteacher_viewで閲覧中の講師
    if not user_id:
        log_error("❌ 学生宿題カレンダーAPI: ユーザーIDなし")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if user_role == 'student':
        # 学生本人の場合
        pass
    elif user_role == 'teacher' and teacher_view and target_student_id:
        # 講師が生徒として閲覧している場合
        log_error(f"🔍 講師が生徒閲覧モード: teacher_id={user_id}, target_student_id={target_student_id}")
    else:
        log_error(f"❌ 学生宿題カレンダーAPI: 認証エラー - role={user_role}, teacher_view={teacher_view}")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = None
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        # student_idの決定：講師の場合はtarget_student_id、学生の場合は自分のID
        if user_role == 'teacher' and teacher_view and target_student_id:
            student_id = target_student_id
        else:
            student_id = user_id
        
        log_error(f"📊 学生宿題カレンダーAPI呼び出し: student_id={student_id}, year={year}, month={month}")
        
        # パラメータ検証
        if not year or not month or year < 2020 or year > 2030 or month < 1 or month > 12:
            return jsonify({'success': False, 'message': '有効な年月を指定してください'}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 小学5・6年生の生徒かどうかを確認
            cur.execute("""
                SELECT grade_level, school_type, name FROM users 
                WHERE id = %s AND role = 'student'
            """, (student_id,))
            student_info = cur.fetchone()
            
            log_error(f"👤 学生情報: {student_info}")
            
            if not student_info:
                log_error(f"❌ 学生情報が見つかりません: student_id={student_id}")
                return jsonify({'success': False, 'message': '学生情報が見つかりません'}), 404
            
            if student_info['school_type'] != 'elementary' or student_info['grade_level'] not in [5, 6]:
                log_error(f"❌ 対象外の学生: grade_level={student_info['grade_level']}, school_type={student_info['school_type']}")
                return jsonify({'success': False, 'message': 'このサービスは小学5・6年生向けです'}), 403
            
            # 月の開始日と終了日を計算
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year+1}-01-01"
            else:
                end_date = f"{year}-{month+1:02d}-01"
            
            log_error(f"📅 検索期間: {start_date} から {end_date}")
            
            # homework_completionsテーブルと結合して正確な完了状態を取得
            cur.execute("""
                SELECT h.id, h.assigned_date, h.subject, h.textbook, h.topic, h.pages,
                       CASE WHEN hc.id IS NOT NULL THEN 1 ELSE 0 END as completed,
                       hc.completed_date, hc.points_awarded,
                       DATE_FORMAT(h.assigned_date, '%%Y年%%m月%%d日') as assigned_date_formatted,
                       DATE_FORMAT(hc.completed_date, '%%Y年%%m月%%d日') as completed_date_formatted
                FROM homework_assignments h
                LEFT JOIN homework_completions hc ON h.id = hc.assignment_id
                WHERE h.student_id = %s
                  AND h.assigned_date >= %s AND h.assigned_date < %s
                ORDER BY h.assigned_date
            """, (student_id, start_date, end_date))
            
            homework_data = cur.fetchall()
            log_error(f"📚 宿題データ取得結果: {len(homework_data)}件")
            
            # 日付フォーマットを統一
            for hw in homework_data:
                if 'assigned_date' in hw and hw['assigned_date']:
                    if hasattr(hw['assigned_date'], 'strftime'):
                        hw['assigned_date'] = hw['assigned_date'].strftime('%Y-%m-%d')
                log_error(f"📝 宿題: ID={hw['id']}, 日付={hw['assigned_date']}, 科目={hw['subject']}, 完了={hw['completed']}")
            
            return jsonify({'success': True, 'homework': homework_data})
            
    except Exception as e:
        log_error(f"❌ Error getting student homework calendar: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/student/homework/list')
def get_student_homework_list():
    """学生向け宿題リスト取得API"""
    # リクエスト情報をログ出力
    log_error(f"🔍 宿題リストAPI Request Path: {request.path}")
    log_error(f"🔍 宿題リストAPI Request URL: {request.url}")
    log_error(f"🔍 宿題リストAPI Request Args: {dict(request.args)}")
    log_error(f"🔍 Session User ID: {session.get('user_id')}")
    log_error(f"🔍 Session Role: {session.get('role')}")
    
    # 講師が生徒として閲覧している場合の認証を考慮
    user_id = session.get('user_id')
    user_role = session.get('role')
    teacher_view = request.args.get('teacher_view') == 'true'
    target_student_id = request.args.get('id', type=int)  # URL参数からstudent_idを取得
    
    # 認証チェック：学生本人またはteacher_viewで閲覧中の講師
    if not user_id:
        log_error("❌ 学生宿題リストAPI: ユーザーIDなし")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if user_role == 'student':
        # 学生本人の場合
        pass
    elif user_role == 'teacher' and teacher_view and target_student_id:
        # 講師が生徒として閲覧している場合
        log_error(f"🔍 講師が生徒リスト閲覧モード: teacher_id={user_id}, target_student_id={target_student_id}")
    else:
        log_error(f"❌ 学生宿題リストAPI: 認証エラー - role={user_role}, teacher_view={teacher_view}")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = None
    try:
        status = request.args.get('status', 'all')  # all, completed, pending
        limit = request.args.get('limit', 20, type=int)
        
        # student_idの決定：講師の場合はtarget_student_id、学生の場合は自分のID
        if user_role == 'teacher' and teacher_view and target_student_id:
            student_id = target_student_id
        else:
            student_id = user_id
        
        # パラメータの検証
        if status not in ['all', 'completed', 'pending']:
            return jsonify({'success': False, 'message': '無効なステータスです'}), 400
            
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 小学5・6年生の確認
            cur.execute("""
                SELECT grade_level, school_type FROM users 
                WHERE id = %s AND role = 'student'
            """, (student_id,))
            student_info = cur.fetchone()
            
            if not student_info:
                return jsonify({'success': False, 'message': '生徒情報が見つかりません'}), 404
                
            if student_info['school_type'] != 'elementary' or student_info['grade_level'] not in [5, 6]:
                return jsonify({'success': False, 'message': 'このサービスは小学5・6年生向けです'}), 403
            
            # homework_completionsテーブルと結合して完了状態を正確に取得
            base_query = """
                SELECT h.*, 
                       CASE WHEN hc.id IS NOT NULL THEN 1 ELSE 0 END as completed,
                       hc.completed_date, hc.points_awarded,
                       DATE_FORMAT(h.assigned_date, '%%Y年%%m月%%d日') as assigned_date_formatted,
                       DATE_FORMAT(hc.completed_date, '%%Y年%%m月%%d日') as completed_date_formatted
                FROM homework_assignments h
                LEFT JOIN homework_completions hc ON h.id = hc.assignment_id
                WHERE h.student_id = %s
            """
            params = [student_id]
            
            if status == 'completed':
                base_query += " AND hc.id IS NOT NULL"
            elif status == 'pending':
                base_query += " AND hc.id IS NULL"
            
            base_query += " ORDER BY h.assigned_date DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(base_query, params)
            homework_list = cur.fetchall()
            
            return jsonify({
                'success': True, 
                'homework': homework_list,
                'total_count': len(homework_list),
                'completed_count': sum(1 for h in homework_list if h['completed']),
                'pending_count': sum(1 for h in homework_list if not h['completed'])
            })
                
    except Exception as e:
        log_error(f"Error in get_student_homework_list: {e}")
        return jsonify({'success': False, 'message': 'データの取得に失敗しました'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/student/homework/submit', methods=['POST'])
def submit_student_homework():
    """学生向け宿題提出API"""
    # リクエスト情報をログ出力
    log_error(f"🔍 宿題提出API Request Path: {request.path}")
    log_error(f"🔍 宿題提出API Request URL: {request.url}")
    log_error(f"🔍 宿題提出API Request Method: {request.method}")
    log_error(f"🔍 Session User ID: {session.get('user_id')}")
    log_error(f"🔍 Session Role: {session.get('role')}")
    
    # 講師が生徒として閲覧している場合の認証を考慮
    user_id = session.get('user_id')
    user_role = session.get('role')
    teacher_view = request.args.get('teacher_view') == 'true'
    target_student_id = request.args.get('id', type=int)  # URL参数からstudent_idを取得
    
    # 認証チェック：学生本人またはteacher_viewで閲覧中の講師
    if not user_id:
        log_error("❌ 学生宿題提出API: ユーザーIDなし")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if user_role == 'student':
        # 学生本人の場合
        pass
    elif user_role == 'teacher' and teacher_view and target_student_id:
        # 講師が生徒として閲覧している場合
        log_error(f"🔍 講師が生徒提出閲覧モード: teacher_id={user_id}, target_student_id={target_student_id}")
    else:
        log_error(f"❌ 学生宿題提出API: 認証エラー - role={user_role}, teacher_view={teacher_view}")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.json
        log_error(f"📤 宿題提出データ: {data}")
        
        assignment_id = data.get('assignment_id')
        comment = data.get('comment', '')
        
        # student_idの決定：講師の場合はtarget_student_id、学生の場合は自分のID
        if user_role == 'teacher' and teacher_view and target_student_id:
            student_id = target_student_id
        else:
            student_id = user_id
        
        log_error(f"📚 宿題提出: assignment_id={assignment_id}, student_id={student_id}")
        
        if not assignment_id:
            log_error("❌ assignment_idが不足")
            return jsonify({'success': False, 'message': 'assignment_idが必要です'}), 400
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # 宿題の存在確認と権限チェック
                cur.execute("""
                    SELECT id FROM homework_assignments 
                    WHERE id = %s AND student_id = %s
                """, (assignment_id, student_id))
                
                if not cur.fetchone():
                    return jsonify({'success': False, 'message': '宿題が見つかりません'}), 404
                
                # 既に提出済みかチェック
                cur.execute("""
                    SELECT id FROM homework_completions
                    WHERE assignment_id = %s
                """, (assignment_id,))
                
                if cur.fetchone():
                    return jsonify({'success': False, 'message': 'この宿題は既に提出済みです'}), 400
                
                # homework_completionsテーブルに提出記録を追加
                cur.execute("""
                    INSERT INTO homework_completions (assignment_id, student_id, completed_date, points_awarded)
                    VALUES (%s, %s, CURDATE(), 10)
                """, (assignment_id, student_id))
                
                # ポイントを付与
                cur.execute("""
                    INSERT INTO points_history (user_id, points, description, created_at)
                    VALUES (%s, %s, %s, NOW())
                """, (student_id, 10, "宿題提出"))
                
                conn.commit()
                
                return jsonify({'success': True, 'message': '宿題を提出しました！10ポイントを獲得しました。'})
                
        except Exception as e:
            conn.rollback()
            log_error(f"Error submitting homework: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
            
    except Exception as e:
        log_error(f"Error in submit_student_homework: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500



# Static file handler for CGI mode
@app.route('/api/handwriting-recognition', methods=['POST'])
def handwriting_recognition():
    """手書き文字認識API（Google Cloud Vision API使用）"""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.json
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': '画像データがありません'}), 400
        
        # Base64デコード
        import base64
        import io
        from google.cloud import vision
        
        # データURLからBase64部分を抽出
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Vision APIクライアントの初期化
        try:
            api_key = app.config.get('GOOGLE_CLOUD_VISION_API_KEY', os.getenv('GOOGLE_CLOUD_VISION_API_KEY'))
            
            # APIキーを使用した認証
            import requests
            vision_api_url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
            
            # リクエストボディの作成
            request_body = {
                "requests": [{
                    "image": {
                        "content": image_data
                    },
                    "features": [{
                        "type": "TEXT_DETECTION",
                        "maxResults": 1
                    }]
                }]
            }
            
            # APIリクエスト
            response = requests.post(vision_api_url, json=request_body)
            result = response.json()
            
            if 'error' in result:
                log_error(f"Vision API error: {result['error']}")
                return jsonify({'success': False, 'message': 'OCRエラーが発生しました'}), 500
            
            # テキスト抽出
            if result['responses'] and result['responses'][0].get('textAnnotations'):
                detected_text = result['responses'][0]['textAnnotations'][0]['description']
                
                # 改行をスペースに変換し、余分な空白を削除
                detected_text = ' '.join(detected_text.split())
                
                # 単語ごとに分割
                words = detected_text.split()
                
                # 各単語の信頼度（デモ用にランダム値）
                import random
                word_results = []
                for word in words:
                    confidence = random.randint(85, 99)
                    word_results.append({
                        'text': word,
                        'confidence': confidence
                    })
                
                return jsonify({
                    'success': True,
                    'text': detected_text,
                    'words': word_results
                })
            else:
                return jsonify({
                    'success': True,
                    'text': '',
                    'words': [],
                    'message': 'テキストが検出されませんでした'
                })
                
        except Exception as e:
            log_error(f"Vision API error: {e}")
            return jsonify({'success': False, 'message': f'OCRエラー: {str(e)}'}), 500
            
    except Exception as e:
        log_error(f"Handwriting recognition error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/english-grammar-practice')
def english_grammar_practice():
    """英語文法練習ページ"""
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    # CSRFトークンの生成
    import secrets
    csrf_token = secrets.token_hex(16)
    session['csrf_token'] = csrf_token
    
    return render_template('english_grammar_practice.html', csrf_token=csrf_token)

@app.route('/static/<path:filename>')
@app.route('/myapp/index.cgi/static/<path:filename>')
def serve_static(filename):
    """Serve static files in CGI mode"""
    import os
    from flask import send_from_directory, make_response
    static_dir = os.path.join(app.root_path, 'static')
    
    # Security check - prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        return "Invalid file path", 400
    
    # Check if file exists
    file_path = os.path.join(static_dir, filename)
    if not os.path.exists(file_path):
        # Log the attempted path for debugging
        log_error(f"Static file not found: {file_path} (requested: {filename})")
        return "File not found", 404
    
    # Serve file with appropriate content type
    response = make_response(send_from_directory(static_dir, filename))
    
    # Set content type based on file extension
    if filename.endswith('.js'):
        response.headers['Content-Type'] = 'application/javascript'
    elif filename.endswith('.css'):
        response.headers['Content-Type'] = 'text/css'
    
    return response

if __name__ == '__main__':
    # アプリケーション起動時の初期化処理
    try:
        conn = get_db_connection()
        try:
            # 必要なテーブルの確認・作成
            create_subjects_table(conn)
            create_internal_points_table(conn)
            create_class_schedule_master_table(conn)
            add_attendance_day_column_to_users(conn)
            ensure_elementary_grades_table(conn)
            ensure_monthly_test_comments_table(conn)
            ensure_eiken_words_table(conn)
            
            # 出席記録テーブルの確認・修正
            from attendance_utils import ensure_attendance_records_table
            ensure_attendance_records_table(conn)
            
            # 外部サービス認証情報テーブルの確認
            if 'ensure_external_service_credentials_table' in globals():
                ensure_external_service_credentials_table(conn)
            
            # 成績・内申向上通知テーブルの確認
            if 'ensure_notification_tables' in globals():
                ensure_notification_tables(conn)
            
            app.logger.info("データベーステーブルの初期化が完了しました")
        except Exception as e:
            app.logger.error(f"データベース初期化中にエラーが発生しました: {e}")
        finally:
            conn.close()
    except Exception as e:
        app.logger.error(f"データベース接続エラー: {e}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)