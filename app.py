import sqlite3
from flask import Flask, request, render_template_string, session, jsonify
import random
import os

app = Flask(__name__)
app.secret_key = 'NewJerusalem'

# Database setup
conn = sqlite3.connect('biblelit.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, level INTEGER, score INTEGER, badges TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS content (id INTEGER PRIMARY KEY, level INTEGER, area TEXT, question TEXT, options TEXT, answer TEXT, hint TEXT, instruction TEXT)''')

# Sample KJV content
content_data = [
    (1, 'phonological_awareness', 'What rhymes with "pray"? (From Psalm 118:24)', 'day,cat,run', 'day', 'Think of a word that sounds like pray, like a bright new day.', 'Rhyming words end the same. Example: Pray rhymes with day in "This is the day which the Lord hath made" (Psalm 118:24 KJV).'),
    (1, 'phonics', 'Blend sounds to make "God" (g-o-d)', 'god,dog,got', 'god', 'Short o sound like in dog.', 'Phonics: G + o + d = God, as in "He that loveth not knoweth not God; for God is love" (1 John 4:8 KJV).'),
    (2, 'phonological_awareness', 'Count syllables in "Jesus" (Je-sus)', '1,2,3', '2', 'Clap it out: Je-sus.', 'Syllables help rhythm. Jesus has 2, like in "For unto you is born this day in the city of David a Saviour, which is Christ the Lord" (Luke 2:11 KJV).'),
    (3, 'phonics', 'What word has silent e: faith (f-a-i-t-h)', 'faith,fat,fit', 'faith', 'Silent e makes long a sound.', 'Silent e in faith, from "Now faith is the substance of things hoped for, the evidence of things not seen" (Hebrews 11:1 KJV).'),
    (4, 'vocabulary', 'What means "love" in Bible terms? (Charity)', 'hate,kindness,anger', 'kindness', 'Unconditional like God\'s.', 'Vocabulary: Charity means selfless love, as in "Thou shalt love thy neighbour as thyself" (Mark 12:31 KJV).'),
    (5, 'comprehension', 'In the Creation story, what did God make on day 1? (Genesis 1)', 'light,animals,people', 'light', 'Read: "Let there be light."', 'Comprehension: God created light first (Genesis 1:3 KJV: "And God said, Let there be light: and there was light"). Answer questions after short passages.')
]
for data in content_data:
    cursor.execute("INSERT OR IGNORE INTO content (level, area, question, options, answer, hint, instruction) VALUES (?, ?, ?, ?, ?, ?, ?)", data)
conn.commit()

def get_question(level, area, difficulty='standard'):
    cursor.execute("SELECT question, options, answer, hint, instruction FROM content WHERE level=? AND area=? LIMIT 1", (level, area))
    row = cursor.fetchone()
    if not row:
        return "No question available", "", "", "", ""
    question, options, answer, hint, instruction = row
    if difficulty == 'guided':
        return f"{question} (Hint: {hint})", options, answer
    elif difficulty == 'instruction':
        return f"{instruction}\nNow try: {question}", options, answer
    return question, options, answer

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        if not user:
            cursor.execute("INSERT INTO users (username, level, score, badges) VALUES (?, 1, 0, '')", (username,))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE username=?", (username,))
            user = cursor.fetchone()
        session['user_id'] = user[0]
        return dashboard()
    return render_template_string('''
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>BibleLit Core</title>
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <h1 class="text-center mb-4">BibleLit Core Login</h1>
            <form method="post" class="card p-4 mx-auto" style="max-width: 400px;">
                <div class="mb-3">
                    <label for="username" class="form-label">Username</label>
                    <input type="text" class="form-control" name="username" required>
                </div>
                <button type="submit" class="btn btn-primary w-100">Login</button>
            </form>
        </div>
    </body>
    </html>
    ''')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return login()
    cursor.execute("SELECT level, score, badges FROM users WHERE id=?", (session['user_id'],))
    level, score, badges = cursor.fetchone()
    return render_template_string('''
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>BibleLit Core Dashboard</title>
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <h1 class="text-center mb-4">BibleLit Core Dashboard</h1>
            <div class="card p-4">
                <p><strong>Level:</strong> {{ level }}</p>
                <p><strong>Score:</strong> {{ score }}</p>
                <p><strong>Badges:</strong> {{ badges }}</p>
                <a href="/quiz?area=phonological_awareness" class="btn btn-primary">Start Phonological Awareness</a>
            </div>
        </div>
    </body>
    </html>
    ''', level=level, score=score, badges=badges or 'None')

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'user_id' not in session:
        return login()
    
    area = request.args.get('area', 'phonological_awareness')
    cursor.execute("SELECT level, score FROM users WHERE id=?", (session['user_id'],))
    level, score = cursor.fetchone()
    difficulty = 'standard' if score >= 7 else 'guided' if score >= 3 else 'instruction'
    
    question, options, answer = get_question(level, area, difficulty)
    options_list = options.split(',') if options else []
    
    if request.method == 'POST':
        user_answer = request.form['answer']
        correct = user_answer.lower() == answer.lower()
        score += 1 if correct else -1
        score = max(0, score)
        cursor.execute("SELECT badges FROM users WHERE id=?", (session['user_id'],))
        badges = cursor.fetchone()[0] or ''
        if correct and score % 5 == 0:
            badges += ',Faith Builder'
        cursor.execute("UPDATE users SET score=?, badges=? WHERE id=?", (score, badges, session['user_id']))
        conn.commit()
        if score >= 10:
            level += 1
            score = 0
            cursor.execute("UPDATE users SET level=?, score=? WHERE id=?", (level, score, session['user_id']))
            conn.commit()
        return jsonify({'correct': correct, 'feedback': 'Great job!' if correct else 'Try again!', 'next_question': get_question(level, area, difficulty)[0]})
    
    return render_template_string('''
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>BibleLit Core Quiz</title>
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <h1 class="text-center mb-4">Level {{ level }}: {{ area.replace('_', ' ').title() }}</h1>
            <div class="card p-4">
                <p class="lead">{{ question }}</p>
                <form id="quiz-form" method="post">
                    {% for opt in options_list %}
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="answer" value="{{ opt }}" id="opt-{{ loop.index }}">
                            <label class="form-check-label" for="opt-{{ loop.index }}">{{ opt }}</label>
                        </div>
                    {% endfor %}
                    <button type="submit" class="btn btn-primary mt-3">Submit</button>
                </form>
            </div>
        </div>
        <script>
            document.getElementById('quiz-form').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const response = await fetch('/quiz?area={{ area }}', { method: 'POST', body: formData });
                const data = await response.json();
                alert(data.feedback);
                location.reload();
            });
        </script>
    </body>
    </html>
    ''', level=level, question=question, options_list=options_list, area=area)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)