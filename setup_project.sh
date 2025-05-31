#!/bin/bash
# setup_project.sh
# プロジェクトのディレクトリと主要なファイルを一括で作成するスクリプト

# プロジェクトのルートディレクトリを作成
mkdir -p project_root/templates
mkdir -p project_root/static

#############################
# app.py の作成
#############################
cat <<'EOF' > project_root/app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'YOUR_SECRET_KEY'  # 本番環境では安全な方法で管理してください

# MySQLの接続設定（さくらインターネットの情報に合わせて更新）
app.config['MYSQL_HOST'] = 'db_host_name'
app.config['MYSQL_USER'] = 'db_user_name'
app.config['MYSQL_PASSWORD'] = 'db_password'
app.config['MYSQL_DB'] = 'db_database_name'

mysql = MySQL(app)

# ------------- ユーザー認証系 ------------- #

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username and password:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            account = cursor.fetchone()
            if account and check_password_hash(account['password'], password):
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                session['role'] = account['role']
                if account['role'] == 'teacher':
                    return redirect(url_for('teacher_dashboard'))
                else:
                    return redirect(url_for('student_dashboard'))
            else:
                msg = 'ユーザ名かパスワードが違います'
        else:
            msg = 'ユーザ名とパスワードを入力してください'
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

# ------------- 生徒用機能 ------------- #

@app.route('/student')
def student_dashboard():
    if not session.get('loggedin'):
        return redirect(url_for('login'))
    if session.get('role') != 'student':
        return abort(403)
    student_id = session['id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT term, subject, grade FROM internal_grades WHERE student_id = %s ORDER BY term, subject', (student_id,))
    grades = cursor.fetchall()
    cursor.execute('SELECT term, subject, score FROM exam_scores WHERE student_id = %s ORDER BY term, subject', (student_id,))
    scores = cursor.fetchall()
    cursor.execute('SELECT term, AVG(score) AS avg_score FROM exam_scores WHERE student_id = %s GROUP BY term ORDER BY term', (student_id,))
    avg_data = cursor.fetchall()
    labels = [f"学期{row['term']}" for row in avg_data]
    values = [float(row['avg_score']) for row in avg_data]
    cursor.execute('SELECT message, created_at, (SELECT name FROM users WHERE id = teacher_id) as teacher_name FROM notifications WHERE student_id = %s ORDER BY created_at DESC', (student_id,))
    notices = cursor.fetchall()
    return render_template('student_dashboard.html', grades=grades, scores=scores, labels=labels, values=values, notices=notices)

