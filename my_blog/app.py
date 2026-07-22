import os
import tempfile
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import yt_dlp

app = Flask(__name__)
app.secret_key = 'super-secret-key'

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

# 4. YouTubeダウンローダー機能（フォーマットエラー対策版）
@app.route('/youtube', methods=['GET', 'POST'])
def youtube():
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        format_type = request.form.get('format', 'm4a')
        cookie_file = request.files.get('cookie_file')

        if not url:
            flash('URLを入力してください', 'error')
            return redirect(url_for('youtube'))

        # 一時保存フォルダを作成
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, '%(title)s.%(ext)s')

        # Cookieファイルの処理
        cookie_path = None
        if cookie_file and cookie_file.filename != '':
            cookie_path = os.path.join(temp_dir, 'cookies.txt')
            cookie_file.save(cookie_path)

        # yt-dlpの基本設定
        ydl_opts = {
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
        }

        if cookie_path:
            ydl_opts['cookiefile'] = cookie_path

        # エラーが出にくい柔軟なフォーマット指定に変更
        if format_type == 'm4a':
            ydl_opts.update({
                'format': 'ba/b', # 最高の音声（bestaudio）、なければ全体の一番良いやつ
            })
        elif format_type == 'mp3':
            ydl_opts.update({
                'format': 'ba/b',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        elif format_type == 'mp4_hd':
            ydl_opts.update({
                'format': 'bv*[height<=1080]+ba/b[height<=1080]/b', # 1080p以下の動画+音声、無理なら単体で最高のもの
            })
        else: # mp4_best
            ydl_opts.update({
                'format': 'bv*+ba/b', # 最高画質動画+最高音声、無理なら単体で最高のもの
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # mp3変換時の拡張子補正
                if format_type == 'mp3':
                    filename = os.path.splitext(filename)[0] + '.mp3'

            return send_file(filename, as_attachment=True)

        except Exception as e:
            flash(f'ダウンロードエラー: {str(e)}', 'error')
            return redirect(url_for('youtube'))

    return render_template('youtube.html')

if __name__ == '__main__':
    app.run(debug=True)
