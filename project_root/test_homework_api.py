#!/usr/bin/env python3
"""
宿題カレンダーAPIのテストスクリプト
"""
import requests
import json

def test_homework_calendar_api():
    """宿題カレンダーAPIをテストする"""
    
    # APIのベースURL
    base_url = "http://localhost/myapp/index.cgi"
    
    # テスト用のパラメータ
    params = {
        'student_id': 33,  # サンプルデータの生徒ID
        'year': 2024,
        'month': 12
    }
    
    try:
        print("宿題カレンダーAPIをテスト中...")
        print(f"URL: {base_url}/api/teacher/homework/calendar")
        print(f"パラメータ: {params}")
        
        # APIにリクエストを送信
        response = requests.get(
            f"{base_url}/api/teacher/homework/calendar",
            params=params,
            timeout=10
        )
        
        print(f"\nレスポンス ステータスコード: {response.status_code}")
        print(f"レスポンス ヘッダー: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"\nレスポンス JSON:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                if data.get('success'):
                    homework_count = len(data.get('homework', []))
                    print(f"\n✅ 成功: {homework_count}件の宿題データを取得")
                    
                    if homework_count > 0:
                        print("\n宿題データの詳細:")
                        for i, hw in enumerate(data['homework'][:3]):  # 最初の3件のみ表示
                            print(f"  {i+1}. 日付: {hw.get('assigned_date')}, 科目: {hw.get('subject')}, 完了状態: {hw.get('completed')}")
                    else:
                        print("⚠️  宿題データが0件です")
                else:
                    print(f"❌ APIエラー: {data.get('message')}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析エラー: {e}")
                print(f"レスポンス本文: {response.text[:500]}...")
        else:
            print(f"❌ HTTPエラー: {response.status_code}")
            print(f"レスポンス本文: {response.text[:500]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ リクエストエラー: {e}")
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")

if __name__ == "__main__":
    test_homework_calendar_api()
