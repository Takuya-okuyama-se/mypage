#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

def fix_grade_improvement_records():
    """
    point_historyテーブル内の「grade_improvement」レコードを
    適切なイベントタイプに修正する
    """
    print('=== データベース接続を開始します ===')
    try:        # 環境変数の確認
        db_host = os.getenv('MYSQL_HOST', 'localhost')
        db_user = os.getenv('MYSQL_USER', 'root')
        db_name = os.getenv('MYSQL_DB', 'juku_management')
        
        print(f'接続先: {db_host}, データベース: {db_name}, ユーザー: {db_user}')
        
        conn = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=db_name,
            charset='utf8mb4'
        )
        
        print('データベース接続に成功しました。')
        
        cursor = conn.cursor(dictionary=True)
        
        # まず「grade_improvement」レコードの有無を確認
        print('=== grade_improvementレコードの確認 ===')
        cursor.execute('''
            SELECT id, student_id, points, event_type, event_description, created_at 
            FROM point_history 
            WHERE event_type = 'grade_improvement'
            ORDER BY created_at DESC
        ''')
        
        records = cursor.fetchall()
        
        if not records:
            print('grade_improvementのレコードは見つかりませんでした。')
            cursor.close()
            conn.close()
            return
        
        print(f'grade_improvementのレコードが{len(records)}件見つかりました：')
        for record in records:
            print(f'ID: {record["id"]}, 生徒ID: {record["student_id"]}, '
                  f'ポイント: {record["points"]}, 説明: {record.get("event_description", "なし")}, '
                  f'作成日: {record["created_at"]}')
        
        # 修正の提案
        print('\n=== 修正の提案 ===')
        for record in records:
            points = record["points"]
            if points >= 50:
                suggested_type = "grade_improvement_large"
                suggested_name = "成績向上ボーナス(大)"
            elif points >= 30:
                suggested_type = "grade_improvement_medium"
                suggested_name = "成績向上ボーナス(中)"
            else:
                suggested_type = "grade_improvement_small"
                suggested_name = "成績向上ボーナス(小)"
            
            print(f'レコードID {record["id"]}: {points}ポイント → {suggested_type} ({suggested_name})')
        
        # 実際の修正を実行するかユーザーに確認
        print('\n修正を実行しますか？ (y/n): ', end='')
        response = input().strip().lower()
        
        if response == 'y':
            print('\n=== 修正実行中 ===')
            updated_count = 0
            
            for record in records:
                points = record["points"]
                if points >= 50:
                    new_type = "grade_improvement_large"
                elif points >= 30:
                    new_type = "grade_improvement_medium"
                else:
                    new_type = "grade_improvement_small"
                
                cursor.execute('''
                    UPDATE point_history 
                    SET event_type = %s 
                    WHERE id = %s
                ''', (new_type, record["id"]))
                
                updated_count += 1
                print(f'レコードID {record["id"]} を {new_type} に更新')
            
            conn.commit()
            print(f'\n{updated_count}件のレコードを正常に更新しました。')
        else:
            print('修正をキャンセルしました。')
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as db_error:
        print(f'データベースエラーが発生しました: {db_error}')
    except ImportError as import_error:
        print(f'モジュールのインポートエラー: {import_error}')
        print('mysql-connector-pythonがインストールされていない可能性があります。')
        print('pip install mysql-connector-python で インストールしてください。')
    except Exception as e:
        print(f'予期しないエラーが発生しました: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_grade_improvement_records()
