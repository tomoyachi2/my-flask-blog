from flask import Flask, render_template, request
import base64
import urllib.parse
import html

app = Flask(__name__)

def convert_data(input_text, mode):
    """
    Pythonバックエンドでの変換処理ロジック
    """
    if not input_text:
        return ""
    
    try:
        if mode == 'uppercase':
            return input_text.upper()
        elif mode == 'lowercase':
            return input_text.lower()
        elif mode == 'base64_encode':
            return base64.b64encode(input_text.encode('utf-8')).decode('utf-8')
        elif mode == 'base64_decode':
            return base64.b64decode(input_text.encode('utf-8')).decode('utf-8')
        elif mode == 'url_encode':
            return urllib.parse.quote(input_text)
        elif mode == 'url_decode':
            return urllib.parse.unquote(input_text)
        elif mode == 'html_escape':
            return html.escape(input_text)
        elif mode == 'line_count':
            lines = input_text.splitlines()
            words = len(input_text.split())
            chars = len(input_text)
            return f"行数: {len(lines)} 行\n単語数: {words} ワード\n文字数: {chars} 文字"
        else:
            return input_text
    except Exception as e:
        return f"【エラー】変換に失敗しました: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def index():
    converted_text = ""
    input_text = ""
    selected_mode = "uppercase"
    
    if request.method == 'POST':
        input_text = request.form.get('input_text', '')
        selected_mode = request.form.get('mode', 'uppercase')
        converted_text = convert_data(input_text, selected_mode)
    
    return render_template(
        'index.html',
        input_text=input_text,
        converted_text=converted_text,
        selected_mode=selected_mode
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
