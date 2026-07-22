import os
import tempfile
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# static-ffmpeg のパスを通す
import static_ffmpeg
static_ffmpeg.add_paths()

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

# ===== データベースのモデル定義 =====
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ===== ルーティング =====

@app.route('/')
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_post = Post(title=title, content=content)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('create.html')

@app.route('/post/<int:id>')
def detail(id):
    post = Post.query.get_or_404(id)
    return render_template('detail.html', post=post)

# 4. YouTubeダウンローダー機能
@app.route('/youtube', methods=['GET', 'POST'])
def youtube():
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        format_type = request.form.get('format', 'm4a')
        cookie_file = request.files.get('cookie_file')

        if not url:
            flash('URLを入力してください', 'error')
            return redirect(url_for('youtube'))

        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, '%(title)s.%(ext)s')

        # Cookieファイルの処理
        cookie_path = None
        if cookie_file and cookie_file.filename != '':
            cookie_path = os.path.join(temp_dir, 'cookies.txt')
            cookie_file.save(cookie_path)

        # yt-dlp設定（エラーの出にくい汎用フォーマット指定）
        ydl_opts = {
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
        }

        if cookie_path:
            ydl_opts['cookiefile'] = cookie_path

        # フォーマット設定の最適化
        if format_type == 'm4a':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                }],
            })
        elif format_type == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        elif format_type == 'mp4_hd':
            ydl_opts.update({
                'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
                'merge_output_format': 'mp4',
            })
        else: # mp4_best
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # 拡張子が変換処理で変わる場合のケア
                base_path = os.path.splitext(filename)[0]
                if format_type == 'm4a' and not filename.endswith('.m4a'):
                    if os.path.exists(base_path + '.m4a'):
                        filename = base_path + '.m4a'
                elif format_type == 'mp3' and not filename.endswith('.mp3'):
                    if os.path.exists(base_path + '.mp3'):
                        filename = base_path + '.mp3'
                elif 'mp4' in format_type and not filename.endswith('.mp4'):
                    if os.path.exists(base_path + '.mp4'):
                        filename = base_path + '.mp4'

            return send_file(filename, as_attachment=True)

        except Exception as e:
            flash(f'ダウンロードエラー: {str(e)}', 'error')
            return redirect(url_for('youtube'))

    return render_template('youtube.html')

if __name__ == '__main__':
    app.run(debug=True)
