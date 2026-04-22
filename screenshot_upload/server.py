from flask import Flask, request, jsonify, send_from_directory, send_file
import base64
import os
import re
from datetime import datetime, timedelta

app = Flask(__name__)
# Screenshots saved here so Claude can read them directly from disk
SAVE_DIR = "/root/agent/downloads"
DOWNLOADS_DIR = "/root/agent/downloads"
os.makedirs(SAVE_DIR, exist_ok=True)

def _next_screenshot_num(ext):
    """Return next sequential screenshot filename: screenshot_001.png etc."""
    existing = [f for f in os.listdir(SAVE_DIR)
                if re.match(r"screenshot_(\d+)\.\w+", f)]
    nums = []
    for f in existing:
        m = re.match(r"screenshot_(\d+)\.\w+", f)
        if m:
            nums.append(int(m.group(1)))
    n = max(nums) + 1 if nums else 1
    # normalise ext: jpeg → jpg, png stays png
    ext = "jpg" if ext.lower() in ("jpeg",) else ext.lower()
    return f"screenshot_{n:03d}.{ext}"

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/upload", methods=["POST"])
def upload():
    data = request.json.get("image", "")
    match = re.match(r"data:image/(\w+);base64,(.+)", data)
    if not match:
        return jsonify({"error": "Invalid image data"}), 400
    ext = match.group(1)
    img_data = base64.b64decode(match.group(2))
    filename = _next_screenshot_num(ext)
    filepath = os.path.join(SAVE_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(img_data)
    return jsonify({"filename": filename})

@app.route("/screenshot/<filename>")
def get_screenshot(filename):
    # Now served from SAVE_DIR (same as DOWNLOADS_DIR)
    return send_from_directory(SAVE_DIR, filename)

@app.route("/list")
def list_files():
    files = sorted(
        [f for f in os.listdir(SAVE_DIR) if re.match(r"screenshot_\d+\.\w+", f)],
        key=lambda f: int(re.search(r"screenshot_(\d+)", f).group(1)),
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

@app.route("/upload-file", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    filename = os.path.basename(f.filename or "")
    if not filename:
        return jsonify({"error": "Invalid filename"}), 400
    save_path = os.path.join(DOWNLOADS_DIR, filename)
    f.save(save_path)
    size = os.path.getsize(save_path)
    return jsonify({"ok": True, "name": filename, "size": size})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
