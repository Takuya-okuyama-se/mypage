# elementary_grade_utils.py
# 小学生の科目別成績向上通知システム

def check_elementary_grade_improvement(conn, student_id, grade_year, term, subject_id, new_score):
    """小学生の成績向上に基づく通知とボーナスを設定する関数
    
    科目ごと（特に算数・国語・英語）に前回比較して成績が向上した場合に通知を生成
    """
    try:
        with conn.cursor() as cur:
            # 小学生であることを確認 (school_type も確認するように修正)
            cur.execute("SELECT role, grade_level, school_type FROM users WHERE id = %s", (student_id,))
            user = cur.fetchone()
            
            if not user or user['role'] != 'student' or user['school_type'] != 'elementary':
                return False, "対象は小学生ではありません"
            
            # 科目が算数・国語・英語のいずれかか確認（科目IDによる判定）
            cur.execute("SELECT id, name FROM subjects WHERE id = %s", (subject_id,))
            subject = cur.fetchone()
            
            if not subject:
                return False, "科目が見つかりません"
            
            subject_name = subject['name']
            # 主要教科（算数・国語・英語）か確認
            is_main_subject = subject_id in [1, 2, 3]  # ID 1: 国語, ID 2: 算数, ID 3: 英語
            
            if not is_main_subject:
                return False, "主要教科（算数・国語・英語）ではありません"
            
            # 前回の成績を取得（同学年の前の学期、または前学年の最終学期）
            previous_term = term - 1
            previous_grade_year = grade_year
            
            if previous_term < 1:
                previous_term = 3  # 前学年の3学期
                previous_grade_year = grade_year - 1
            
            # 前回の成績を取得
            cur.execute("""
                SELECT g.score, u.name as student_name
                FROM grades g
                JOIN users u ON g.student_id = u.id
                WHERE g.student_id = %s
                AND g.grade_year = %s
                AND g.subject = %s
                AND g.term = %s
            """, (student_id, previous_grade_year, subject_id, previous_term))
            
            prev_data = cur.fetchone()
            if not prev_data:
                return False, "前回の成績データがありません"
            
            previous_score = prev_data['score']
            student_name = prev_data['student_name']
            
            # 成績向上を計算
            score_difference = new_score - previous_score
            
            if score_difference <= 0:
                return False, "成績が向上していません"
            
            # 向上レベルと推奨ポイントを設定
            if score_difference >= 15:
                level = '大'
                points = 50
            elif score_difference >= 10:
                level = '中'
                points = 30
            elif score_difference >= 5:
                level = '小'
                points = 20
            else:
                return False, "ボーナス条件を満たしていません"
            
            # 通知テーブルの存在確認と生成
            cur.execute("SHOW TABLES LIKE 'elementary_grade_notifications'")
            if not cur.fetchone():
                cur.execute("""
                    CREATE TABLE elementary_grade_notifications (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        student_id INT NOT NULL,
                        grade_year INT NOT NULL,
                        subject_id INT NOT NULL,
                        previous_term INT NOT NULL,
                        previous_grade_year INT NOT NULL,
                        current_term INT NOT NULL,
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
            
            # 既存の未処理通知を確認
            cur.execute("""
                SELECT id FROM elementary_grade_notifications
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
                    UPDATE elementary_grade_notifications
                    SET previous_score = %s,
                        new_score = %s,
                        improvement_level = %s,
                        potential_points = %s
                    WHERE id = %s
                """, (previous_score, new_score, level, points, existing['id']))
            else:
                # 新規通知を作成
                cur.execute("""
                    INSERT INTO elementary_grade_notifications
                    (student_id, grade_year, subject_id, 
                    previous_term, previous_grade_year, current_term,
                    previous_score, new_score, improvement_level, potential_points)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    student_id, grade_year, subject_id,
                    previous_term, previous_grade_year, term,
                    previous_score, new_score, level, points
                ))
            
            conn.commit()
            
            return True, {
                'student_name': student_name,
                'subject_name': subject_name,
                'previous_score': previous_score,
                'new_score': new_score,
                'score_difference': score_difference,
                'level': level,
                'points': points,
                'previous_term': f"{previous_grade_year}年{previous_term}学期",
                'current_term': f"{grade_year}年{term}学期",
            }
    
    except Exception as e:
        conn.rollback()
        return False, f"小学生成績向上通知処理エラー: {str(e)}"


# この関数を update_grade 関数内から呼び出す
def update_grade(conn, data):
    """成績を更新する関数"""
    student_id = data.get('student_id')
    grade_year = data.get('grade_year')
    subject_id = data.get('subject_id')
    term = data.get('term')
    score = data.get('score')
    grade_id = data.get('grade_id')
    
    try:
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
        
            # ユーザーが小学生かチェック
            cur.execute("SELECT role, grade_level, school_type FROM users WHERE id = %s", (student_id,))
            user = cur.fetchone()
            
            if user and user['role'] == 'student' and user['school_type'] == 'elementary':
                # 小学生の場合、成績向上通知を必ず生成する（問題点修正）
                success, result = check_elementary_grade_improvement(conn, student_id, grade_year, term, subject_id, score)
                if not success:
                    print(f"通知生成エラー: {result}")
            
            conn.commit()
            return True, grade_id
            
    except Exception as e:
        conn.rollback()
        return False, f"更新エラー: {str(e)}"
    """成績を更新する関数"""
    student_id = data.get('student_id')
    grade_year = data.get('grade_year')
    subject_id = data.get('subject_id')
    term = data.get('term')
    score = data.get('score')
    grade_id = data.get('grade_id')
    
    try:
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
        
            # 成績向上通知の処理
            # ユーザーが小学生かチェック
            cur.execute("SELECT role, grade_level, school_type FROM users WHERE id = %s", (student_id,))
            user = cur.fetchone()
            
            if user and user['role'] == 'student' and user['school_type'] == 'elementary':
                # 小学生の場合、成績向上通知を処理
                check_elementary_grade_improvement(conn, student_id, grade_year, term, subject_id, score)
            
            conn.commit()
            return True, grade_id
            
    except Exception as e:
        conn.rollback()
        return False, f"更新エラー: {str(e)}"