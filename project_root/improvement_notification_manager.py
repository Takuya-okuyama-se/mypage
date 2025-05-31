#!/usr/local/bin/python
# -*- coding: utf-8 -*-

# 成績・内申点向上通知管理のユーティリティモジュール

import logging
from datetime import datetime

def ensure_notification_tables(conn):
    """各通知テーブルを確認・必要に応じて作成する"""
    try:
        with conn.cursor() as cur:
            # 1. 中学生成績向上通知テーブル
            cur.execute("SHOW TABLES LIKE 'grade_improvement_notifications'")
            if not cur.fetchone():
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
                logging.info("grade_improvement_notifications テーブルを作成しました")
            
            # 2. 小学生成績向上通知テーブル
            cur.execute("SHOW TABLES LIKE 'elementary_grade_improvement_notifications'")
            if not cur.fetchone():
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS elementary_grade_improvement_notifications (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        student_id INT NOT NULL,
                        grade_year INT NOT NULL,
                        subject_id INT NOT NULL,
                        month INT NOT NULL,
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
                logging.info("elementary_grade_improvement_notifications テーブルを作成しました")
            
            # 3. 高校生成績向上通知テーブル
            cur.execute("SHOW TABLES LIKE 'high_school_grade_improvement_notifications'")
            if not cur.fetchone():
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS high_school_grade_improvement_notifications (
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
                logging.info("high_school_grade_improvement_notifications テーブルを作成しました")
            
            # 4. 内申点向上通知テーブル
            cur.execute("SHOW TABLES LIKE 'internal_point_improvement_notifications'")
            if not cur.fetchone():
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS internal_point_improvement_notifications (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        student_id INT NOT NULL,
                        grade_year INT NOT NULL,
                        subject_id INT NOT NULL,
                        term INT NOT NULL,
                        previous_point INT NOT NULL,
                        new_point INT NOT NULL,
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
                logging.info("internal_point_improvement_notifications テーブルを作成しました")
        
        conn.commit()
    except Exception as e:
        logging.error(f"Error ensuring notification tables: {e}")
        conn.rollback()
        raise

def get_notification_counts(conn):
    """未処理の成績・内申点向上通知数を取得する"""
    counts = {
        'elementary_count': 0,
        'middle_count': 0,
        'high_count': 0,
        'internal_count': 0,
        'total_count': 0
    }
    
    try:
        with conn.cursor() as cur:
            # 小学生成績向上通知
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM elementary_grade_improvement_notifications 
                WHERE is_processed = 0
            """)
            result = cur.fetchone()
            if result:
                counts['elementary_count'] = result['count']
            
            # 中学生成績向上通知
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM grade_improvement_notifications 
                WHERE is_processed = 0
            """)
            result = cur.fetchone()
            if result:
                counts['middle_count'] = result['count']
            
            # 高校生成績向上通知
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM high_school_grade_improvement_notifications 
                WHERE is_processed = 0
            """)
            result = cur.fetchone()
            if result:
                counts['high_count'] = result['count']
            
            # 内申点向上通知
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM internal_point_improvement_notifications 
                WHERE is_processed = 0
            """)
            result = cur.fetchone()
            if result:
                counts['internal_count'] = result['count']
            
            # 合計
            counts['total_count'] = (
                counts['elementary_count'] + 
                counts['middle_count'] + 
                counts['high_count'] + 
                counts['internal_count']
            )
    
    except Exception as e:
        logging.error(f"Error getting notification counts: {e}")
    
    return counts

def get_elementary_student_notifications(conn):
    """小学生の成績向上通知を取得する"""
    try:
        # 直接 elementary_grades テーブルからデータを集計して通知を生成
        with conn.cursor() as cur:
            cur.execute("""
                SELECT eg.*, u.name as student_name, s.name as subject_name,
                       t.name as teacher_name, u.grade_level
                FROM elementary_grades eg
                JOIN users u ON eg.student_id = u.id
                JOIN subjects s ON eg.subject = s.id
                LEFT JOIN users t ON t.role = 'teacher'
                WHERE u.school_type = 'elementary'
                AND eg.score >= 80
                ORDER BY eg.created_at DESC
                LIMIT 10
            """)
            results = cur.fetchall() or []

            notifications = []
            for r in results:
                # 通知データを構築
                notifications.append({
                    'id': r.get('id'),
                    'type': 'elementary',
                    'student_id': r.get('student_id'),
                    'student_name': r.get('student_name', '不明'),
                    'student_type': 'elementary',
                    'grade_year': r.get('grade_year'),
                    'subject_id': r.get('subject'),
                    'subject_name': r.get('subject_name', '不明'),
                    'term_month': r.get('month'),
                    'previous_score': 0,  # 仮の値
                    'new_score': r.get('score', 0),
                    'improvement': 0,  # 仮の値
                    'improvement_level': '中' if r.get('score', 0) >= 85 else '小',
                    'potential_points': 30 if r.get('score', 0) >= 85 else 20,
                    'is_processed': 0,
                    'processed_by': None,
                    'processed_at': None,
                    'teacher_name': r.get('teacher_name'),
                    'created_at': r.get('created_at', datetime.now()),
                    'term_display': f"{r.get('grade_year', '?')}年{r.get('month', '?')}月",
                    'notification_text': f"{r.get('subject_name', '不明')}のテストで{r.get('score', 0)}点を獲得しました"
                })
            
            return notifications
    except Exception as e:
        logging.error(f"Error getting elementary student notifications: {e}")
        return []

def get_middle_student_notifications(conn):
    """中学生の成績と内申点向上通知を取得する"""
    try:
        notifications = []
        
        # 成績データを取得
        with conn.cursor() as cur:
            cur.execute("""
                SELECT g.*, u.name as student_name, s.name as subject_name,
                       t.name as teacher_name, u.grade_level
                FROM grades g
                JOIN users u ON g.student_id = u.id
                JOIN subjects s ON g.subject = s.id
                LEFT JOIN users t ON t.role = 'teacher' AND t.id = 1
                WHERE u.school_type = 'middle'
                AND g.score >= 70
                ORDER BY g.id DESC
                LIMIT 5
            """)
            grade_results = cur.fetchall() or []
            
            for r in grade_results:
                notifications.append({
                    'id': r.get('id'),
                    'type': 'middle',
                    'student_id': r.get('student_id'),
                    'student_name': r.get('student_name', '不明'),
                    'student_type': 'middle',
                    'grade_year': r.get('grade_year'),
                    'subject_id': r.get('subject'),
                    'subject_name': r.get('subject_name', '不明'),
                    'term': r.get('term'),
                    'previous_score': 0,  # 仮の値
                    'new_score': r.get('score', 0),
                    'improvement': 0,  # 仮の値
                    'improvement_level': '大' if r.get('score', 0) >= 85 else ('中' if r.get('score', 0) >= 75 else '小'),
                    'potential_points': 50 if r.get('score', 0) >= 85 else (30 if r.get('score', 0) >= 75 else 20),
                    'is_processed': 0,
                    'processed_by': None,
                    'processed_at': None,
                    'teacher_name': r.get('teacher_name'),
                    'created_at': datetime.now(),
                    'term_display': f"{r.get('grade_year', '?')}年{r.get('term', '?')}学期",
                    'notification_text': f"{r.get('subject_name', '不明')}のテストで{r.get('score', 0)}点を獲得しました"
                })
        
        # 内申点データを取得
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ip.*, u.name as student_name, s.name as subject_name,
                       t.name as teacher_name, u.grade_level
                FROM internal_points ip
                JOIN users u ON ip.student_id = u.id
                JOIN subjects s ON ip.subject = s.id
                LEFT JOIN users t ON t.role = 'teacher' AND t.id = 1
                WHERE u.school_type = 'middle'
                AND ip.point >= 3
                ORDER BY ip.id DESC
                LIMIT 5
            """)
            internal_results = cur.fetchall() or []
            
            for r in internal_results:
                notifications.append({
                    'id': r.get('id'),
                    'type': 'internal',
                    'student_id': r.get('student_id'),
                    'student_name': r.get('student_name', '不明'),
                    'student_type': 'middle',
                    'grade_year': r.get('grade_year'),
                    'subject_id': r.get('subject'),
                    'subject_name': r.get('subject_name', '不明'),
                    'term': r.get('term'),
                    'previous_point': 0,  # 仮の値
                    'new_point': r.get('point', 0),
                    'improvement': 0,  # 仮の値
                    'improvement_level': '大' if r.get('point', 0) >= 5 else ('中' if r.get('point', 0) >= 4 else '小'),
                    'potential_points': 50 if r.get('point', 0) >= 5 else (30 if r.get('point', 0) >= 4 else 20),
                    'is_processed': 0,
                    'processed_by': None,
                    'processed_at': None,
                    'teacher_name': r.get('teacher_name'),
                    'created_at': datetime.now(),
                    'term_display': f"{r.get('grade_year', '?')}年{r.get('term', '?')}学期",
                    'notification_text': f"{r.get('subject_name', '不明')}の内申点で{r.get('point', 0)}を獲得しました"
                })
                
        return notifications
    except Exception as e:
        logging.error(f"Error getting middle student notifications: {e}")
        return []

def get_high_school_notifications(conn):
    """高校生の成績向上通知を取得する"""
    try:
        # grade_improvement_notifications テーブルからデータを取得
        with conn.cursor() as cur:
            cur.execute("""
                SELECT g.*, u.name as student_name, s.name as subject_name,
                       t.name as teacher_name, u.grade_level
                FROM grades g
                JOIN users u ON g.student_id = u.id
                JOIN subjects s ON g.subject = s.id
                LEFT JOIN users t ON t.role = 'teacher' AND t.id = 1
                WHERE u.school_type = 'high'
                AND g.score >= 70
                ORDER BY g.id DESC
                LIMIT 5
            """)
            grade_results = cur.fetchall() or []
            
            notifications = []
            for r in grade_results:
                notifications.append({
                    'id': r.get('id'),
                    'type': 'high',
                    'student_id': r.get('student_id'),
                    'student_name': r.get('student_name', '不明'),
                    'student_type': 'high',
                    'grade_year': r.get('grade_year'),
                    'subject_id': r.get('subject'),
                    'subject_name': r.get('subject_name', '不明'),
                    'term': r.get('term'),
                    'previous_score': 0,  # 仮の値
                    'new_score': r.get('score', 0),
                    'improvement': 0,  # 仮の値
                    'improvement_level': '大' if r.get('score', 0) >= 85 else ('中' if r.get('score', 0) >= 75 else '小'),
                    'potential_points': 50 if r.get('score', 0) >= 85 else (30 if r.get('score', 0) >= 75 else 20),
                    'is_processed': 0,
                    'processed_by': None,
                    'processed_at': None,
                    'teacher_name': r.get('teacher_name'),
                    'created_at': datetime.now(),
                    'term_display': f"{r.get('grade_year', '?')}年{r.get('term', '?')}学期",
                    'notification_text': f"{r.get('subject_name', '不明')}のテストで{r.get('score', 0)}点を獲得しました"
                })
                
            return notifications
    except Exception as e:
        logging.error(f"Error getting high school notifications: {e}")
        return []

def get_all_improvement_notifications(conn):
    """すべての成績・内申点向上通知を取得する"""
    all_notifications = []
    
    try:
        # 通知テーブルからでなく、直接各種テーブルからデータを取得
        
        # 1. 小学生のデータを elementary_grades から取得
        elementary_notifications = get_elementary_student_notifications(conn)
        all_notifications.extend(elementary_notifications)
        
        # 2. 中学生の成績とシンセキ内申点データを取得
        middle_notifications = get_middle_student_notifications(conn)
        all_notifications.extend(middle_notifications)
        
        # 3. 高校生の成績データを取得
        high_school_notifications = get_high_school_notifications(conn)
        all_notifications.extend(high_school_notifications)
        
        # 4. 各通知テーブルからの既存データも取得して追加
        try:
            with conn.cursor() as cur:
                # grade_improvement_notifications からのデータ
                cur.execute("""
                    SELECT n.*, u.name as student_name, s.name as subject_name,
                           t.name as teacher_name, 'middle' as student_type
                    FROM grade_improvement_notifications n
                    JOIN users u ON n.student_id = u.id
                    JOIN subjects s ON n.subject_id = s.id
                    LEFT JOIN users t ON n.processed_by = t.id
                    ORDER BY n.is_processed ASC, n.created_at DESC
                    LIMIT 10
                """)
                db_notifications = cur.fetchall() or []
                
                for n in db_notifications:
                    display_term = f"{n.get('grade_year', '?')}年{n.get('term', '?')}学期"
                    notification = {
                        'id': n.get('id'),
                        'type': 'middle',
                        'student_id': n.get('student_id'),
                        'student_name': n.get('student_name', '不明'),
                        'student_type': 'middle',
                        'grade_year': n.get('grade_year'),
                        'subject_id': n.get('subject_id'),
                        'subject_name': n.get('subject_name', '不明'),
                        'term': n.get('term'),
                        'previous_score': n.get('previous_score', 0),
                        'new_score': n.get('new_score', 0),
                        'improvement': n.get('new_score', 0) - n.get('previous_score', 0),
                        'improvement_level': n.get('improvement_level', '不明'),
                        'potential_points': n.get('potential_points', 0),
                        'is_processed': n.get('is_processed', 0),
                        'processed_by': n.get('processed_by'),
                        'processed_at': n.get('processed_at'),
                        'teacher_name': n.get('teacher_name'),
                        'created_at': n.get('created_at', datetime.now()),
                        'term_display': display_term,
                        'notification_text': f"{n.get('subject_name', '不明')}の成績が{n.get('previous_score', 0)}点から{n.get('new_score', 0)}点に向上しました"
                    }
                    all_notifications.append(notification)
        except Exception as e:
            logging.error(f"Error getting existing notifications: {e}")
    
    except Exception as e:
        logging.error(f"Error getting improvement notifications: {e}")
    
    # 日付の新しい順にソート（通知には created_at が必須）
    try:
        # created_at がない場合は現在時刻をデフォルトとして使用
        all_notifications.sort(
            key=lambda x: x.get('created_at', datetime.now()) if x.get('created_at') else datetime.now(), 
            reverse=True
        )
    except Exception as e:
        logging.error(f"Error sorting notifications: {e}")
    
    return all_notifications

def process_notification(conn, notification_id, notification_type, student_id, points, teacher_id):
    """通知を処理し、ポイントを付与する"""
    try:
        # 直接ポイント付与処理を実行
        comment = f"成績・内申点向上ボーナス: {points}ポイント付与"
        
        event_types = {
            'elementary': 'grade_improvement_small',
            'middle': 'grade_improvement_medium',
            'high': 'high_school_grade_improvement_medium',
            'internal': 'internal_point_improvement_small'
        }
        
        event_type = event_types.get(notification_type, 'grade_improvement_small')
        
        # ポイント付与
        try:
            from points_utils import teacher_award_points
            
            # ポイント付与
            award_success, award_message = teacher_award_points(
                conn,
                teacher_id,
                student_id,
                event_type,
                points,
                comment
            )
            
            if not award_success:
                return False, f"ポイント付与エラー: {award_message}"
            
            conn.commit()
            return True, f"{points}ポイントを付与しました"
            
        except ImportError:
            return False, "ポイント付与システムが利用できません"
    
    except Exception as e:
        logging.error(f"Error processing notification: {e}")
        conn.rollback()
        return False, f"処理エラー: {str(e)}"

if __name__ == "__main__":
    print("このファイルは直接実行せず、インポートして使用してください。")