# 生徒自身が点数や内申点を入力・更新できるルート
@app.route('/student/edit_scores', methods=['GET', 'POST'])
def student_edit_scores():
    if not session.get('loggedin') or session.get('role') != 'student':
        return abort(403)
    student_id = session['id']
    msg_exam = ''
    msg_internal = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        # 期末試験点数のフォーム
        if 'score_submit' in request.form:
            subject = request.form.get('subject_exam')
            term = request.form.get('term_exam')
            score = request.form.get('score')
            if subject and term and score:
                cursor.execute('SELECT id FROM exam_scores WHERE student_id = %s AND subject = %s AND term = %s',
                               (student_id, subject, term))
                existing = cursor.fetchone()
                if existing:
                    cursor.execute('UPDATE exam_scores SET score = %s WHERE id = %s',
                                   (score, existing['id']))
                    msg_exam = f"{term}学期の{subject}の点数を更新しました。"
                else:
                    cursor.execute('INSERT INTO exam_scores (student_id, subject, term, score) VALUES (%s, %s, %s, %s)',
                                   (student_id, subject, term, score))
                    msg_exam = f"{term}学期の{subject}の点数を登録しました。"
                mysql.connection.commit()
        # 内申点のフォーム
        elif 'grade_submit' in request.form:
            subject = request.form.get('subject_grade')
            term = request.form.get('term_grade')
            grade = request.form.get('grade')
            if subject and term and grade:
                cursor.execute('SELECT id FROM internal_grades WHERE student_id = %s AND subject = %s AND term = %s',
                               (student_id, subject, term))
                existing = cursor.fetchone()
                if existing:
                    cursor.execute('UPDATE internal_grades SET grade = %s WHERE id = %s',
                                   (grade, existing['id']))
                    msg_internal = f"{term}学期の{subject}の内申点を更新しました。"
                else:
                    cursor.execute('INSERT INTO internal_grades (student_id, subject, term, grade) VALUES (%s, %s, %s, %s)',
                                   (student_id, subject, term, grade))
                    msg_internal = f"{term}学期の{subject}の内申点を登録しました。"
                mysql.connection.commit()
    cursor.execute('SELECT term, subject, score FROM exam_scores WHERE student_id = %s ORDER BY term, subject', (student_id,))
    scores = cursor.fetchall()
    cursor.execute('SELECT term, subject, grade FROM internal_grades WHERE student_id = %s ORDER BY term, subject', (student_id,))
    grades = cursor.fetchall()
    return render_template('student_edit_scores.html',
                           msg_exam=msg_exam, msg_internal=msg_internal, scores=scores, grades=grades)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('loggedin'):
        return redirect(url_for('login'))
    user_id = session['id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT username, name, email FROM users WHERE id = %s', (user_id,))
    account = cursor.fetchone()
    if request.method == 'POST':
        new_name = request.form.get('name')
        new_email = request.form.get('email')
        new_password = request.form.get('password')
        if new_name and new_email:
            if new_password:
                hashed_pw = generate_password_hash(new_password)
                cursor.execute('UPDATE users SET name=%s, email=%s, password=%s WHERE id=%s',
                               (new_name, new_email, hashed_pw, user_id))
            else:
                cursor.execute('UPDATE users SET name=%s, email=%s WHERE id=%s',
                               (new_name, new_email, user_id))
            mysql.connection.commit()
            flash('プロフィールを更新しました。')
            return redirect(url_for('profile'))
        else:
            flash('名前とメールアドレスは必須です。')
            return redirect(url_for('profile'))
    return render_template('profile.html', account=account)

# ------------- 講師用機能 ------------- #

@app.route('/teacher')
def teacher_dashboard():
    if not session.get('loggedin'):
        return redirect(url_for('login'))
    if session.get('role') != 'teacher':
        return abort(403)
    return render_template('teacher_dashboard.html')

# 生徒の試験点数入力（講師が入力する既存の例）
@app.route('/teacher/add_score', methods=['GET', 'POST'])
def teacher_add_score():
    if not session.get('loggedin') or session.get('role') != 'teacher':
        return abort(403)
    msg = ''
    if request.method == 'POST':
        student_username = request.form.get('student_username')
        subject = request.form.get('subject')
        term = request.form.get('term')
        score = request.form.get('score')
        if student_username and subject and term and score:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT id FROM users WHERE username = %s AND role = %s', (student_username, 'student'))
            student = cursor.fetchone()
            if student:
                cursor.execute('SELECT id FROM exam_scores WHERE student_id=%s AND subject=%s AND term=%s',
                               (student['id'], subject, term))
                existing = cursor.fetchone()
                if existing:
                    cursor.execute('UPDATE exam_scores SET score=%s WHERE id=%s', (score, existing['id']))
                else:
                    cursor.execute('INSERT INTO exam_scores (student_id, subject, term, score) VALUES (%s, %s, %s, %s)',
                                   (student['id'], subject, term, score))
                mysql.connection.commit()
                msg = f"「{student_username}」さんの{term}学期「{subject}」の点数を登録しました。"
            else:
                msg = "指定されたユーザー名の生徒が見つかりません。"
        else:
            msg = "全ての項目を入力してください。"
    return render_template('teacher_add_score.html', msg=msg)

