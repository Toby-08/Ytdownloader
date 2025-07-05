from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import yt_dlp
import os
import uuid
import zipfile
import shutil

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


TEMP_DIR = "downloads"
COOKIE_DIR = "cookies"

# Ensure temp directories exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(COOKIE_DIR, exist_ok=True)

def download_youtube_video(video_url, video_quality, cookie_mode, cookie_file_path=None, start_index=None):
    unique_id = str(uuid.uuid4())
    output_template = os.path.join(TEMP_DIR, f"{unique_id}-%(playlist_index)02d-%(title)s.%(ext)s")

    ydl_opts = {
        'format': f'{video_quality}+bestaudio/best' if video_quality != "bestaudio" else 'bestaudio/best',
        'outtmpl': output_template,
        'continuedl': True,
        'noplaylist': False,  # Allow playlist downloads
    }

    if video_quality == "bestaudio":
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        ydl_opts['merge_output_format'] = 'mp4'

    if start_index is not None:
        ydl_opts['playliststart'] = start_index

    # Add cookies based on selected mode
    if cookie_mode == "upload" and cookie_file_path:
        ydl_opts['cookiefile'] = cookie_file_path
    elif cookie_mode == "browser":
        ydl_opts['cookiesfrombrowser'] = ('chrome',)

    downloaded_files = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        # Handle playlist or single video
        if 'entries' in info:
            # Playlist
            for entry in info['entries']:
                if entry:
                    filename = ydl.prepare_filename(entry)
                    if video_quality == "bestaudio":
                        filename = os.path.splitext(filename)[0] + ".mp3"
                    downloaded_files.append(filename)
        else:
            # Single video
            filename = ydl.prepare_filename(info)
            if video_quality == "bestaudio":
                filename = os.path.splitext(filename)[0] + ".mp3"
            downloaded_files.append(filename)

    return downloaded_files

@app.route('/download', methods=['POST'])
def download():
    try:
        # Use form data, not JSON
        video_url = request.form.get("video_url")
        video_quality = request.form.get("video_quality", "bestvideo")
        cookie_mode = request.form.get("cookie_mode", "none")
        start_index = request.form.get("start_index")
        start_index = int(start_index) if start_index and start_index.isdigit() else None

        if not video_url:
            return jsonify({"error": "Missing video_url"}), 400

        cookie_file_path = None
        if cookie_mode == "upload" and "cookies_file" in request.files:
            file = request.files["cookies_file"]
            cookie_filename = str(uuid.uuid4()) + "_cookies.txt"
            cookie_file_path = os.path.join(COOKIE_DIR, cookie_filename)
            file.save(cookie_file_path)

        # Download video(s)
        files = download_youtube_video(video_url, video_quality, cookie_mode, cookie_file_path, start_index)

        # If multiple files, zip them
        if len(files) > 1:
            zip_name = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_playlist.zip")
            with zipfile.ZipFile(zip_name, 'w') as zipf:
                for f in files:
                    zipf.write(f, os.path.basename(f))
            # Optionally, clean up individual files after zipping
            for f in files:
                os.remove(f)
            return send_file(zip_name, as_attachment=True, download_name=os.path.basename(zip_name))

        return send_file(files[0], as_attachment=True, download_name=os.path.basename(files[0]))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "YouTube Downloader Backend Running"}), 200


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

