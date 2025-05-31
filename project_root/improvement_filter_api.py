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

# ログディレクトリを作成
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except:
        pass

try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=os.path.join(log_dir, 'improvement_filter.log'),
        filemode='a'
    )
except:
    # ログファイルが作成できない場合は標準出力を使用
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# ライブラリのインポート
# 現在のディレクトリをPythonパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from points_utils import teacher_award_points
except ImportError:
    # points_utils モジュールが見つからない場合のスタブ実装
    def teacher_award_points(conn, teacher_id, student_id, event_type, points, comment=None):
        # ダミー実装
        logging.warning("points_utils モジュールがないためダミー実装を使用")
        
        # 直接 point_history テーブルに挿入する
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO point_history
                    (user_id, points, event_type, comment, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (student_id, points, event_type, comment, teacher_id))
                conn.commit()
                return True, "ポイントを付与しました（ID: {}）".format(cur.lastrowid)
        except Exception as e:
            conn.rollback()
            return False, str(e)

# 設定をインポート
try:
    from config import Config
except ImportError:
    # config.pyがない場合のフォールバック設定
    class Config:
        MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql3103.db.sakura.ne.jp')
        MYSQL_USER = os.getenv('MYSQL_USER', 'seishinn')
        MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'Yakyuubu8')
        MYSQL_DB = os.getenv('MYSQL_DB', 'seishinn_test')
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
        # フィルターパラメータの処理を改善
        # month パラメータを使用（start_month/end_month ではなく）
        month = filters.get('month')
        if isinstance(month, list):
            month = month[0] if month else None
        current_month = int(month) if month else datetime.now().month
        
        # subject パラメータ
        subject_id = filters.get('subject')
        if isinstance(subject_id, list):
            subject_id = subject_id[0] if subject_id else None
        
        # min_improvement パラメータ
        min_improvement_str = filters.get('min_improvement', '0')
        if isinstance(min_improvement_str, list):
            min_improvement_str = min_improvement_str[0] if min_improvement_str else '0'
        min_improvement = int(min_improvement_str) if min_improvement_str else 0
        
        logging.info(f"Processing elementary students - month: {current_month}, subject: {subject_id}, min_improvement: {min_improvement}")
        
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
                    COALESCE(sub.name, CONCAT('科目', e1.subject)) AS subject_name,
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
            
            # 前月を計算
            previous_month = current_month - 1 if current_month > 1 else 12
            params = [current_month, previous_month, min_improvement]
            
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
                # ポイント付与状況をチェック（月を考慮）
                cur.execute("""
                    SELECT id, points, comment, created_at 
                    FROM point_history 
                    WHERE user_id = %s 
                    AND event_type LIKE 'grade_improvement%'
                    AND comment LIKE %s
                    AND is_active = 1
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (row['student_id'], f"%{row['current_month']}月%"))
                
                points_awarded = cur.fetchone()
                
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
                    'improvement': row['improvement'],
                    # ポイント付与状況を追加
                    'points_awarded': bool(points_awarded),
                    'is_points_awarded': bool(points_awarded),
                    'awarded_points': points_awarded['points'] if points_awarded else 0,
                    'awarded_date': points_awarded['created_at'].strftime('%Y-%m-%d %H:%M:%S') if points_awarded else None,
                    'awarded_comment': points_awarded['comment'] if points_awarded else None
                }
                
                students.append(student)
            
            # points_statusフィルターを適用
            points_status = filters.get('points_status')
            if isinstance(points_status, list):
                points_status = points_status[0] if points_status else None
                
            if points_status == 'pending':
                students = [s for s in students if not s['points_awarded']]
            elif points_status == 'awarded':
                students = [s for s in students if s['points_awarded']]
                
            return {'success': True, 'students': students}
    
    except Exception as e:
        # エラーメッセージを安全に処理
        logging.error("Error in get_elementary_improved_students: %s", str(e))
        import traceback
        logging.error("Traceback: %s", traceback.format_exc())
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
        # フィルターから値を取得
        from_internal = filters.get('from_internal')
        if isinstance(from_internal, list):
            from_internal = from_internal[0] if from_internal else '1-1'
        from_internal = from_internal or '1-1'
        
        to_internal = filters.get('to_internal')
        if isinstance(to_internal, list):
            to_internal = to_internal[0] if to_internal else '1-2'
        to_internal = to_internal or '1-2'
        
        # 期間情報を解析
        from_parts = from_internal.split('-')
        start_year = int(from_parts[0])
        start_term = int(from_parts[1])
        
        to_parts = to_internal.split('-')
        end_year = int(to_parts[0])
        end_term = int(to_parts[1])
        
        subject_id = filters.get('subject')
        if isinstance(subject_id, list):
            subject_id = subject_id[0] if subject_id else None
            
        min_improvement_str = filters.get('min_improvement', '0')
        if isinstance(min_improvement_str, list):
            min_improvement_str = min_improvement_str[0] if min_improvement_str else '0'
        min_improvement = int(min_improvement_str) if min_improvement_str else 0
        
        logging.info(f"Processing middle internal points - from: {from_internal}, to: {to_internal}, subject: {subject_id}, min_improvement: {min_improvement}")
        
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
                    COALESCE(sub.name, CONCAT('科目', e1.subject)) AS subject_name,
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
                    (p1.point - p2.point) >= %s
            """
            
            params = [end_year, end_term, start_year, start_term, min_improvement]
            
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
                # ポイント付与状況をチェック（学期と年を考慮）
                cur.execute("""
                    SELECT id, points, comment, created_at 
                    FROM point_history 
                    WHERE user_id = %s 
                    AND event_type LIKE 'grade_improvement%'
                    AND comment LIKE %s
                    AND is_active = 1
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (row['student_id'], f"%{row['current_year']}年{row['current_term']}学期%"))
                
                points_awarded = cur.fetchone()
                
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
                    'previous_period': f"{row['previous_year']}-{row['previous_term']}",
                    'current_period': f"{row['current_year']}-{row['current_term']}",
                    'previous_point': row['previous_point'],
                    'current_point': row['current_point'],
                    'improvement': row['improvement'],
                    'comparison_type': 'internal',
                    # ポイント付与状況を追加
                    'points_awarded': bool(points_awarded),
                    'is_points_awarded': bool(points_awarded),
                    'awarded_points': points_awarded['points'] if points_awarded else 0,
                    'awarded_date': points_awarded['created_at'].strftime('%Y-%m-%d %H:%M:%S') if points_awarded else None,
                    'awarded_comment': points_awarded['comment'] if points_awarded else None
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
        - improvement_type: 成績向上種別
    - teacher_id: 教師ID
    """
    
    conn = get_db_connection()
    
    try:
        student_id = int(data.get('student_id'))
        points = int(data.get('points'))
        event_type = data.get('event_type')
        comment = data.get('comment')
        subject_id = data.get('subject_id')
        improvement_type = data.get('improvement_type', 'general')
        
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
                return {
                    'success': False,
                    'message': f'この生徒には既に{improvement_type}の成績向上ポイントが付与されています（{existing_award["created_at"]}）',
                    'points': 0,
                    'student_id': student_id,
                    'already_awarded': True,
                    'existing_points': existing_award['points'],
                    'awarded_date': existing_award['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                }
        
        # 重複がない場合、ポイント付与実行
        success, message = teacher_award_points(
            conn,
            teacher_id,
            student_id,
            event_type,
            points,
            f"{comment} ({improvement_type})"
        )
        
        return {
            'success': success,
            'message': message,
            'points': points,
            'student_id': student_id
        }
    
    except Exception as e:
        logging.error("Error in award_improvement_points: %s", str(e))
        return {'success': False, 'message': str(e)}
        
    finally:
        conn.close()

# 中学生の定期テスト比較データを取得するAPI
def get_middle_exam_improved_students(filters):
    """
    中学生の定期テスト成績向上データを取得するAPI
    
    引数:
    - filters: フィルター辞書
        - from_exam: 比較元テスト（例: "1-1", "1-1-final"）
        - to_exam: 比較先テスト（例: "1-2", "1-2-final"）
        - subject: 科目ID（all の場合はすべての科目）
        - min_improvement: 最小向上点数
    """
    
    conn = get_db_connection()
    
    try:
        # フィルターから値を取得
        from_exam = filters.get('from_exam')
        if isinstance(from_exam, list):
            from_exam = from_exam[0] if from_exam else '1-1'
        from_exam = from_exam or '1-1'
        
        to_exam = filters.get('to_exam')
        if isinstance(to_exam, list):
            to_exam = to_exam[0] if to_exam else '1-1-final'
        to_exam = to_exam or '1-1-final'
        
        subject_id = filters.get('subject')
        if isinstance(subject_id, list):
            subject_id = subject_id[0] if subject_id else None
            
        min_improvement_str = filters.get('min_improvement', '0')
        if isinstance(min_improvement_str, list):
            min_improvement_str = min_improvement_str[0] if min_improvement_str else '0'
        min_improvement = int(min_improvement_str) if min_improvement_str else 0
        
        logging.info(f"Processing middle exam students - from: {from_exam}, to: {to_exam}, subject: {subject_id}, min_improvement: {min_improvement}")
        
        # 期間を月に変換（簡易的なマッピング）
        # 1-1 (1年1学期中間) → 5月, 1-1-final (1年1学期期末) → 7月
        # 1-2 (1年2学期中間) → 10月, 1-2-final (1年2学期期末) → 12月
        # 1-3 (1年3学期学年末) → 3月
        exam_to_month = {
            '1-1': 5, '1-1-final': 7,
            '1-2': 10, '1-2-final': 12,
            '1-3': 3,
            '2-1': 5, '2-1-final': 7,
            '2-2': 10, '2-2-final': 12,
            '2-3': 3,
            '3-1': 5, '3-1-final': 7,
            '3-2': 10, '3-2-final': 12,
            '3-3': 3
        }
        
        from_month = exam_to_month.get(from_exam, 5)
        to_month = exam_to_month.get(to_exam, 7)
        
        with conn.cursor() as cur:
            # 基本的なSQLクエリの構築
            query = """
                SELECT 
                    e1.student_id, 
                    e1.score AS current_score,
                    e1.month AS current_month,
                    e2.score AS previous_score,
                    e2.month AS previous_month,
                    u.name AS student_name,
                    u.school_type,
                    u.grade_level,
                    e1.subject,
                    COALESCE(sub.name, CONCAT('科目', e1.subject)) AS subject_name,
                    (e1.score - e2.score) AS improvement
                FROM grades e1
                JOIN grades e2 ON 
                    e1.student_id = e2.student_id AND 
                    e1.subject = e2.subject AND
                    e1.grade_year = e2.grade_year
                JOIN users u ON e1.student_id = u.id
                LEFT JOIN subjects sub ON e1.subject = sub.id
                WHERE 
                    u.school_type = 'middle' AND
                    e1.month = %s AND 
                    e2.month = %s AND
                    (e1.score - e2.score) >= %s
            """
            
            params = [to_month, from_month, min_improvement]
            
            # 科目フィルターが指定されている場合はWHERE句に追加
            if subject_id != 'all':
                query += " AND e1.subject = %s"
                params.append(subject_id)
                
            # 向上幅でソート
            query += " ORDER BY (e1.score - e2.score) DESC"
            
            # クエリを実行
            cur.execute(query, params)
            results = cur.fetchall()
            
            # 結果をリスト形式に整形
            students = []
            for row in results:
                # ポイント付与状況をチェック
                cur.execute("""
                    SELECT id, points, comment, created_at 
                    FROM point_history 
                    WHERE user_id = %s 
                    AND event_type LIKE 'grade_improvement%'
                    AND comment LIKE %s
                    AND is_active = 1
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (row['student_id'], f"%{to_exam}%"))
                
                points_awarded = cur.fetchone()
                
                # JavaScriptで使いやすい形式に変換
                student = {
                    'id': row['student_id'],
                    'name': row['student_name'],
                    'grade_level': row['grade_level'],
                    'school_type': row['school_type'],
                    'subject_id': row['subject'],
                    'subject_name': row['subject_name'],
                    'previous_period': from_exam,
                    'current_period': to_exam,
                    'previous_score': row['previous_score'],
                    'current_score': row['current_score'],
                    'improvement': row['improvement'],
                    'comparison_type': 'exam',
                    # ポイント付与状況を追加
                    'points_awarded': bool(points_awarded),
                    'is_points_awarded': bool(points_awarded),
                    'awarded_points': points_awarded['points'] if points_awarded else 0,
                    'awarded_date': points_awarded['created_at'].strftime('%Y-%m-%d %H:%M:%S') if points_awarded else None,
                    'awarded_comment': points_awarded['comment'] if points_awarded else None
                }
                
                students.append(student)
                
            return {'success': True, 'students': students}
    
    except Exception as e:
        # エラーメッセージを安全に処理
        logging.error("Error in get_middle_exam_improved_students: %s", str(e))
        import traceback
        logging.error("Traceback: %s", traceback.format_exc())
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
        elif school_type == 'middle':
            comparison_type = filters.get('comparison_type', 'internal')
            if comparison_type == 'exam':
                result = get_middle_exam_improved_students(filters)
            else:
                result = get_middle_improved_students(filters)
        else:
            result = {'success': False, 'message': 'Invalid school type'}
        
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