# 講師から通知送信
@app.route('/teacher/notify', methods=['GET', 'POST'])
def teacher_notify():
    if not session.get('loggedin') or session.get('role') != 'teacher':
        return abort(403)
    msg = ''
    if request.method == 'POST':
        student_username = request.form.get('student_username')
        message = request.form.get('message')
        if student_username and message:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT id FROM users WHERE username = %s AND role = %s', (student_username, 'student'))
            student = cursor.fetchone()
            if student:
                cursor.execute('INSERT INTO notifications (student_id, teacher_id, message) VALUES (%s, %s, %s)',
                               (student['id'], session['id'], message))
                mysql.connection.commit()
                msg = f"「{student_username}」さんへ通知を送りました。"
            else:
                msg = "指定されたユーザー名の生徒が見つかりません。"
        else:
            msg = "生徒のユーザー名とメッセージ内容を入力してください。"
    return render_template('teacher_notify.html', msg=msg)

# 講師側：生徒一覧表示
@app.route('/teacher/students')
def teacher_students():
    if not session.get('loggedin') or session.get('role') != 'teacher':
        return abort(403)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, username, name, email FROM users WHERE role = 'student' ORDER BY name")
    students = cursor.fetchall()
    return render_template('teacher_students.html', students=students)

# 講師側：各生徒の詳細確認画面
@app.route('/teacher/student/<int:student_id>')
def teacher_student_detail(student_id):
    if not session.get('loggedin') or session.get('role') != 'teacher':
        return abort(403)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, username, name, email FROM users WHERE id = %s AND role = 'student'", (student_id,))
    student = cursor.fetchone()
    if not student:
        flash('生徒が見つかりません。')
        return redirect(url_for('teacher_students'))
    cursor.execute('SELECT term, subject, score FROM exam_scores WHERE student_id = %s ORDER BY term, subject', (student_id,))
    scores = cursor.fetchall()
    cursor.execute('SELECT term, subject, grade FROM internal_grades WHERE student_id = %s ORDER BY term, subject', (student_id,))
    grades = cursor.fetchall()
    return render_template('teacher_student_detail.html', student=student, scores=scores, grades=grades)

# 講師側：個別生徒の成績編集
@app.route('/teacher/edit_student/<int:student_id>', methods=['GET','POST'])
def teacher_edit_student(student_id):
    if not session.get('loggedin') or session.get('role') != 'teacher':
        return abort(403)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, username, name FROM users WHERE id = %s AND role = 'student'", (student_id,))
    student = cursor.fetchone()
    if not student:
        flash("指定した生徒が見つかりません。")
        return redirect(url_for('teacher_students'))
    msg_exam = ''
    msg_internal = ''
    if request.method == 'POST':
        if 'score_submit' in request.form:
            subject = request.form.get('subject_exam')
            term = request.form.get('term_exam')
            score = request.form.get('score')
            if subject and term and score:
                cursor.execute('SELECT id FROM exam_scores WHERE student_id = %s AND subject = %s AND term = %s', (student_id, subject, term))
                existing = cursor.fetchone()
                if existing:
                    cursor.execute('UPDATE exam_scores SET score=%s WHERE id=%s',(score, existing['id']))
                    msg_exam = f"{term}学期の{subject}の点数を更新しました。"
                else:
                    cursor.execute('INSERT INTO exam_scores (student_id, subject, term, score) VALUES (%s, %s, %s, %s)',(student_id, subject, term, score))
                    msg_exam = f"{term}学期の{subject}の点数を登録しました。"
                mysql.connection.commit()
        elif 'grade_submit' in request.form:
            subject = request.form.get('subject_grade')
            term = request.form.get('term_grade')
            grade = request.form.get('grade')
            if subject and term and grade:
                cursor.execute('SELECT id FROM internal_grades WHERE student_id = %s AND subject = %s AND term = %s', (student_id, subject, term))
                existing = cursor.fetchone()
                if existing:
                    cursor.execute('UPDATE internal_grades SET grade=%s WHERE id=%s',(grade, existing['id']))
                    msg_internal = f"{term}学期の{subject}の内申点を更新しました。"
                else:
                    cursor.execute('INSERT INTO internal_grades (student_id, subject, term, grade) VALUES (%s, %s, %s, %s)',(student_id, subject, term, grade))
                    msg_internal = f"{term}学期の{subject}の内申点を登録しました。"
                mysql.connection.commit()
    return render_template('teacher_edit_student.html', student=student, msg_exam=msg_exam, msg_internal=msg_internal)

