from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import yt_dlp
import os
import uuid

app = Flask(__name__)
CORS(app) 

TEMP_DIR = "downloads"

def download_youtube_video(video_url, video_quality):
    """
    Downloads a YouTube video/audio using yt-dlp and returns the file path.
    """
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    unique_id = str(uuid.uuid4())
    output_template = os.path.join(TEMP_DIR, f"{unique_id}.%(ext)s")

    if video_quality == "bestaudio":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'continuedl': True,
            'cookiefile': 'cookies.txt'
        }
    else:
        ydl_opts = {
            'format': f'{video_quality}+bestaudio/best',
            'outtmpl': output_template,
            'merge_output_format': 'mp4',
            'continuedl': True,
            'cookiefile': 'cookies.txt'
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        downloaded_filename = ydl.prepare_filename(info)

        # If audio-only was downloaded, change extension
        if video_quality == "bestaudio":
            downloaded_filename = os.path.splitext(downloaded_filename)[0] + ".mp3"
    
    return downloaded_filename

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "YouTube Downloader API"}), 200

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        video_quality = data.get('video_quality', 'bestvideo')

        if not video_url:
            return jsonify({"error": "Missing video_url"}), 400

        file_path = download_youtube_video(video_url, video_quality)
        filename = os.path.basename(file_path)

        return send_file(file_path, as_attachment=True, download_name=filename)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

