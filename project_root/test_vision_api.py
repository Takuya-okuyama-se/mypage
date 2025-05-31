#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Cloud Vision API接続テストスクリプト
本番環境での動作確認用
"""

import os
import base64
import requests
import json
from PIL import Image, ImageDraw, ImageFont
import io

# 環境変数を手動で読み込み
def load_env_file():
    """手動で.envファイルを読み込む"""
    try:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
    except Exception:
        pass

# 環境変数を読み込み
load_env_file()

def create_test_image():
    """テスト用の手書き文字画像を生成"""
    # 100x100の白い背景画像を作成
    img = Image.new('RGB', (100, 100), 'white')
    draw = ImageDraw.Draw(img)
    
    # 簡単な「I」の文字を描画
    draw.rectangle([45, 20, 55, 80], fill='black')  # 縦線
    draw.rectangle([35, 20, 65, 28], fill='black')  # 上の横線
    draw.rectangle([35, 72, 65, 80], fill='black')  # 下の横線
    
    # Base64エンコード
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_data = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_data}"

def test_vision_api():
    """Google Cloud Vision APIのテスト"""
    # APIキーを取得
    api_key = os.getenv('GOOGLE_CLOUD_VISION_API_KEY')
    
    if not api_key:
        print("❌ GOOGLE_CLOUD_VISION_API_KEY が設定されていません")
        return False
    
    print(f"✅ APIキー: {api_key[:10]}...")
    
    # テスト画像を作成
    test_image = create_test_image()
    image_data = test_image.split(',')[1]  # data:image/png;base64, の部分を削除
    
    # Vision API リクエスト
    vision_url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    
    vision_request = {
        "requests": [
            {
                "image": {
                    "content": image_data
                },
                "features": [
                    {
                        "type": "TEXT_DETECTION",
                        "maxResults": 3
                    }
                ]
            }
        ]
    }
    
    try:
        print("🔍 Google Cloud Vision APIにリクエスト送信中...")
        response = requests.post(vision_url, json=vision_request, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API呼び出し成功")
            print(f"📝 レスポンス: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # テキスト認識結果を確認
            if 'responses' in result and len(result['responses']) > 0:
                text_annotations = result['responses'][0].get('textAnnotations', [])
                
                if text_annotations:
                    recognized_text = text_annotations[0].get('description', '').strip()
                    confidence = text_annotations[0].get('score', 0)
                    print(f"🎯 認識結果: '{recognized_text}' (信頼度: {confidence})")
                    return True
                else:
                    print("⚠️ テキストが認識されませんでした")
                    return True  # APIは動作しているが認識なし
            else:
                print("⚠️ レスポンスが空です")
                return False
        else:
            print(f"❌ APIエラー: {response.status_code}")
            print(f"エラー詳細: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ APIタイムアウト")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ ネットワークエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False

def test_local_endpoint():
    """ローカルのFlaskエンドポイントをテスト"""
    # テスト画像を作成
    test_image = create_test_image()
    
    test_data = {
        "image": test_image
    }
    
    try:
        print("🔍 ローカルエンドポイント /api/english/recognize をテスト中...")
        
        # ローカルサーバーにリクエスト（開発環境）
        response = requests.post(
            'http://localhost:5000/api/english/recognize',
            json=test_data,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ ローカルエンドポイント動作確認")
            print(f"📝 レスポンス: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"❌ ローカルエンドポイントエラー: {response.status_code}")
            print(f"エラー詳細: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("⚠️ ローカルサーバーが起動していません")
        return False
    except Exception as e:
        print(f"❌ ローカルエンドポイントテストエラー: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Google Cloud Vision API 本番環境テスト")
    print("=" * 60)
    
    # 1. 直接Vision APIテスト
    print("\n1. 直接Vision APIテスト")
    print("-" * 30)
    api_test_result = test_vision_api()
    
    # 2. ローカルエンドポイントテスト
    print("\n2. ローカルエンドポイントテスト")
    print("-" * 30)
    local_test_result = test_local_endpoint()
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    print(f"Vision API直接呼び出し: {'✅ 成功' if api_test_result else '❌ 失敗'}")
    print(f"ローカルエンドポイント: {'✅ 成功' if local_test_result else '❌ 失敗'}")
    
    if api_test_result and local_test_result:
        print("\n🎉 すべてのテストが成功しました！本番環境でも正常に動作するはずです。")
    elif api_test_result:
        print("\n⚠️ Vision APIは動作していますが、ローカルサーバーに問題があります。")
    else:
        print("\n❌ Vision APIに問題があります。APIキーや設定を確認してください。")