# 講師側：新規生徒追加
@app.route('/teacher/add_student', methods=['GET', 'POST'])
def teacher_add_student():
    if not session.get('loggedin') or session.get('role') != 'teacher':
        return abort(403)
    msg = ''
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        if username and name and email and password:
            hashed_pw = generate_password_hash(password)
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                msg = "このユーザー名は既に使用されています。"
            else:
                cursor.execute("INSERT INTO users (username, name, email, password, role) VALUES (%s, %s, %s, %s, %s)",
                               (username, name, email, hashed_pw, 'student'))
                mysql.connection.commit()
                msg = f"生徒「{name}」を追加しました。"
        else:
            msg = "全ての項目を入力してください。"
    return render_template('teacher_add_student.html', msg=msg)

if __name__ == '__main__':
    app.run(debug=True)
EOF

#############################
# templates/login.html の作成
#############################
cat <<'EOF' > project_root/templates/login.html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>ログイン | 学習サイト</title>
  <!-- Bootstrap CSS -->
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body class="bg-light">
<div class="container" style="max-width:400px; margin-top:100px;">
  <div class="card p-4">
    <h3 class="text-center">ログイン</h3>
    {% if msg %}
      <div class="alert alert-danger" role="alert">{{ msg }}</div>
    {% endif %}
    <form action="{{ url_for('login') }}" method="post">
      <div class="form-group">
        <label for="username">ユーザー名</label>
        <input type="text" name="username" id="username" class="form-control" required>
      </div>
      <div class="form-group">
        <label for="password">パスワード</label>
        <input type="password" name="password" id="password" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary btn-block">ログイン</button>
    </form>
  </div>
</div>
</body>
</html>
EOF

#############################
# templates/student_dashboard.html の作成
#############################
cat <<'EOF' > project_root/templates/student_dashboard.html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>生徒ダッシュボード</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
</head>
<body class="bg-white">
<div class="container my-4">
  <h2>{{ session['username'] }}さんのダッシュボード</h2>
  <hr>
  <h5>内申（学期ごとの評価）</h5>
  {% if grades %}
    {% set current_term = None %}
    <ul class="list-unstyled">
    {% for g in grades %}
      {% if current_term != g['term'] %}
        {% set current_term = g['term'] %}
        <li><strong>学期{{ current_term }}</strong></li>
      {% endif %}
      <li>・{{ g['subject'] }}: 評価{{ g['grade'] }}</li>
    {% endfor %}
    </ul>
  {% else %}
    <p>内申データがありません。</p>
  {% endif %}
  <h5>期末試験の点数</h5>
  {% if scores %}
    {% set current_term = None %}
    <ul class="list-unstyled">
    {% for s in scores %}
      {% if current_term != s['term'] %}
        {% set current_term = s['term'] %}
        <li><strong>学期{{ current_term }}</strong></li>
      {% endif %}
      <li>・{{ s['subject'] }}: {{ s['score'] }}点</li>
    {% endfor %}
    </ul>
  {% else %}
    <p>試験点数のデータがありません。</p>
  {% endif %}
  <h5>学期ごとの平均点推移</h5>
  <canvas id="scoreChart" width="400" height="200"></canvas>
  <script>
    const labels = {{ labels|tojson }};
    const data = {{ values|tojson }};
    const ctx = document.getElementById('scoreChart').getContext('2d');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: '平均点',
          data: data,
          borderColor: 'rgba(75, 192, 192, 1)',
          fill: false,
          tension: 0.1
        }]
      }
    });
  </script>
  <h5 class="mt-4">通知・コメント</h5>
  {% if notices %}
    <ul class="list-group">
      {% for note in notices %}
      <li class="list-group-item">
        <small class="text-muted float-right">{{ note['created_at'] }}</small>
        <p class="mb-1"><strong>{{ note['teacher_name'] }} 先生より:</strong></p>
        <p class="mb-0">{{ note['message'] }}</p>
      </li>
      {% endfor %}
    </ul>
  {% else %}
    <p>新着通知はありません。</p>
  {% endif %}
  <hr>
  <a href="{{ url_for('profile') }}">プロフィール編集</a> |
  <a href="{{ url_for('logout') }}">ログアウト</a>
