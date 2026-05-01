#!/usr/bin/env python3
"""
Ridgecrest Agency — MCP Server
Port: 8766
Transport: HTTP + SSE (Model Context Protocol 2024-11-05)
Auth: Bearer token (same token as api_server.py)

Tools: list_files, read_file, write_file
Scope: ridgecrest-agency/ root only — path traversal rejected
"""

import json
import os
import queue
import threading
import uuid

from flask import Flask, Response, request, stream_with_context

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "API_TOKEN.txt")

with open(TOKEN_FILE) as f:
    API_TOKEN = f.read().strip()

VALID_FOLDERS = {
    "campaigns", "keywords", "locations", "competitors",
    "rules", "ads", "performance", "handoffs", "scripts", "assets", ""
}

app = Flask(__name__)

_sessions: dict[str, queue.Queue] = {}
_sessions_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Auth + path safety
# ---------------------------------------------------------------------------

def check_auth() -> bool:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and auth[7:] == API_TOKEN:
        return True
    return request.args.get("token", "") == API_TOKEN


def safe_path(relative: str) -> str | None:
    target = os.path.realpath(os.path.join(BASE_DIR, relative))
    if not target.startswith(BASE_DIR + os.sep) and target != BASE_DIR:
        return None
    return target


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def tool_list_files(folder: str = "") -> dict:
    folder = folder.strip().strip("/")
    if folder and folder not in VALID_FOLDERS:
        return {"error": f"Invalid folder. Valid: {sorted(VALID_FOLDERS - {''})}"}
    scan_dir = os.path.join(BASE_DIR, folder) if folder else BASE_DIR
    if not os.path.isdir(scan_dir):
        return {"files": []}
    entries = []
    for entry in sorted(os.listdir(scan_dir)):
        full = os.path.join(scan_dir, entry)
        if os.path.isfile(full):
            entries.append(os.path.join(folder, entry) if folder else entry)
        elif os.path.isdir(full) and entry in VALID_FOLDERS:
            entries.append(f"{entry}/")
    return {"folder": folder or "/", "files": entries}


def tool_read_file(path: str) -> dict:
    rel = path.strip().lstrip("/")
    target = safe_path(rel)
    if target is None:
        return {"error": "Path traversal rejected"}
    if not os.path.isfile(target):
        return {"error": f"File not found: {rel}"}
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return {"path": rel, "content": content}


def tool_write_file(folder: str, filename: str, content: str) -> dict:
    folder = folder.strip().strip("/")
    filename = filename.strip()
    if not filename:
        return {"error": "filename required"}
    if ".." in filename or "/" in filename or "\\" in filename:
        return {"error": "Invalid filename"}
    if folder not in VALID_FOLDERS:
        return {"error": f"Invalid folder. Valid: {sorted(VALID_FOLDERS)}"}
    dest_dir = os.path.join(BASE_DIR, folder) if folder else BASE_DIR
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)
    saved = os.path.join(folder, filename) if folder else filename
    return {"saved": saved, "bytes": len(content.encode())}


# ---------------------------------------------------------------------------
# MCP tool registry
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "list_files",
        "description": (
            "List files in an agency knowledge base folder. "
            "Valid folders: campaigns, keywords, locations, competitors, rules, "
            "ads, performance, handoffs, scripts, assets. Leave folder empty to list root."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": "Folder name, or empty string for root"
                }
            }
        }
    },
    {
        "name": "read_file",
        "description": (
            "Read a file from the agency knowledge base. "
            "Provide a relative path such as 'handoffs/ACTIVE_SESSION.md' or 'campaigns/google_search.md'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file within the agency root"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": (
            "Write or overwrite a file in the agency knowledge base. "
            "Use this to save drafts, campaign plans, keyword research, handoffs, and strategy docs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": "Target folder: campaigns, keywords, locations, competitors, rules, ads, performance, handoffs, scripts, or assets"
                },
                "filename": {
                    "type": "string",
                    "description": "Filename only, no path separators"
                },
                "content": {
                    "type": "string",
                    "description": "Full text content to write"
                }
            },
            "required": ["folder", "filename", "content"]
        }
    }
]


def dispatch_tool(name: str, args: dict) -> dict:
    if name == "list_files":
        return tool_list_files(args.get("folder", ""))
    if name == "read_file":
        return tool_read_file(args.get("path", ""))
    if name == "write_file":
        return tool_write_file(
            args.get("folder", ""),
            args.get("filename", ""),
            args.get("content", "")
        )
    return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# JSON-RPC dispatcher
# ---------------------------------------------------------------------------

def handle_jsonrpc(body: dict) -> dict | None:
    method = body.get("method", "")
    msg_id = body.get("id")
    params = body.get("params", {}) or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ridgecrest-agency-mcp", "version": "1.0.0"}
            }
        }

    if method in ("notifications/initialized", "notifications/cancelled"):
        return None  # notifications — no response

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {}) or {}
        result = dispatch_tool(tool_name, tool_args)
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                "isError": "error" in result
            }
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    return {
        "jsonrpc": "2.0", "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }


# ---------------------------------------------------------------------------
# SSE transport endpoints
# ---------------------------------------------------------------------------

@app.route("/sse")
def sse():
    if not check_auth():
        return Response("Unauthorized", status=401)

    session_id = str(uuid.uuid4())
    q: queue.Queue = queue.Queue()
    with _sessions_lock:
        _sessions[session_id] = q

    def generate():
        try:
            yield f"event: endpoint\ndata: /messages?sessionId={session_id}\n\n"
            while True:
                try:
                    msg = q.get(timeout=25)
                    if msg is None:
                        break
                    yield f"event: message\ndata: {json.dumps(msg)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            with _sessions_lock:
                _sessions.pop(session_id, None)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@app.route("/messages", methods=["POST"])
def messages():
    if not check_auth():
        return Response("Unauthorized", status=401)

    session_id = request.args.get("sessionId", "")
    body = request.get_json(silent=True)
    if not body:
        return Response("Bad Request", status=400)

    response = handle_jsonrpc(body)
    if response is not None:
        with _sessions_lock:
            q = _sessions.get(session_id)
        if q is not None:
            q.put(response)

    return Response("", status=202)


@app.route("/health")
def health():
    return {"status": "ok", "service": "ridgecrest-agency-mcp", "port": 8766}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8766, debug=False, threaded=True)
