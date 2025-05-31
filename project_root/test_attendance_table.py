from attendance_utils import ensure_attendance_records_table
from app import get_db_connection

# データベース接続を取得
conn = get_db_connection()

# 出席記録テーブルの確認・修正
ensure_attendance_records_table(conn)

# 接続をクローズ
conn.close()

print('テスト完了：出席記録テーブルの確認が正常に行われました')