</div>
</body>
</html>
EOF

#############################
# templates/student_edit_scores.html の作成
#############################
cat <<'EOF' > project_root/templates/student_edit_scores.html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>成績入力・更新（生徒）</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container my-4">
  <h3>成績の入力／更新</h3>
  <p><a href="{{ url_for('student_dashboard') }}">ダッシュボードに戻る</a></p>
  <hr>
  <h5>期末試験点数の入力／更新</h5>
  {% if msg_exam %}
    <div class="alert alert-info">{{ msg_exam }}</div>
  {% endif %}
  <form method="post" action="{{ url_for('student_edit_scores') }}">
    <input type="hidden" name="score_submit" value="1">
    <div class="form-group">
      <label>教科</label>
      <input type="text" name="subject_exam" class="form-control" required>
    </div>
    <div class="form-group">
      <label>学期</label>
      <select name="term_exam" class="form-control" required>
        <option value="">--選択--</option>
        <option value="1">1学期</option>
        <option value="2">2学期</option>
        <option value="3">3学期</option>
      </select>
    </div>
    <div class="form-group">
      <label>点数</label>
      <input type="number" name="score" class="form-control" min="0" max="100" required>
    </div>
    <button type="submit" class="btn btn-primary">登録／更新</button>
  </form>
  <hr>
  <h5>内申点の入力／更新</h5>
  {% if msg_internal %}
    <div class="alert alert-info">{{ msg_internal }}</div>
  {% endif %}
  <form method="post" action="{{ url_for('student_edit_scores') }}">
    <input type="hidden" name="grade_submit" value="1">
    <div class="form-group">
      <label>教科</label>
      <input type="text" name="subject_grade" class="form-control" required>
    </div>
    <div class="form-group">
      <label>学期</label>
      <select name="term_grade" class="form-control" required>
        <option value="">--選択--</option>
        <option value="1">1学期</option>
        <option value="2">2学期</option>
        <option value="3">3学期</option>
      </select>
    </div>
    <div class="form-group">
      <label>内申点（1～5）</label>
      <input type="number" name="grade" class="form-control" min="1" max="5" required>
    </div>
    <button type="submit" class="btn btn-primary">登録／更新</button>
  </form>
  <hr>
  <h5>現在の期末試験点数一覧</h5>
  {% if scores %}
    <ul class="list-group">
      {% for s in scores %}
        <li class="list-group-item">学期{{ s['term'] }} – {{ s['subject'] }}：{{ s['score'] }}点</li>
      {% endfor %}
    </ul>
  {% else %}
    <p>入力された試験点数はありません。</p>
  {% endif %}
  <hr>
  <h5>現在の内申点一覧</h5>
  {% if grades %}
    <ul class="list-group">
      {% for g in grades %}
        <li class="list-group-item">学期{{ g['term'] }} – {{ g['subject'] }}：評価{{ g['grade'] }}</li>
      {% endfor %}
    </ul>
  {% else %}
    <p>入力された内申点はありません。</p>
  {% endif %}
</div>
</body>
</html>
EOF

#############################
# templates/teacher_dashboard.html の作成
#############################
cat <<'EOF' > project_root/templates/teacher_dashboard.html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>講師ダッシュボード</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container my-4">
  <h2>{{ session['username'] }}先生のダッシュボード</h2>
  <ul>
    <li><a href="{{ url_for('teacher_students') }}">生徒一覧</a></li>
    <li><a href="{{ url_for('teacher_add_score') }}">生徒の試験点数入力</a></li>
    <li><a href="{{ url_for('teacher_notify') }}">生徒への通知送信</a></li>
    <li><a href="{{ url_for('profile') }}">プロフィール編集</a></li>
    <li><a href="{{ url_for('logout') }}">ログアウト</a></li>
  </ul>
</div>
</body>
</html>
EOF

