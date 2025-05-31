# internal_points_notification.py
# 中学生の内申点向上通知システム

def check_internal_point_improvement(conn, student_id, grade_year, term, subject_id, new_point):
    """内申点向上に基づく通知とボーナスを設定する関数
    
    前学期または前学年最終学期と比較して内申点が向上した場合に通知を生成
    """
    try:
        with conn.cursor() as cur:
            # 前学期または前学年の学期を計算
            previous_term = term - 1
            previous_grade_year = grade_year
            
            if previous_term < 1:
                previous_term = 3  # 前学年の3学期
                previous_grade_year = grade_year - 1
            
            # 前学期の内申点を取得
            cur.execute("""
                SELECT ip.point, s.name as subject_name, u.name as student_name
                FROM internal_points ip
                JOIN subjects s ON ip.subject = s.id
                JOIN users u ON ip.student_id = u.id
                WHERE ip.student_id = %s
                AND ip.grade_year = %s
                AND ip.subject = %s
                AND ip.term = %s
            """, (student_id, previous_grade_year, subject_id, previous_term))
            
            prev_data = cur.fetchone()
            if not prev_data:
                return False, "前学期のデータがありません"
            
            previous_point = prev_data['point']
            subject_name = prev_data['subject_name']
            student_name = prev_data['student_name']
            
            # 内申点の向上を計算
            improvement = new_point - previous_point
            
            if improvement <= 0:
                return False, "内申点が向上していません"
            
            # 向上レベルと推奨ポイントを設定
            if improvement >= 2:
                level = '大'
                points = 50
            elif improvement == 1:
                level = '小'
                points = 20
            else:
                return False, "ボーナス条件を満たしていません"

            # 通知テーブルの存在確認と生成
            cur.execute("SHOW TABLES LIKE 'internal_point_notifications'")
            if not cur.fetchone():
                cur.execute("""
                    CREATE TABLE internal_point_notifications (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        student_id INT NOT NULL,
                        grade_year INT NOT NULL,
                        subject_id INT NOT NULL,
                        previous_term INT NOT NULL,
                        previous_grade_year INT NOT NULL,
                        current_term INT NOT NULL,
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
            
            # 既存の未処理通知を確認
            cur.execute("""
                SELECT id FROM internal_point_notifications
                WHERE student_id = %s
                AND grade_year = %s
                AND subject_id = %s
                AND current_term = %s
                AND is_processed = 0
            """, (student_id, grade_year, subject_id, term))
            
            existing = cur.fetchone()
            
            if existing:
                # 既存の通知を更新
                cur.execute("""
                    UPDATE internal_point_notifications
                    SET previous_point = %s,
                        new_point = %s,
                        improvement_level = %s,
                        potential_points = %s
                    WHERE id = %s
                """, (previous_point, new_point, level, points, existing['id']))
            else:
                # 新規通知を作成
                cur.execute("""
                    INSERT INTO internal_point_notifications
                    (student_id, grade_year, subject_id, 
                    previous_term, previous_grade_year, current_term,
                    previous_point, new_point, improvement_level, potential_points)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    student_id, grade_year, subject_id,
                    previous_term, previous_grade_year, term,
                    previous_point, new_point, level, points
                ))
                
            conn.commit()
            
            return True, {
                'student_name': student_name,
                'subject_name': subject_name,
                'previous_point': previous_point,
                'new_point': new_point,
                'improvement': improvement,
                'level': level,
                'points': points,
                'previous_term': f"{previous_grade_year}年{previous_term}学期",
                'current_term': f"{grade_year}年{term}学期",
            }
    
    except Exception as e:
        conn.rollback()
        return False, f"内申点向上通知処理エラー: {str(e)}"


# この関数を update_internal_point 関数内から呼び出す
def update_internal_point(conn, data):
    """内申点を更新する関数"""
    student_id = data.get('student_id')
    grade_year = data.get('grade_year')
    subject_id = data.get('subject_id')
    term = data.get('term')
    point = data.get('point')
    point_id = data.get('point_id')
    
    try:
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
        
            # 内申点向上通知の処理
            # ユーザーが中学生かチェック
            cur.execute("SELECT role, grade_level, school_type FROM users WHERE id = %s", (student_id,))
            user = cur.fetchone()
            
            if user and user['role'] == 'student' and user['school_type'] == 'middle':
                # 中学生の場合、内申点向上通知を必ず処理（問題点修正）
                success, result = check_internal_point_improvement(conn, student_id, grade_year, term, subject_id, point)
                if not success:
                    print(f"通知生成エラー: {result}")
            
            conn.commit()
            return True, point_id
            
    except Exception as e:
        conn.rollback()
        return False, f"更新エラー: {str(e)}"
    """内申点を更新する関数"""
    student_id = data.get('student_id')
    grade_year = data.get('grade_year')
    subject_id = data.get('subject_id')
    term = data.get('term')
    point = data.get('point')
    point_id = data.get('point_id')
    
    try:
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
        
            # 内申点向上通知の処理
            # ユーザーが中学生かチェック (school_type も確認するように修正)
            cur.execute("SELECT role, grade_level, school_type FROM users WHERE id = %s", (student_id,))
            user = cur.fetchone()
            
            if user and user['role'] == 'student' and user['school_type'] == 'middle':
                # 中学生の場合、内申点向上通知を処理
                check_internal_point_improvement(conn, student_id, grade_year, term, subject_id, point)
            
            conn.commit()
            return True, point_id
            
    except Exception as e:
        conn.rollback()
        return False, f"更新エラー: {str(e)}"