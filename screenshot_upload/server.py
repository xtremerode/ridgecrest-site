from flask import Flask, request, jsonify, send_from_directory, send_file
import base64
import os
import re
from datetime import datetime, timedelta

app = Flask(__name__)
SAVE_DIR = "/root/screenshots"
DOWNLOADS_DIR = "/root/agent/downloads"
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def cleanup_old_files():
    cutoff = datetime.now() - timedelta(days=10)
    for f in os.listdir(SAVE_DIR):
        m = re.match(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", f)
        if m:
            file_dt = datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6]))
            if file_dt < cutoff:
                try:
                    os.remove(os.path.join(SAVE_DIR, f))
                except:
                    pass

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/upload", methods=["POST"])
def upload():
    cleanup_old_files()
    data = request.json.get("image", "")
    match = re.match(r"data:image/(\w+);base64,(.+)", data)
    if not match:
        return jsonify({"error": "Invalid image data"}), 400
    ext = match.group(1)
    img_data = base64.b64decode(match.group(2))
    filename = datetime.now().strftime("%Y%m%d_%H%M%S") + f".{ext}"
    filepath = os.path.join(SAVE_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(img_data)
    return jsonify({"filename": filename})

@app.route("/list")
def list_files():
    files = sorted(
        [f for f in os.listdir(SAVE_DIR) if re.match(r"\d{8}_\d{6}", f)],
        reverse=True
    )
    return jsonify(files)

@app.route("/files")
def list_downloads():
    files = sorted(os.listdir(DOWNLOADS_DIR), reverse=True)
    result = []
    for f in files:
        path = os.path.join(DOWNLOADS_DIR, f)
        size = os.path.getsize(path)
        modified = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
        result.append({"name": f, "size": size, "modified": modified})
    return jsonify(result)

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(DOWNLOADS_DIR, filename, as_attachment=True, mimetype="application/octet-stream")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
