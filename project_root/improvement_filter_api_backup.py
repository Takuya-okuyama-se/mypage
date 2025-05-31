#!/usr/local/bin/python
# -*- coding: utf-8 -*-

# improvement_filter_api.py
# 成績向上フィルタと成績向上ポイント付与APIを提供するモジュール

import pymysql
from pymysql.cursors import DictCursor
import json
import sys
import os
from datetime import datetime
from urllib.parse import parse_qs

# ロギング用セットアップ
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/improvement_filter.log',
    filemode='a'
)

# ライブラリのインポート
sys.path.append('/path/to/your/modules')
try:
    from points_utils import teacher_award_points
except ImportError:
    # points_utils モジュールが見つからない場合のスタブ実装
    def teacher_award_points(conn, teacher_id, student_id, event_type, points, comment=None):
        # ダミー実装
        logging.warning("points_utils モジュールがないためダミー実装を使用")
        
        # 直接 point_history テーブルに挿入する
        try:
            with conn.cursor() as cur:                cur.execute("""
                    INSERT INTO point_history
                    (user_id, points, event_type, comment, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (student_id, points, event_type, comment, teacher_id))
                conn.commit()
                return True, "ポイントを付与しました（ID: {}）".format(cur.lastrowid)
        except Exception as e:
            conn.rollback()
            return False, str(e)

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

# データベース接続関数
def get_db_connection():
    try:
        return pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            port=Config.MYSQL_PORT,
            charset='utf8mb4',
            cursorclass=DictCursor
        )
    except Exception as e:
        logging.error("Database connection error: %s", str(e))
        raise

# 小学生の成績向上データを取得するAPI
def get_elementary_improved_students(filters):
    """
    小学生の成績向上データを取得するAPI
    
    引数:
    - filters: フィルター辞書
        - start_month: 開始月
        - end_month: 終了月
        - subject: 科目ID（all の場合はすべての科目）
        - min_improvement: 最小向上点数
    """
    
    conn = get_db_connection()
    
    try:
        start_month = int(filters.get('start_month', 1))
        end_month = int(filters.get('end_month', 12))
        subject_id = filters.get('subject', 'all')
        min_improvement = int(filters.get('min_improvement', 0))
        
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
                params.append(subject_id)
                
            # 向上幅でソート
            query += " ORDER BY (s1.score - s2.score) DESC"
            
            # クエリを実行
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
                    'current_month': row['current_month'],                    'previous_score': row['previous_score'],
                    'current_score': row['current_score'],
                    'improvement': row['improvement']
                }
                
                students.append(student)
                
            return {'success': True, 'students': students}
    
    except Exception as e:
        # エラーメッセージを安全に処理
        error_msg = str(e).replace('%', '%%')  # % 文字をエスケープ
        logging.error("Error in get_elementary_improved_students: %s", str(e))
        return {'success': False, 'message': str(e)}
        
    finally:
        conn.close()

# 中学生の内申点向上データを取得するAPI
def get_middle_improved_students(filters):
    """
    中学生の内申点向上データを取得するAPI
    
    引数:
    - filters: フィルター辞書
        - start_year: 開始年
        - start_term: 開始学期
        - end_year: 終了年
        - end_term: 終了学期
        - subject: 科目ID（all の場合はすべての科目）
    """
    
    conn = get_db_connection()
    
    try:
        start_year = int(filters.get('start_year', 1))
        start_term = int(filters.get('start_term', 1))
        end_year = int(filters.get('end_year', 3))
        end_term = int(filters.get('end_term', 3))
        subject_id = filters.get('subject', 'all')
        
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
                params.append(subject_id)
                
            # 向上幅でソート
            query += " ORDER BY (p1.point - p2.point) DESC"
            
            # クエリを実行
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
                    'current_year': row['current_year'],                    'current_term': row['current_term'],
                    'previous_point': row['previous_point'],
                    'current_point': row['current_point'],
                    'improvement': row['improvement']
                }
                
                students.append(student)
                
            return {'success': True, 'students': students}
    
    except Exception as e:
        # エラーメッセージを安全に処理
        logging.error("Error in get_middle_improved_students: %s", str(e))
        return {'success': False, 'message': str(e)}
        
    finally:
        conn.close()

# 成績向上ポイント付与API
def award_improvement_points(data, teacher_id):
    """
    成績向上ポイントを付与するAPI
    
    引数:
    - data: POST データ
        - student_id: 生徒ID
        - points: 付与ポイント
        - event_type: イベントタイプ
        - comment: コメント
        - subject_id: 科目ID
    - teacher_id: 教師ID
    """
    
    conn = get_db_connection()
    
    try:
        student_id = int(data.get('student_id'))
        points = int(data.get('points'))
        event_type = data.get('event_type')
        comment = data.get('comment')
        subject_id = data.get('subject_id')
        
        # ポイント付与実行
        success, message = teacher_award_points(
            conn,
            teacher_id,
            student_id,
            event_type,
            points,
            comment
        )
        
        return {
            'success': success,
            'message': message,
            'points': points,            'student_id': student_id
        }
    
    except Exception as e:
        logging.error("Error in award_improvement_points: %s", str(e))
        return {'success': False, 'message': str(e)}
        
    finally:
        conn.close()

# メインルーティング処理
def application(environ, start_response):
    method = environ.get('REQUEST_METHOD')
    path = environ.get('PATH_INFO', '').lstrip('/')
    
    # APIエンドポイントを処理
    if path == 'api/teacher/improved-students':
        # GETパラメータを取得
        query_params = parse_qs(environ.get('QUERY_STRING', ''))
        
        # 各パラメータは配列として返されるため、最初の要素を取得
        filters = {k: v[0] if v else None for k, v in query_params.items()}
        
        # 学校タイプに応じて処理を分岐
        school_type = filters.get('type', 'elementary')
        
        if school_type == 'elementary':
            result = get_elementary_improved_students(filters)
        else:
            result = get_middle_improved_students(filters)
        
        # レスポンス設定
        start_response('200 OK', [('Content-Type', 'application/json')])
        return [json.dumps(result).encode()]
    
    elif path == 'api/teacher/award-improvement-points' and method == 'POST':
        try:
            # POSTデータを取得
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(content_length)
            data = json.loads(request_body)
              # 教師IDを取得（実際のシステムによって取得方法は異なる）
            # ここではセッションから取得すると仮定
            teacher_id = 1  # 仮のID（実際の環境に合わせて変更）
            
            result = award_improvement_points(data, teacher_id)
            
            # レスポンス設定
            start_response('200 OK', [('Content-Type', 'application/json')])
            return [json.dumps(result).encode()]
        
        except Exception as e:
            logging.error("Error processing request: %s", str(e))
            start_response('400 Bad Request', [('Content-Type', 'application/json')])
            return [json.dumps({'success': False, 'message': str(e)}).encode()]
    
    else:
        # 不明なパスの場合は404を返す
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return [b'Not Found']

# CGIとしても実行可能にする
if __name__ == "__main__":
    # テスト用の実行
    print("Improvement Filter API - Testing Mode")
    
    # テスト用のデータ
    test_filters = {
        'start_month': '1',
        'end_month': '12',
        'subject': 'all',
        'min_improvement': '5'
    }
    
    print("Testing get_elementary_improved_students...")
    try:
        result = get_elementary_improved_students(test_filters)
        print("結果数:", len(result.get('students', [])) if result.get('success') else 0)
        print("成功:", result.get('success'))
    except Exception as e:
        print("エラー:", str(e))
        import traceback
        traceback.print_exc()