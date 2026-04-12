#!/usr/bin/env python3
"""
Ridgecrest Agency Knowledge Base — File API
Port: 8765
Auth: Bearer token (see API_TOKEN.txt)

Endpoints:
  POST /upload  — { "folder": "<subfolder>", "filename": "<name>", "content": "<text>" }
  GET  /file?path=<relative-path> — read any file by relative path
"""

import os
import re
from flask import Flask, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "API_TOKEN.txt")

with open(TOKEN_FILE) as f:
    API_TOKEN = f.read().strip()

VALID_FOLDERS = {
    "campaigns", "keywords", "locations", "competitors",
    "rules", "ads", "performance", "handoffs", "scripts", "assets", ""
}

app = Flask(__name__)


def check_auth():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    return auth[7:] == API_TOKEN


def safe_path(relative):
    """Resolve path within BASE_DIR, reject traversal attempts."""
    target = os.path.realpath(os.path.join(BASE_DIR, relative))
    if not target.startswith(BASE_DIR + os.sep) and target != BASE_DIR:
        return None
    return target


@app.route("/upload", methods=["POST"])
def upload():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    folder = data.get("folder", "").strip().strip("/")
    filename = data.get("filename", "").strip()
    content = data.get("content", "")

    if not filename:
        return jsonify({"error": "filename required"}), 400

    # Reject filename traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid filename"}), 400

    if folder not in VALID_FOLDERS:
        return jsonify({"error": f"Invalid folder. Must be one of: {sorted(VALID_FOLDERS)}"}), 400

    if folder:
        dest_dir = os.path.join(BASE_DIR, folder)
    else:
        dest_dir = BASE_DIR

    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)

    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)

    relative_saved = os.path.join(folder, filename) if folder else filename
    return jsonify({"saved": relative_saved, "path": dest_path}), 200


@app.route("/file", methods=["GET"])
def read_file():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    rel = request.args.get("path", "").strip().lstrip("/")
    if not rel:
        return jsonify({"error": "path parameter required"}), 400

    target = safe_path(rel)
    if target is None:
        return jsonify({"error": "Path traversal rejected"}), 400

    if not os.path.isfile(target):
        return jsonify({"error": "File not found"}), 404

    with open(target, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    return jsonify({"path": rel, "content": content}), 200


@app.route("/list", methods=["GET"])
def list_files():
    """List files in a folder (optional ?folder= param)."""
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    folder = request.args.get("folder", "").strip().strip("/")
    if folder and folder not in VALID_FOLDERS:
        return jsonify({"error": "Invalid folder"}), 400

    scan_dir = os.path.join(BASE_DIR, folder) if folder else BASE_DIR
    if not os.path.isdir(scan_dir):
        return jsonify({"files": []}), 200

    files = []
    for entry in sorted(os.listdir(scan_dir)):
        full = os.path.join(scan_dir, entry)
        if os.path.isfile(full):
            rel = os.path.join(folder, entry) if folder else entry
            files.append(rel)

    return jsonify({"folder": folder or "/", "files": files}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "ridgecrest-agency-api"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765, debug=False)
