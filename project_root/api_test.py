#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
英語学習システムのAPIテストツール
新しく追加したAPIエンドポイントの動作確認を行います
"""

import requests
import json
from datetime import datetime

# テスト用の設定
BASE_URL = "http://localhost:5000"  # 本番環境では適切なURLに変更
API_ENDPOINTS = {
    'user_info': '/api/english/user-info',
    'detailed_stats': '/api/english/detailed-stats',
    'level_assessment': '/api/english/level-assessment',
    'generate_problems': '/api/english/generate-problems',
    'review_problems': '/api/english/review-problems',
    'learning_plan': '/api/english/learning-plan',
    'achievement_tracking': '/api/english/achievement-tracking',
    'start_session': '/api/english/start-session',
    'save_answer': '/api/english/save-answer',
    'add_points': '/api/english/add-points'
}

class EnglishLearningAPITester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_user_info_api(self):
        """ユーザー情報取得APIのテスト"""
        print("=== ユーザー情報取得APIテスト ===")
        
        try:
            response = self.session.get(f"{self.base_url}{API_ENDPOINTS['user_info']}")
            if response.status_code == 200:
                data = response.json()
                print("✅ ユーザー情報取得成功")
                print(f"データ: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print(f"❌ エラー: {response.status_code}")
                print(f"レスポンス: {response.text}")
        except Exception as e:
            print(f"❌ 例外エラー: {e}")
        print()
    
    def test_detailed_stats_api(self):
        """詳細統計情報取得APIのテスト"""
        print("=== 詳細統計情報取得APIテスト ===")
        
        try:
            response = self.session.get(f"{self.base_url}{API_ENDPOINTS['detailed_stats']}")
            if response.status_code == 200:
                data = response.json()
                print("✅ 詳細統計情報取得成功")
                print(f"全体統計: {data.get('overallStats', {})}")
                print(f"ステージ統計数: {len(data.get('stageStats', []))}")
            else:
                print(f"❌ エラー: {response.status_code}")
        except Exception as e:
            print(f"❌ 例外エラー: {e}")
        print()
    
    def test_level_assessment_api(self):
        """レベル判定APIのテスト"""
        print("=== レベル判定APIテスト ===")
        
        try:
            response = self.session.get(f"{self.base_url}{API_ENDPOINTS['level_assessment']}")
            if response.status_code == 200:
                data = response.json()
                print("✅ レベル判定成功")
                print(f"現在のレベル: {data.get('currentLevel')}")
                print(f"推奨ステージ: {data.get('recommendedStage')}")
                print(f"最近の正答率: {data.get('recentAccuracy')}%")
            else:
                print(f"❌ エラー: {response.status_code}")
        except Exception as e:
            print(f"❌ 例外エラー: {e}")
        print()
    
    def test_generate_problems_api(self):
        """問題生成APIのテスト"""
        print("=== 問題生成APIテスト ===")
        
        try:
            params = {'stage': 1, 'count': 5, 'type': 'mixed'}
            response = self.session.get(f"{self.base_url}{API_ENDPOINTS['generate_problems']}", params=params)
            if response.status_code == 200:
                data = response.json()
                print("✅ 問題生成成功")
                print(f"ステージ: {data.get('stage')}")
                print(f"基本問題数: {len(data.get('problems', {}).get('basic', []))}")
                print(f"文法問題数: {len(data.get('problems', {}).get('question', []))}")
            else:
                print(f"❌ エラー: {response.status_code}")
        except Exception as e:
            print(f"❌ 例外エラー: {e}")
        print()
    
    def test_learning_plan_api(self):
        """学習計画APIのテスト"""
        print("=== 学習計画APIテスト ===")
        
        try:
            response = self.session.get(f"{self.base_url}{API_ENDPOINTS['learning_plan']}")
            if response.status_code == 200:
                data = response.json()
                print("✅ 学習計画生成成功")
                plan = data.get('learningPlan', {})
                print(f"推奨事項数: {len(plan.get('recommendations', []))}")
                print(f"次のステージ: {plan.get('nextStage')}")
                print(f"重点分野: {plan.get('focusAreas', [])}")
            else:
                print(f"❌ エラー: {response.status_code}")
        except Exception as e:
            print(f"❌ 例外エラー: {e}")
        print()
    
    def test_achievement_tracking_api(self):
        """成果追跡APIのテスト"""
        print("=== 成果追跡APIテスト ===")
        
        try:
            response = self.session.get(f"{self.base_url}{API_ENDPOINTS['achievement_tracking']}")
            if response.status_code == 200:
                data = response.json()
                print("✅ 成果追跡成功")
                achievements = data.get('achievements', {})
                print(f"総問題数: {achievements.get('totalProblems')}")
                print(f"正答率: {achievements.get('accuracyRate'):.2f}%")
                print(f"獲得バッジ数: {len(data.get('earnedBadges', []))}")
            else:
                print(f"❌ エラー: {response.status_code}")
        except Exception as e:
            print(f"❌ 例外エラー: {e}")
        print()
    
    def test_start_session_api(self):
        """セッション開始APIのテスト"""
        print("=== セッション開始APIテスト ===")
        
        try:
            payload = {
                'student_id': 1,  # テスト用ID
                'stage': 1
            }
            response = self.session.post(f"{self.base_url}{API_ENDPOINTS['start_session']}", json=payload)
            if response.status_code == 200:
                data = response.json()
                print("✅ セッション開始成功")
                print(f"セッションID: {data.get('sessionId')}")
                return data.get('sessionId')
            else:
                print(f"❌ エラー: {response.status_code}")
                print(f"レスポンス: {response.text}")
        except Exception as e:
            print(f"❌ 例外エラー: {e}")
        print()
        return None
    
    def run_all_tests(self):
        """全てのAPIテストを実行"""
        print("=" * 50)
        print("英語学習システム APIテスト開始")
        print(f"テスト時刻: {datetime.now().isoformat()}")
        print("=" * 50)
        
        # 各APIテストを実行
        self.test_user_info_api()
        self.test_detailed_stats_api()
        self.test_level_assessment_api()
        self.test_generate_problems_api()
        self.test_learning_plan_api()
        self.test_achievement_tracking_api()
        
        # セッション関連のテスト
        session_id = self.test_start_session_api()
        
        print("=" * 50)
        print("APIテスト完了")
        print("=" * 50)

def main():
    """メイン関数"""
    print("英語学習システム APIテストツール")
    print("このツールは新しく追加されたAPIエンドポイントの動作を確認します。")
    print()
    
    # 実際のサーバーURLを確認
    server_url = input("サーバーURL (デフォルト: http://localhost:5000): ").strip()
    if not server_url:
        server_url = "http://localhost:5000"
    
    # テスト実行
    tester = EnglishLearningAPITester(server_url)
    tester.run_all_tests()

if __name__ == "__main__":
    main()
