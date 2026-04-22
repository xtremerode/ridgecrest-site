# Session Handoff — 2026-04-22

## What Was Done This Session

### New Project: Photo Studio — AI Color Grading Web App

Built a **completely isolated** new web app for batch AI photo color-grading. Zero changes to any Ridgecrest project files.

**Background:** Henry had a completed photo shoot where images were blown out with wrong color grading. He re-rendered one image using ChatGPT to get the exact desired look. The Photo Studio app lets him upload all photos + a reference image, then uses OpenAI's image API to batch-process them to match the reference.

---

### What Was Built

**Location:** `/home/claudeuser/photo_studio/` (completely separate from `/home/claudeuser/agent/`)

**Architecture:**
```
photo_studio/
├── app.py                    Flask app factory (ApplicationDispatcher with /studio prefix)
├── config.py                 Constants + env vars (OpenAI key, limits, port)
├── guardrails.py             File validation (type, size, dimension limits)
├── run.py                    Startup script — locks cwd to photo_studio/ dir
├── requirements.txt          Pinned dependencies
├── .env                      OpenAI API key + config (NOT committed)
├── routes/
│   ├── upload.py             POST /upload — accepts photos + reference image
│   ├── process.py            POST /process/<job_id> — starts AI processing
│   ├── jobs.py               GET /jobs, GET /jobs/<id> — status tracking
│   └── download.py           GET /download/<job_id>/<filename> — fetch results
├── agents/
│   ├── style_analyzer_agent.py   Analyzes reference image style via GPT-4o
│   ├── photo_processor_agent.py  Applies style to each photo via gpt-image-1
│   └── batch_manager_agent.py    Orchestrates parallel processing with rate limiting
├── jobs/                     Job state files (JSON per job_id)
├── static/
│   ├── uploads/              Uploaded originals
│   └── results/              Processed outputs
└── templates/
    └── index.html            Single-page app with upload, progress, download UI
```

**Models used:**
- `gpt-4o` — style analysis of reference image
- `gpt-image-1` — image editing/color grading

**Config:**
- Port: 8090 (internal Flask)
- Max file size: 20 MB
- Max photos per job: 50
- Allowed: .jpg, .jpeg, .png
- Max dimension: 4096px (auto-resized before API call)
- Min API interval: 3.0s (rate limiting)
- Edit quality: medium (configurable via env)

**OpenAI API Key:** Saved to `/home/claudeuser/photo_studio/.env` as `OPENAI_API_KEY`

---

### Nginx Setup — PENDING (needs DigitalOcean console)

The Flask app is running on port 8090 (internal only). To make it accessible through port 80, nginx needs a new location block. The config file is already prepared at:

**`/tmp/nginx_ridgecrest.conf`**

It adds:
```nginx
location /studio/ {
    proxy_pass http://127.0.0.1:8090/;
    client_max_body_size 500m;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}
location = /studio {
    return 301 /studio/;
}
```

**Henry needs to run this in the DigitalOcean console:**
```
sudo cp /tmp/nginx_ridgecrest.conf /etc/nginx/sites-available/ridgecrest && sudo nginx -t && sudo systemctl reload nginx
```

**Risk:** Near-zero. `nginx -t` validates first; if it fails, nothing changes. Graceful reload = zero downtime.

**After running:** Photo Studio accessible at `http://147.182.242.54/studio/`

---

### Server Status at Session End

- Flask server running on port 8090 (`/home/claudeuser/photo_studio/server.pid` exists)
- Nginx config at `/tmp/nginx_ridgecrest.conf` — prepared but NOT applied
- OpenAI key in `.env` — confirmed working
- All Ridgecrest project files: **untouched**

---

## What Is Pending

1. **Henry runs nginx command** in DigitalOcean console → Photo Studio goes live at `/studio/`
2. **Test full workflow:** Upload reference image + batch of photos → verify AI processing → download results
3. Henry's actual photos need to be uploaded for the first real run

---

## What Next Session Should Read First

1. This handoff file
2. `/home/claudeuser/photo_studio/config.py` — to understand settings
3. `/home/claudeuser/photo_studio/agents/` — to understand processing pipeline
4. `/tmp/nginx_ridgecrest.conf` — if nginx hasn't been reloaded yet, this is the file to apply

---

## Decisions Henry Made

- New project is **completely isolated** from Ridgecrest — no shared code, no shared venv, no shared config
- Use OpenAI API (gpt-4o + gpt-image-1) for the photo editing pipeline
- Port 8090 internally; serve through nginx at `/studio/` path
- Reference image style analysis approach: analyze first, then apply to each photo individually
- Session ended before Henry ran the nginx command — he was asking about safety first