#############################
# templates/teacher_add_score.html の作成
#############################
cat <<'EOF' > project_root/templates/teacher_add_score.html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>試験点数入力</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container my-4">
  <h3>生徒の期末試験点数入力</h3>
  {% if msg %}
    <div class="alert alert-info">{{ msg }}</div>
  {% endif %}
  <form action="{{ url_for('teacher_add_score') }}" method="post" class="bg-light p-3">
    <div class="form-group">
      <label>生徒のユーザー名</label>
      <input type="text" name="student_username" class="form-control" required>
    </div>
    <div class="form-group">
      <label>教科</label>
      <input type="text" name="subject" class="form-control" required>
    </div>
    <div class="form-group">
      <label>学期</label>
      <select name="term" class="form-control" required>
        <option value="">--選択--</option>
        <option value="1">1学期</option>
        <option value="2">2学期</option>
        <option value="3">3学期</option>
      </select>
    </div>
    <div class="form-group">
      <label>点数</label>
      <input type="number" name="score" class="form-control" min="0" max="100" required>
    </div>
    <button type="submit" class="btn btn-primary">登録</button>
    <a href="{{ url_for('teacher_dashboard') }}" class="btn btn-secondary">戻る</a>
  </form>
</div>
</body>
</html>
EOF

#############################
# templates/teacher_notify.html の作成
#############################
cat <<'EOF' > project_root/templates/teacher_notify.html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>通知メッセージ送信</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container my-4">
  <h3>生徒への通知送信</h3>
  {% if msg %}
    <div class="alert alert-info">{{ msg }}</div>
  {% endif %}
  <form action="{{ url_for('teacher_notify') }}" method="post" class="bg-light p-3">
    <div class="form-group">
      <label>生徒のユーザー名</label>
      <input type="text" name="student_username" class="form-control" required>
    </div>
    <div class="form-group">
      <label>メッセージ内容</label>
      <textarea name="message" class="form-control" rows="4" required></textarea>
    </div>
    <button type="submit" class="btn btn-primary">送信</button>
    <a href="{{ url_for('teacher_dashboard') }}" class="btn btn-secondary">戻る</a>
  </form>
</div>
</body>
</html>
EOF

#############################
# templates/teacher_students.html の作成
#############################
cat <<'EOF' > project_root/templates/teacher_students.html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>生徒一覧</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container my-4">
  <h3>生徒一覧</h3>
  <a href="{{ url_for('teacher_dashboard') }}">ダッシュボードに戻る</a>
  <a href="{{ url_for('teacher_add_student') }}" class="btn btn-success btn-sm">新規生徒追加</a>
  {% if students %}
    <table class="table table-bordered mt-3">
      <thead>
         <tr>
           <th>ユーザー名</th>
           <th>氏名</th>
           <th>メール</th>
           <th>操作</th>
         </tr>
      </thead>
      <tbody>
        {% for student in students %}
        <tr>
          <td>{{ student['username'] }}</td>
          <td>{{ student['name'] }}</td>
          <td>{{ student['email'] }}</td>
          <td>
            <a href="{{ url_for('teacher_student_detail', student_id=student['id']) }}" class="btn btn-info btn-sm">詳細</a>
            <a href="{{ url_for('teacher_edit_student', student_id=student['id']) }}" class="btn btn-warning btn-sm">成績編集</a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>生徒が登録されていません。</p>
  {% endif %}
</div>
</body>
</html>
EOF

#############################
# templates/teacher_student_detail.html の作成
#############################
cat <<'EOF' > project_root/templates/teacher_student_detail.html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>{{ student['name'] }} の詳細</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container my-4">
  <h3>{{ student['name'] }} の詳細情報</h3>
  <p>ユーザー名: {{ student['username'] }}</p>
  <p>メール: {{ student['email'] }}</p>
  <h5>期末試験点数</h5>
  {% if scores %}
    <ul class="list-group">
      {% for s in scores %}
        <li class="list-group-item">学期{{ s['term'] }} – {{ s['subject'] }}：{{ s['score'] }}点</li>
      {% endfor %}
    </ul>
  {% else %}
    <p>点数情報はありません。</p>
  {% endif %}
  <h5>内申点</h5>
  {% if grades %}
    <ul class="list-group">
      {% for g in grades %}
        <li class="list-group-item">学期{{ g['term'] }} – {{ g['subject'] }}：評価{{ g['grade'] }}</li>
      {% endfor %}
    </ul>
  {% else %}
    <p>内申点情報はありません。</p>
  {% endif %}
  <a href="{{ url_for('teacher_students') }}">一覧に戻る</a>
