from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import yt_dlp
import os
import uuid

app = Flask(__name__)
CORS(app)

TEMP_DIR = "downloads"
COOKIES_DIR = "cookies"

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)
if not os.path.exists(COOKIES_DIR):
    os.makedirs(COOKIES_DIR)

def download_youtube_video(video_url, video_quality, cookie_mode="none", cookies_file_path=None):
    """
    Downloads a YouTube video/audio using yt-dlp and returns the file path.
    """
    unique_id = str(uuid.uuid4())
    output_template = os.path.join(TEMP_DIR, f"{unique_id}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_template,
        'continuedl': True,
    }

    if video_quality == "bestaudio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        })
    else:
        ydl_opts.update({
            'format': f'{video_quality}+bestaudio/best',
            'merge_output_format': 'mp4',
        })

    # Handle cookies
    if cookie_mode == "upload" and cookies_file_path:
        ydl_opts['cookiefile'] = cookies_file_path
    elif cookie_mode == "browser":
        ydl_opts['cookiesfrombrowser'] = ('chrome',)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        downloaded_filename = ydl.prepare_filename(info)

        # Adjust filename if audio was downloaded
        if video_quality == "bestaudio":
            downloaded_filename = os.path.splitext(downloaded_filename)[0] + ".mp3"

    return downloaded_filename

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "YouTube Downloader API"}), 200

@app.route('/download', methods=['POST'])
def download():
    try:
        video_url = request.form.get("video_url")
        video_quality = request.form.get("video_quality", "bestvideo")
        cookie_mode = request.form.get("cookie_mode", "none")

        if not video_url:
            return jsonify({"error": "Missing video_url"}), 400

        cookies_file_path = None

        if cookie_mode == "upload" and 'cookies_file' in request.files:
            uploaded_file = request.files['cookies_file']
            if uploaded_file.filename:
                filename = str(uuid.uuid4()) + ".txt"
                cookies_file_path = os.path.join(COOKIES_DIR, filename)
                uploaded_file.save(cookies_file_path)

        file_path = download_youtube_video(video_url, video_quality, cookie_mode, cookies_file_path)
        filename = os.path.basename(file_path)

        return send_file(file_path, as_attachment=True, download_name=filename)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
