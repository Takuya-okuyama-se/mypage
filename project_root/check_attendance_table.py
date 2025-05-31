import pymysql
from pymysql.cursors import DictCursor
import sys
import os
import logging
from datetime import datetime

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('attendance_check.log'),
        logging.StreamHandler()
    ]
)

# アプリケーションモジュールをインポートするためにパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

def get_db_connection():
    """データベース接続を取得する"""
    # データベース接続情報
    db_config = {
        'host': Config.MYSQL_HOST,
        'user': Config.MYSQL_USER,
        'password': Config.MYSQL_PASSWORD,
        'database': Config.MYSQL_DB,
        'port': Config.MYSQL_PORT,
        'charset': 'utf8mb4',
        'cursorclass': DictCursor,
    }
    
    try:
        # データベース接続
        conn = pymysql.connect(**db_config)
        logging.info("データベースに接続しました")
        return conn
    except Exception as e:
        logging.error(f"データベース接続エラー: {e}")
        raise

def check_attendance_table():
    """出席記録テーブルの構造を確認する"""
    try:
        conn = get_db_connection()
        
        with conn.cursor() as cursor:
            # テーブルが存在するか確認
            cursor.execute("SHOW TABLES LIKE 'attendance_records'")
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                logging.info("出席記録テーブルが存在します。構造を確認します...")
                
                # テーブル構造を取得
                cursor.execute("DESCRIBE attendance_records")
                columns = cursor.fetchall()
                
                logging.info("--- 現在のテーブル構造 ---")
                for column in columns:
                    logging.info(f"{column['Field']}: {column['Type']} {column['Null']} {column['Key']} {column['Default']} {column['Extra']}")
                
                # インデックスを確認
                cursor.execute("SHOW INDEX FROM attendance_records")
                indexes = cursor.fetchall()
                
                logging.info("--- インデックス情報 ---")
                index_dict = {}
                for idx in indexes:
                    key_name = idx['Key_name']
                    if key_name not in index_dict:
                        index_dict[key_name] = []
                    index_dict[key_name].append(idx['Column_name'])
                
                for key_name, columns in index_dict.items():
                    logging.info(f"{key_name}: Columns: {', '.join(columns)}")
                
                # 必須インデックスの確認
                required_indexes = {
                    'idx_user_date': ['user_id', 'attendance_date'],
                    'idx_attendance_date': ['attendance_date'],
                    'idx_user_status': ['user_id', 'status']
                }
                
                missing_indexes = []
                for idx_name, cols in required_indexes.items():
                    # 同等のインデックスが存在するか確認
                    found = False
                    for existing_idx, existing_cols in index_dict.items():
                        if set(cols) == set(existing_cols):
                            found = True
                            break
                    
                    if not found:
                        missing_indexes.append(idx_name)
                
                if missing_indexes:
                    logging.warning(f"不足しているインデックス: {missing_indexes}")
                else:
                    logging.info("すべての必須インデックスが存在します")
                
                # サンプルデータの確認
                cursor.execute("SELECT COUNT(*) as count FROM attendance_records")
                count = cursor.fetchone()['count']
                logging.info(f"テーブル内のレコード数: {count}")
                
                if count > 0:
                    cursor.execute("SELECT * FROM attendance_records LIMIT 5")
                    samples = cursor.fetchall()
                    logging.info("--- サンプルデータ ---")
                    for sample in samples:
                        logging.info(str(sample))
                else:
                    logging.warning("テーブルにデータがありません")
                
                # 重複データのチェック
                cursor.execute("""
                    SELECT user_id, attendance_date, COUNT(*) as count
                    FROM attendance_records
                    GROUP BY user_id, attendance_date
                    HAVING COUNT(*) > 1
                """)
                duplicates = cursor.fetchall()
                
                if duplicates:
                    logging.warning(f"重複データが見つかりました（{len(duplicates)}件）")
                    for dup in duplicates:
                        logging.warning(f"重複: user_id={dup['user_id']}, date={dup['attendance_date']}, count={dup['count']}")
                    
                    # 重複を解決するか確認
                    fix_duplicates = input("重複データを修正しますか？(y/n): ").strip().lower() == 'y'
                    if fix_duplicates:
                        fixed_count = 0
                        for dup in duplicates:
                            # 最新のレコードのIDを取得
                            cursor.execute("""
                                SELECT id FROM attendance_records
                                WHERE user_id = %s AND attendance_date = %s
                                ORDER BY recorded_at DESC LIMIT 1
                            """, (dup['user_id'], dup['attendance_date']))
                            latest = cursor.fetchone()
                            
                            if latest:
                                # 最新以外を削除
                                cursor.execute("""
                                    DELETE FROM attendance_records
                                    WHERE user_id = %s AND attendance_date = %s AND id != %s
                                """, (dup['user_id'], dup['attendance_date'], latest['id']))
                                fixed_count += cursor.rowcount
                        
                        conn.commit()
                        logging.info(f"{fixed_count}件の重複データを修正しました")
                else:
                    logging.info("重複データはありません")
            else:
                logging.warning("出席記録テーブルが存在しません。作成します...")
                
                # attendance_utils.pyから関数をインポート
                try:
                    from attendance_utils import ensure_attendance_records_table
                    ensure_attendance_records_table(conn)
                    logging.info("出席記録テーブルを作成しました")
                except Exception as e:
                    logging.error(f"テーブル作成エラー: {e}")
                    
                    # 基本的なテーブル構造で直接作成
                    try:
                        cursor.execute("""
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
                        logging.info("基本構造で出席記録テーブルを作成しました")
                    except Exception as create_error:
                        logging.error(f"テーブル直接作成エラー: {create_error}")
        
        conn.close()
        logging.info("チェック完了")
        
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")
        import traceback
        logging.error(traceback.format_exc())

def test_insert_record():
    """テスト用の出席レコードを挿入する"""
    try:
        conn = get_db_connection()
        
        # テスト用データ
        test_data = {
            'user_id': 999,  # テスト用ユーザーID
            'attendance_date': datetime.now().strftime('%Y-%m-%d'),
            'status': 'present',
            'recorded_by': 1  # テスト用教師ID
        }
        
        with conn.cursor() as cursor:
            # 既存レコードを確認
            cursor.execute("""
                SELECT id FROM attendance_records 
                WHERE user_id = %s AND attendance_date = %s
            """, (test_data['user_id'], test_data['attendance_date']))
            
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                cursor.execute("""
                    UPDATE attendance_records
                    SET status = %s, recorded_by = %s
                    WHERE id = %s
                """, (test_data['status'], test_data['recorded_by'], existing['id']))
                logging.info(f"既存レコードを更新しました: ID={existing['id']}")
            else:
                # 挿入
                cursor.execute("""
                    INSERT INTO attendance_records
                    (user_id, attendance_date, status, recorded_by)
                    VALUES (%s, %s, %s, %s)
                """, (
                    test_data['user_id'],
                    test_data['attendance_date'],
                    test_data['status'],
                    test_data['recorded_by']
                ))
                logging.info(f"新規レコードを挿入しました: ID={cursor.lastrowid}")
        
        conn.commit()
        conn.close()
        logging.info("テスト挿入完了")
        
    except Exception as e:
        logging.error(f"テスト挿入エラー: {e}")
        import traceback
        logging.error(traceback.format_exc())

if __name__ == "__main__":
    action = 'check'
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
    
    if action == 'check':
        logging.info("出席テーブルの構造確認を開始します")
        check_attendance_table()
    elif action == 'test':
        logging.info("テスト用レコードの挿入を開始します")
        test_insert_record()
    else:
        logging.error(f"不明なアクション: {action}")
        print("使用方法: python check_attendance_table.py [check|test]")
        print("  check: テーブル構造を確認（デフォルト）")
        print("  test: テスト用レコードを挿入")