</div>
</body>
</html>
EOF

#############################
# templates/teacher_edit_student.html の作成
#############################
cat <<'EOF' > project_root/templates/teacher_edit_student.html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>{{ student['name'] }} の成績編集</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container my-4">
  <h3>{{ student['name'] }} の成績編集</h3>
  <a href="{{ url_for('teacher_student_detail', student_id=student['id']) }}">詳細に戻る</a>
  <hr>
  <h5>期末試験点数入力／更新</h5>
  {% if msg_exam %}
    <div class="alert alert-info">{{ msg_exam }}</div>
  {% endif %}
  <form method="post" action="{{ url_for('teacher_edit_student', student_id=student['id']) }}">
    <input type="hidden" name="score_submit" value="1">
    <div class="form-group">
      <label>教科</label>
      <input type="text" name="subject_exam" class="form-control" required>
    </div>
    <div class="form-group">
      <label>学期</label>
      <select name="term_exam" class="form-control" required>
        <option value="">--選択--</option>
        <option value="1">1学期</option>
        <option value="2">2学期</option>
        <option value="3">3学期</option>
      </select>
    </div>
    <div class="form-group">
      <label>点数</label>
      <input type="number" name="score" class="form-control" min="0" max="100" required>
    </div>
    <button type="submit" class="btn btn-primary">登録／更新</button>
  </form>
  <hr>
  <h5>内申点入力／更新</h5>
  {% if msg_internal %}
    <div class="alert alert-info">{{ msg_internal }}</div>
  {% endif %}
  <form method="post" action="{{ url_for('teacher_edit_student', student_id=student['id']) }}">
    <input type="hidden" name="grade_submit" value="1">
    <div class="form-group">
      <label>教科</label>
      <input type="text" name="subject_grade" class="form-control" required>
    </div>
    <div class="form-group">
      <label>学期</label>
      <select name="term_grade" class="form-control" required>
        <option value="">--選択--</option>
        <option value="1">1学期</option>
        <option value="2">2学期</option>
        <option value="3">3学期</option>
      </select>
    </div>
    <div class="form-group">
      <label>内申点（1～5）</label>
      <input type="number" name="grade" class="form-control" min="1" max="5" required>
    </div>
    <button type="submit" class="btn btn-primary">登録／更新</button>
  </form>
</div>
</body>
</html>
EOF

#############################
# templates/teacher_add_student.html の作成
#############################
cat <<'EOF' > project_root/templates/teacher_add_student.html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>新規生徒追加</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
<div class="container my-4" style="max-width:500px;">
  <h3>新規生徒追加</h3>
  {% if msg %}
    <div class="alert alert-info">{{ msg }}</div>
  {% endif %}
  <form method="post" action="{{ url_for('teacher_add_student') }}">
    <div class="form-group">
      <label>ユーザー名</label>
      <input type="text" name="username" class="form-control" required>
    </div>
    <div class="form-group">
      <label>氏名</label>
      <input type="text" name="name" class="form-control" required>
    </div>
    <div class="form-group">
      <label>メール</label>
      <input type="email" name="email" class="form-control" required>
    </div>
    <div class="form-group">
      <label>パスワード</label>
      <input type="password" name="password" class="form-control" required>
    </div>
    <button type="submit" class="btn btn-primary">追加</button>
    <a href="{{ url_for('teacher_students') }}" class="btn btn-secondary">戻る</a>
  </form>
</div>
</body>
</html>
EOF

#############################
# static/style.css の作成（任意。サンプルとして空ファイルを作成）
#############################
cat <<'EOF' > project_root/static/style.css
/* style.css - 必要に応じてCSSを追加してください */
EOF

echo "プロジェクト構成が project_root/ 以下に作成されました。"
