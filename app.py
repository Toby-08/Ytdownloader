from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import yt_dlp
import os
import uuid

app = Flask(__name__)
CORS(app)

TEMP_DIR = "downloads"
COOKIE_DIR = "cookies"

# Ensure temp directories exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(COOKIE_DIR, exist_ok=True)

def download_youtube_video(video_url, video_quality, cookie_mode, cookie_file_path=None):
    unique_id = str(uuid.uuid4())
    output_template = os.path.join(TEMP_DIR, f"{unique_id}.%(ext)s")

    ydl_opts = {
        'format': f'{video_quality}+bestaudio/best' if video_quality != "bestaudio" else 'bestaudio/best',
        'outtmpl': output_template,
        'continuedl': True,
    }

    if video_quality == "bestaudio":
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        ydl_opts['merge_output_format'] = 'mp4'

    # Add cookies based on selected mode
    if cookie_mode == "upload" and cookie_file_path:
        ydl_opts['cookiefile'] = cookie_file_path
    elif cookie_mode == "browser":
        ydl_opts['cookiesfrombrowser'] = ('chrome',)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        downloaded_filename = ydl.prepare_filename(info)

        if video_quality == "bestaudio":
            downloaded_filename = os.path.splitext(downloaded_filename)[0] + ".mp3"

    return downloaded_filename

@app.route('/download', methods=['POST'])
def download():
    try:
        # Use form data, not JSON
        video_url = request.form.get("video_url")
        video_quality = request.form.get("video_quality", "bestvideo")
        cookie_mode = request.form.get("cookie_mode", "none")

        if not video_url:
            return jsonify({"error": "Missing video_url"}), 400

        cookie_file_path = None
        if cookie_mode == "upload" and "cookies_file" in request.files:
            file = request.files["cookies_file"]
            cookie_filename = str(uuid.uuid4()) + "_cookies.txt"
            cookie_file_path = os.path.join(COOKIE_DIR, cookie_filename)
            file.save(cookie_file_path)

        # Call download function
        file_path = download_youtube_video(video_url, video_quality, cookie_mode, cookie_file_path)
        filename = os.path.basename(file_path)

        return send_file(file_path, as_attachment=True, download_name=filename)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
