#!/usr/local/bin/python
# -*- coding: utf-8 -*-

# mock_exam_utils.py - 模試関連ユーティリティ関数

from datetime import datetime
import logging

# 模試結果のスコアに応じたポイント計算
def calculate_mock_exam_points(percentage):
    """模試のパーセンテージに基づくポイントを計算する関数"""
    try:
        percentage_value = float(percentage)
        
        if percentage_value >= 90:
            return 50, "模試ボーナス（金）: 90%以上達成"
        elif percentage_value >= 80:
            return 30, "模試ボーナス（銀）: 80%以上達成"
        elif percentage_value >= 70:
            return 20, "模試ボーナス（銅）: 70%以上達成"
        elif percentage_value >= 60:
            return 10, "模試ボーナス: 60%以上達成"
        else:
            return 0, "ポイント付与基準未達"
    except ValueError:
        logging.error(f"Invalid percentage value: {percentage}")
        return 0, "無効なパーセンテージ値"

# 模試スコアの保存
def save_mock_exam_score(conn, data, teacher_id):
    """模試のスコアを保存する関数"""
    try:
        # データ検証
        required_fields = ['student_id', 'exam_type', 'subject', 'score', 'max_score']
        for field in required_fields:
            if field not in data:
                return False, f"必須フィールド {field} がありません"
        
        # パーセンテージの計算
        score = int(data['score'])
        max_score = int(data['max_score'])
        
        if max_score <= 0:
            return False, "満点は0より大きい値である必要があります"
        
        percentage = round(score / max_score * 100, 1)
        
        # 保存処理
        with conn.cursor() as cur:
            # mock_exam_scores テーブルが存在するかチェック
            cur.execute("SHOW TABLES LIKE 'mock_exam_scores'")
            if not cur.fetchone():
                # テーブルが存在しない場合は作成
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS mock_exam_scores (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        student_id INT NOT NULL,
                        exam_date DATE NOT NULL,
                        exam_type VARCHAR(50) NOT NULL,
                        subject VARCHAR(50) NOT NULL,
                        score INT NOT NULL,
                        max_score INT NOT NULL,
                        percentage FLOAT NOT NULL,
                        points_awarded INT DEFAULT 0,
                        created_by INT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX(student_id),
                        INDEX(exam_type),
                        INDEX(exam_date)
                    )
                """)
            
            # データを保存
            sql = """
                INSERT INTO mock_exam_scores 
                (student_id, exam_date, exam_type, subject, score, max_score, percentage, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # 試験日が指定されていない場合は現在の日付を使用
            exam_date = data.get('exam_date', datetime.now().strftime('%Y-%m-%d'))
            
            values = (
                data['student_id'],
                exam_date,
                data['exam_type'],
                data['subject'],
                score,
                max_score,
                percentage,
                teacher_id
            )
            
            cur.execute(sql, values)
            score_id = cur.lastrowid
            
            # ポイント付与
            points_awarded = 0
            if data.get('award_points', False):
                from points_utils import teacher_award_points
                
                # ポイント計算
                points, comment = calculate_mock_exam_points(percentage)
                
                if points > 0:
                    # コメントに試験の詳細を追加
                    full_comment = f"{comment}: {data['exam_type']} {data['subject']} ({data['score']}/{data['max_score']}点 - {percentage}%)"
                    
                    # ポイント付与
                    success, _ = teacher_award_points(
                        conn,
                        teacher_id,
                        data['student_id'],
                        'mock_exam',
                        points,
                        full_comment
                    )
                    
                    if success:
                        points_awarded = points
                        
                        # 付与したポイントを記録
                        cur.execute("""
                            UPDATE mock_exam_scores
                            SET points_awarded = %s
                            WHERE id = %s
                        """, (points, score_id))
            
            conn.commit()
            return True, {
                'score_id': score_id,
                'points_awarded': points_awarded
            }
    
    except Exception as e:
        logging.error(f"Error saving mock exam score: {e}")
        conn.rollback()
        return False, str(e)

# 模試スコアの取得
def get_mock_exam_scores(conn, student_id=None, exam_type=None):
    """模試のスコアを取得する関数"""
    try:
        with conn.cursor() as cur:
            # mock_exam_scores テーブルが存在するかチェック
            cur.execute("SHOW TABLES LIKE 'mock_exam_scores'")
            if not cur.fetchone():
                # テーブルが存在しない場合は空リストを返す
                return True, []
            
            # 基本クエリ
            query = """
                SELECT mes.*, u.name as student_name, t.name as teacher_name, u.school_type as student_school_type
                FROM mock_exam_scores mes
                JOIN users u ON mes.student_id = u.id
                JOIN users t ON mes.created_by = t.id
            """
            
            params = []
            conditions = []
            
            # フィルター条件
            if student_id:
                conditions.append("mes.student_id = %s")
                params.append(student_id)
            
            if exam_type:
                conditions.append("mes.exam_type = %s")
                params.append(exam_type)
            
            # 条件の追加
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # 並び順
            query += " ORDER BY mes.created_at DESC"
            
            # 実行
            cur.execute(query, params)
            scores = cur.fetchall()
            
            # 日付オブジェクトをYYYY-MM-DD文字列に変換（JSON変換用）
            for score in scores:
                if 'exam_date' in score and score['exam_date']:
                    score['exam_date'] = score['exam_date'].strftime('%Y-%m-%d')
            
            return True, scores
    
    except Exception as e:
        logging.error(f"Error getting mock exam scores: {e}")
        return False, str(e)

# 模試スコアの削除
def delete_mock_exam_score(conn, score_id, teacher_id):
    """模試のスコアを削除する関数"""
    try:
        with conn.cursor() as cur:
            # 削除対象のスコアが存在するか確認
            cur.execute("""
                SELECT * FROM mock_exam_scores
                WHERE id = %s
            """, (score_id,))
            
            score = cur.fetchone()
            if not score:
                return False, "スコアが見つかりません"
            
            # 作成者と削除者が一致するか確認（セキュリティチェック）
            if score['created_by'] != teacher_id:
                # 権限チェックは省略（講師であれば他の講師のデータも削除可能）
                pass
            
            # スコアを削除
            cur.execute("""
                DELETE FROM mock_exam_scores
                WHERE id = %s
            """, (score_id,))
            
            conn.commit()
            return True, "スコアを削除しました"
    
    except Exception as e:
        logging.error(f"Error deleting mock exam score: {e}")
        conn.rollback()
        return False, str(e)