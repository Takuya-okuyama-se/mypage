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
                    english VARCHAR(255) NOT NULL COMMENT '英単語',
                    japanese VARCHAR(255) NOT NULL COMMENT '日本語意味',
                    pronunciation VARCHAR(255) COMMENT '発音',
                    audio_url VARCHAR(255) COMMENT '音声ファイルURL',
                    notes TEXT COMMENT '追加情報・メモ',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_grade_question (grade, question_id),
                    INDEX idx_grade_stage (grade, stage_number),
                    INDEX idx_english (english(20)),
                    INDEX idx_japanese (japanese(20))
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """)
            
            # カラムの存在確認と追加（既存テーブルへの後方互換性対応）
            columns_to_check = [
                ('english', "ALTER TABLE eiken_words ADD COLUMN english VARCHAR(255) NOT NULL COMMENT '英単語' AFTER stage_number"),
                ('japanese', "ALTER TABLE eiken_words ADD COLUMN japanese VARCHAR(255) NOT NULL COMMENT '日本語意味' AFTER english"),
                ('notes', "ALTER TABLE eiken_words ADD COLUMN notes TEXT COMMENT '追加情報・メモ' AFTER audio_url"),
                ('audio_url', "ALTER TABLE eiken_words ADD COLUMN audio_url VARCHAR(255) COMMENT '音声ファイルURL' AFTER pronunciation")
            ]
            
            for column_name, alter_sql in columns_to_check:
                try:
                    cur.execute(f"SHOW COLUMNS FROM eiken_words LIKE '{column_name}'")
                    if not cur.fetchone():
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
                        cur.execute(create_index_sql)
                        log_error(f"eiken_words テーブルに {index_name} インデックスを追加しました")
                except Exception as index_error:
                    log_error(f"インデックス確認/追加エラー ({index_name}): {index_error}")
            
            # 後方互換性対応：wordカラムがあれば、それをenglishにマッピング
            try:
                cur.execute("SHOW COLUMNS FROM eiken_words LIKE 'word'")
                if cur.fetchone():
                    # wordカラムの値をenglishカラムにコピー
                    cur.execute("""
                        UPDATE eiken_words SET english = word 
                        WHERE english IS NULL OR english = ''
                    """)
                    log_error("wordカラムの値をenglishカラムに移行しました")
            except Exception as word_migrate_error:
                log_error(f"word->english移行エラー: {word_migrate_error}")
                
            log_error("eiken_words テーブルを確認/作成しました")
            conn.commit()
    except Exception as e:
        log_error(f"Error creating eiken_words table: {e}")
        conn.rollback()

def ensure_eiken_progress_table(conn):
    """英検単語学習進捗テーブルを確認・作成する"""
    try:
        with conn.cursor() as cur:
            # テーブル作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS eiken_word_progress (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL COMMENT '生徒ID',
                    word_id INT NOT NULL COMMENT '英検単語ID',
                    status VARCHAR(20) NOT NULL DEFAULT 'new' COMMENT '学習状況 (new, learning, mastered)',
                    last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '最後に学習した日時',
                    correct_count INT NOT NULL DEFAULT 0 COMMENT '正解回数',
                    incorrect_count INT NOT NULL DEFAULT 0 COMMENT '不正解回数',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY (student_id, word_id),
                    INDEX idx_student_id (student_id),
                    INDEX idx_word_id (word_id),
                    INDEX idx_status (status),
                    INDEX idx_last_reviewed (last_reviewed)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """)
            
            log_error("eiken_word_progress テーブルを確認/作成しました")
            conn.commit()
    except Exception as e:
        log_error(f"Error creating eiken_word_progress table: {e}")
        conn.rollback()
