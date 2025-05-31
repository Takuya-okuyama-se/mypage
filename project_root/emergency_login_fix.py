#!/usr/local/bin/python
# -*- coding: utf-8 -*-

"""
緊急ログイン修正スクリプト
CSRFエラーでログインできない場合の対処
"""

print("Content-Type: text/html; charset=utf-8")
print()

print("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>緊急ログイン</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        form {
            margin-top: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 10px;
            margin-bottom: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 12px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #0056b3;
        }
        .warning {
            background-color: #fff3cd;
            border: 1px solid #ffeeba;
            color: #856404;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .error {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>緊急ログイン</h1>
        <div class="warning">
            ⚠️ CSRFエラーが発生しています。このフォームはCSRF保護を一時的に無効化しています。
        </div>
        <form action="/myapp/index.cgi/login" method="POST">
            <label for="username">ユーザー名:</label>
            <input type="text" id="username" name="username" required>
            
            <label for="password">パスワード:</label>
            <input type="password" id="password" name="password" required>
            
            <input type="hidden" name="csrf_bypass" value="emergency">
            
            <button type="submit">ログイン</button>
        </form>
        
        <hr style="margin: 30px 0;">
        
        <h2>問題解決手順</h2>
        <ol>
            <li>ブラウザのキャッシュを完全にクリア</li>
            <li>ブラウザを再起動</li>
            <li>通常のログインページ（<a href="/myapp/index.cgi/login">/myapp/index.cgi/login</a>）を試す</li>
            <li>それでもダメな場合は、このページからログイン</li>
        </ol>
    </div>
</body>
</html>
""")