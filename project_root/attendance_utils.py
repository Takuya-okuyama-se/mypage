def ensure_attendance_records_table(conn):
    """出席記録テーブルの構造を確認・修正する関数（MySQL用）"""
    try:
        with conn.cursor() as cur:
            # テーブルが存在するか確認
            cur.execute("SHOW TABLES LIKE 'attendance_records'")
            table_exists = cur.fetchone() is not None
            
            import logging
            
            if not table_exists:
                # テーブルが存在しない場合は作成
                logging.error("attendance_recordsテーブルが存在しないため新規作成します")
                cur.execute("""
                    CREATE TABLE attendance_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        attendance_date DATE NOT NULL,
                        status ENUM('present', 'absent', 'late', 'excused') NOT NULL DEFAULT 'present',
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        recorded_by INT NOT NULL,
                        comments TEXT,
                        UNIQUE KEY idx_user_date (user_id, attendance_date),
                        INDEX idx_attendance_date (attendance_date),
                        INDEX idx_user_status (user_id, status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
                """)
                conn.commit()
                logging.error("attendance_recordsテーブルを新規作成しました")
                return
            
            logging.error("attendance_recordsテーブルは既に存在します。構造を確認します")
            
            # テーブルが存在する場合、カラムの確認と追加/修正を行う
            cur.execute("DESCRIBE attendance_records")
            columns_result = cur.fetchall()
            columns = {row['Field']: row for row in columns_result}
            logging.error(f"既存のカラム: {list(columns.keys())}")
            
            # 必要なカラムのリスト
            required_columns = {
                'id': {'Type': 'int', 'Key': 'PRI', 'Extra': 'auto_increment'},
                'user_id': {'Type': 'int', 'Null': 'NO'},
                'attendance_date': {'Type': 'date', 'Null': 'NO'},
                'status': {'Type': "enum('present','absent','late','excused')", 'Default': 'present'},
                'recorded_at': {'Type': 'timestamp', 'Default': 'CURRENT_TIMESTAMP'},
                'recorded_by': {'Type': 'int', 'Null': 'NO'},
                'comments': {'Type': 'text'}
            }
            
            # 必要なカラムが存在しない場合は追加
            missing_columns = []
            for column_name, specs in required_columns.items():
                if column_name not in columns:
                    missing_columns.append(column_name)
                    logging.error(f"カラム {column_name} が不足しています。追加します。")
                    
                    if column_name == 'id':
                        cur.execute("ALTER TABLE attendance_records ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST")
                    elif column_name == 'user_id':
                        cur.execute("ALTER TABLE attendance_records ADD COLUMN user_id INT NOT NULL")
                    elif column_name == 'attendance_date':
                        cur.execute("ALTER TABLE attendance_records ADD COLUMN attendance_date DATE NOT NULL")
                    elif column_name == 'status':
                        cur.execute("ALTER TABLE attendance_records ADD COLUMN status ENUM('present', 'absent', 'late', 'excused') NOT NULL DEFAULT 'present'")
                    elif column_name == 'recorded_at':
                        cur.execute("ALTER TABLE attendance_records ADD COLUMN recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    elif column_name == 'recorded_by':
                        cur.execute("ALTER TABLE attendance_records ADD COLUMN recorded_by INT NOT NULL")
                    elif column_name == 'comments':
                        cur.execute("ALTER TABLE attendance_records ADD COLUMN comments TEXT")
                    conn.commit()
                    logging.error(f"カラム {column_name} を追加しました")
            
            if missing_columns:
                logging.error(f"不足していたカラムを追加しました: {missing_columns}")
            else:
                logging.error("すべての必須カラムが存在します")
            
            # recorded_byカラムがNULLを許可している場合、NOT NULLに変更
            if 'recorded_by' in columns and columns['recorded_by']['Null'] == 'YES':
                logging.error("recorded_byカラムをNOT NULLに変更します")
                # 既存のNULL値を0に更新
                cur.execute("UPDATE attendance_records SET recorded_by = 0 WHERE recorded_by IS NULL")
                # NOT NULL制約を追加
                cur.execute("ALTER TABLE attendance_records MODIFY COLUMN recorded_by INT NOT NULL")
                conn.commit()
                logging.error("recorded_byカラムをNOT NULLに変更しました")
            
            # statusカラムの型をチェック、必要に応じて修正
            if 'status' in columns and not columns['status']['Type'].startswith("enum"):
                logging.error("statusカラムをENUMに変更します")
                # VARCHAR(20)からENUMに変更
                cur.execute("""
                    ALTER TABLE attendance_records 
                    MODIFY COLUMN status ENUM('present', 'absent', 'late', 'excused') NOT NULL DEFAULT 'present'
                """)
                conn.commit()
                logging.error("statusカラムをENUMに変更しました")
            
            # インデックスの確認と作成
            cur.execute("SHOW INDEX FROM attendance_records")
            indexes_result = cur.fetchall()
            indexes = {}
            for row in indexes_result:
                key_name = row.get('Key_name')
                if key_name:
                    indexes[key_name] = row
            
            logging.error(f"既存のインデックス: {list(indexes.keys())}")
              # ユーザーIDと日付の複合ユニークインデックス
            if 'idx_user_date' not in indexes and 'user_id_attendance_date' not in indexes:
                logging.error("user_idとattendance_dateの複合ユニークインデックスを追加します")
                try:
                    # まず重複データがないか確認
                    cur.execute("""
                        SELECT user_id, attendance_date, COUNT(*) as count
                        FROM attendance_records
                        GROUP BY user_id, attendance_date
                        HAVING COUNT(*) > 1
                    """)
                    duplicates = cur.fetchall()
                    
                    if duplicates:
                        logging.error(f"重複データがあります（{len(duplicates)}件）。ユニークインデックス作成前に解決します。")
                        # 重複データを解決（最新のレコードのみを残す）
                        for dup in duplicates:
                            logging.error(f"重複データを解決中: user_id={dup['user_id']}, date={dup['attendance_date']}")
                            # 最新のレコードのIDを取得
                            cur.execute("""
                                SELECT id FROM attendance_records
                                WHERE user_id = %s AND attendance_date = %s
                                ORDER BY recorded_at DESC LIMIT 1
                            """, (dup['user_id'], dup['attendance_date']))
                            latest = cur.fetchone()
                            if latest:
                                # 最新以外を削除
                                cur.execute("""
                                    DELETE FROM attendance_records
                                    WHERE user_id = %s AND attendance_date = %s AND id != %s
                                """, (dup['user_id'], dup['attendance_date'], latest['id']))
                                conn.commit()
                                logging.error(f"重複を解決しました: user_id={dup['user_id']}, date={dup['attendance_date']}")
                    
                    # インデックス作成
                    cur.execute("""
                        ALTER TABLE attendance_records 
                        ADD UNIQUE KEY idx_user_date (user_id, attendance_date)
                    """)
                    conn.commit()
                    logging.error("user_idとattendance_dateの複合ユニークインデックスを追加しました")
                except Exception as e:
                    logging.error(f"ユニークインデックス作成時にエラーが発生しました: {e}")
                    # 重複データが存在する可能性があるため、それを確認
                    cur.execute("""
                        SELECT user_id, attendance_date, COUNT(*) as count
                        FROM attendance_records
                        GROUP BY user_id, attendance_date
                        HAVING COUNT(*) > 1
                    """)
                    duplicates = cur.fetchall()
                    if duplicates:
                        logging.error(f"重複データが見つかりました: {duplicates}")
                        # 重複を解決（最新のレコードのみを残す）
                        for dup in duplicates:
                            logging.error(f"重複データを解決中: user_id={dup['user_id']}, date={dup['attendance_date']}")
                            # 最新のレコードのIDを取得
                            cur.execute("""
                                SELECT id FROM attendance_records
                                WHERE user_id = %s AND attendance_date = %s
                                ORDER BY recorded_at DESC LIMIT 1
                            """, (dup['user_id'], dup['attendance_date']))
                            latest = cur.fetchone()
                            if latest:
                                # 最新以外を削除
                                cur.execute("""
                                    DELETE FROM attendance_records
                                    WHERE user_id = %s AND attendance_date = %s AND id != %s
                                """, (dup['user_id'], dup['attendance_date'], latest['id']))
                                conn.commit()
                                logging.error(f"重複を解決しました: user_id={dup['user_id']}, date={dup['attendance_date']}")
                        
                        # 重複解決後、再度ユニークインデックスを作成
                        try:
                            cur.execute("""
                                ALTER TABLE attendance_records 
                                ADD UNIQUE KEY idx_user_date (user_id, attendance_date)
                            """)
                            conn.commit()
                            logging.error("重複解決後、ユニークインデックスを追加しました")
                        except Exception as e2:
                            logging.error(f"2回目のユニークインデックス作成時にもエラーが発生しました: {e2}")
                    else:
                        logging.error("重複データはありませんが、インデックス作成に失敗しました")
            
            # 日付のインデックス
            if 'idx_attendance_date' not in indexes:
                logging.error("attendance_dateのインデックスを追加します")
                cur.execute("""
                    ALTER TABLE attendance_records 
                    ADD INDEX idx_attendance_date (attendance_date)
                """)
                conn.commit()
                logging.error("attendance_dateのインデックスを追加しました")
            
            # ユーザーIDと出席状態の複合インデックス
            if 'idx_user_status' not in indexes:
                logging.error("user_idとstatusの複合インデックスを追加します")
                cur.execute("""
                    ALTER TABLE attendance_records 
                    ADD INDEX idx_user_status (user_id, status)
                """)
                conn.commit()
                logging.error("user_idとstatusの複合インデックスを追加しました")
            
            logging.error("attendance_recordsテーブルの構造確認・修正が完了しました")
    
    except Exception as e:
        import logging
        logging.error(f"Error ensuring attendance_records table: {e}")
        conn.rollback()
        
        # 詳細なエラー情報を収集
        import traceback
        logging.error(f"詳細なエラー情報: {traceback.format_exc()}")
        
        # エラーに対処する追加ロジック
        try:
            # テーブルが存在するか再確認
            with conn.cursor() as cur:
                cur.execute("SHOW TABLES LIKE 'attendance_records'")
                table_exists = cur.fetchone() is not None
                
                if not table_exists:
                    logging.error("テーブルが存在しないため、再度作成を試みます")
                    # 基本的なテーブル構造で再作成
                    cur.execute("""
                        CREATE TABLE attendance_records (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT NOT NULL,
                            attendance_date DATE NOT NULL,
                            status VARCHAR(20) NOT NULL DEFAULT 'present',
                            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            recorded_by INT NOT NULL
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
                    """)
                    conn.commit()
                    logging.error("attendance_recordsテーブルを基本構造で再作成しました")
        except Exception as recovery_error:
            logging.error(f"リカバリ処理中にエラーが発生しました: {recovery_error}")
            # これ以上の処理は行わない
