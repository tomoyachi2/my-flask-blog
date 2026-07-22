import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Render環境（DATABASE_URL環境変数がある場合）ならPostgreSQL、ローカルならSQLiteを使用
db_url = os.environ.get('DATABASE_URL', 'sqlite:///blog.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ===== データベースのモデル定義（ブログ記事データ） =====
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False) # 記事タイトル
    content = db.Column(db.Text, nullable=False)       # 記事本文
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # 投稿日時

# データベースの初期化
with app.app_context():
    db.create_all()

# ===== ルーティング（ページごとの処理） =====

# 1. 記事一覧画面（トップページ）
@app.route('/')
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

# 2. 記事新規投稿処理
@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        # 新しい記事を作成してDBに保存
        new_post = Post(title=title, content=content)
        db.session.add(new_post)
        db.session.commit()
        
        return redirect(url_for('index'))
    return render_template('create.html')

# 3. 記事詳細画面
@app.route('/post/<int:id>')
def detail(id):
    post = Post.query.get_or_404(id)
    return render_template('detail.html', post=post)

if __name__ == '__main__':
    app.run(debug=True)