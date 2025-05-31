import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

connection = pymysql.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'seishinn_test'),
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

with connection.cursor() as cursor:
    cursor.execute('DESCRIBE homework_assignments')
    columns = cursor.fetchall()
    print('homework_assignmentsテーブルの構造:')
    for col in columns:
        print(f'  {col["Field"]}: {col["Type"]}')

connection.close()
