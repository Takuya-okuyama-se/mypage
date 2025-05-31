# 英語学習システム API ドキュメント

## 概要
英語学習システムのバックエンドAPIエンドポイントの詳細仕様書です。  
このドキュメントでは、新しく実装されたAPIエンドポイントについて説明します。

## 認証
全てのAPIエンドポイントは、有効なセッションが必要です。  
認証されていない場合は、`401 Unauthorized` エラーが返されます。

## エンドポイント一覧

### 1. ユーザー情報取得
**エンドポイント:** `GET /api/english/user-info`  
**説明:** 英語学習用のユーザー情報とポイントを取得します。

**レスポンス例:**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "name": "田中太郎",
    "grade_level": 3,
    "class_name": "3年A組"
  },
  "currentPoints": 150
}
```

### 2. 詳細統計情報取得
**エンドポイント:** `GET /api/english/detailed-stats`  
**説明:** 英語学習の詳細統計情報を取得します。

**レスポンス例:**
```json
{
  "success": true,
  "overallStats": {
    "totalSessions": 15,
    "totalProblems": 120,
    "correctAnswers": 96,
    "accuracyRate": 80.0,
    "highestStage": 3,
    "currentStreak": 5
  },
  "stageStats": [
    {
      "stage": 1,
      "problems_count": 40,
      "correct_count": 35,
      "accuracy": 87.5
    }
  ],
  "recentActivity": [
    {
      "study_date": "2024-01-15",
      "problems_solved": 8,
      "correct_count": 7
    }
  ]
}
```

### 3. レベル判定
**エンドポイント:** `GET /api/english/level-assessment`  
**説明:** 現在の英語学習レベルを判定します。

**レスポンス例:**
```json
{
  "success": true,
  "currentLevel": "中級",
  "recentAccuracy": 78.5,
  "recommendedStage": 3,
  "recommendations": [
    "文法問題にも挑戦してみましょう",
    "間違えた問題を復習しましょう"
  ]
}
```

### 4. 問題生成
**エンドポイント:** `GET /api/english/generate-problems`  
**説明:** ステージに応じた英語学習問題を動的に生成します。

**パラメータ:**
- `stage` (int): ステージ番号 (デフォルト: 1)
- `count` (int): 問題数 (デフォルト: 10)
- `type` (string): 問題タイプ ('basic', 'question', 'mixed') (デフォルト: 'basic')

**レスポンス例:**
```json
{
  "success": true,
  "stage": 1,
  "problems": {
    "basic": [
      {
        "id": 0,
        "japanese": "学生",
        "answer": ["student"],
        "hint": "studentを英語で書いてください"
      }
    ],
    "question": [
      {
        "id": 0,
        "japanese": "私は学生です。",
        "answer": ["I", "am", "a", "student"],
        "hint": "be動詞を使った文です"
      }
    ]
  },
  "totalProblems": 2
}
```

### 5. 復習問題取得
**エンドポイント:** `GET /api/english/review-problems`  
**説明:** 間違えた問題の復習用問題を生成します。

**レスポンス例:**
```json
{
  "success": true,
  "reviewProblems": [
    {
      "id": 0,
      "type": "basic",
      "japanese": "学校",
      "correct_answer": ["school"],
      "error_count": 3,
      "hint": "この問題は3回間違えています。復習しましょう。"
    }
  ],
  "totalReviewProblems": 1,
  "message": "1個の復習問題があります"
}
```

### 6. 学習計画取得
**エンドポイント:** `GET /api/english/learning-plan`  
**説明:** 個人に最適化された学習計画を提供します。

**レスポンス例:**
```json
{
  "success": true,
  "learningPlan": {
    "recommendations": [
      "良いペースで学習できています。現在のステージを完璧にしましょう。"
    ],
    "nextStage": 2,
    "focusAreas": ["基本文法の定着", "語彙の復習"],
    "weeklyGoals": ["現在のステージで30問以上解く", "正答率75%以上を目指す"],
    "studySchedule": ["2日に1回の学習", "15分程度の集中学習"]
  }
}
```

### 7. 成果追跡
**エンドポイント:** `GET /api/english/achievement-tracking`  
**説明:** 学習成果とバッジシステムを管理します。

**レスポンス例:**
```json
{
  "success": true,
  "achievements": {
    "totalProblems": 120,
    "correctAnswers": 96,
    "accuracyRate": 80.0,
    "studyDays": 12,
    "currentStreak": 5
  },
  "earnedBadges": [
    {
      "id": "first_steps",
      "name": "初めの一歩",
      "earnedAt": "2024-01-15T10:30:00Z",
      "points": 10
    }
  ],
  "nextBadges": [
    {
      "name": "問題解決者",
      "requirement": "あと30問解く",
      "progress": 60.0
    }
  ]
}
```

### 8. セッション開始
**エンドポイント:** `POST /api/english/start-session`  
**説明:** 英語学習セッションを開始します。

**リクエストボディ:**
```json
{
  "student_id": 1,
  "stage": 1
}
```

**レスポンス例:**
```json
{
  "success": true,
  "sessionId": 123,
  "message": "セッションを開始しました"
}
```

### 9. 回答保存
**エンドポイント:** `POST /api/english/save-answer`  
**説明:** 英語学習の回答を保存します。

**リクエストボディ:**
```json
{
  "student_id": 1,
  "stage": 1,
  "problem_type": "basic",
  "question_id": 0,
  "japanese_text": "学生",
  "correct_answer": "student",
  "user_answer": "student",
  "handwriting_data": {},
  "is_correct": true
}
```

### 10. ポイント追加
**エンドポイント:** `POST /api/english/add-points`  
**説明:** 英語学習でのポイントを追加します。

**リクエストボディ:**
```json
{
  "userId": 1,
  "points": 10,
  "eventType": "english_practice",
  "comment": "英語学習"
}
```

### 11. 手書き認識
**エンドポイント:** `POST /api/english/recognize`  
**説明:** 手書き文字をGoogle Cloud Vision APIで認識します。

**リクエストボディ:**
```json
{
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

**レスポンス例:**
```json
{
  "success": true,
  "text": "student",
  "raw_text": "student",
  "confidence": 0.95
}
```

## エラーレスポンス

全てのエラーレスポンスは以下の形式で返されます：

```json
{
  "success": false,
  "message": "エラーメッセージ"
}
```

### 一般的なエラーコード
- `401 Unauthorized`: 認証エラー
- `403 Forbidden`: 権限エラー
- `400 Bad Request`: リクエストパラメータエラー
- `404 Not Found`: リソースが見つからない
- `500 Internal Server Error`: サーバー内部エラー

## 利用例

### JavaScript (フロントエンド)
```javascript
// ユーザー情報を取得
async function getUserInfo() {
  try {
    const response = await fetch('/api/english/user-info');
    const data = await response.json();
    if (data.success) {
      console.log('ユーザー情報:', data.user);
      console.log('現在のポイント:', data.currentPoints);
    }
  } catch (error) {
    console.error('エラー:', error);
  }
}

// 問題を生成
async function generateProblems(stage = 1) {
  try {
    const response = await fetch(`/api/english/generate-problems?stage=${stage}&type=mixed`);
    const data = await response.json();
    if (data.success) {
      console.log('生成された問題:', data.problems);
    }
  } catch (error) {
    console.error('エラー:', error);
  }
}

// セッションを開始
async function startSession(studentId, stage) {
  try {
    const response = await fetch('/api/english/start-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: studentId, stage: stage })
    });
    const data = await response.json();
    if (data.success) {
      return data.sessionId;
    }
  } catch (error) {
    console.error('エラー:', error);
  }
}
```

## 注意事項

1. **レート制限**: APIへの過度なリクエストを避けてください。
2. **セッション管理**: セッションの有効期限に注意してください。
3. **データ形式**: 日本語文字列はUTF-8エンコーディングで送信してください。
4. **画像データ**: 手書き認識APIでは、base64エンコードされた画像データを送信してください。

## サポート

APIに関する質問や問題がある場合は、開発チームまでお問い合わせください。
