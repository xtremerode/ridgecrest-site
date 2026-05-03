# Active Session — 2026-05-02

**Focus:** Built Ridgecrest 360 from scratch (was stuck on a Codex runaway loop)

## What was done this session

### Ridgecrest 360 — BUILT AND RUNNING

**Prior session recap:** The architecture was designed in session c22d501d (7:16–7:46am), then got stuck when Codex review spawned 1,501 subagents in a runaway loop. Nothing was built.

**This session:** Full app built and running.

### Files created
- `/home/claudeuser/sphere_docs/app.py` — Flask app, all routes
- `/home/claudeuser/sphere_docs/db.py` — SQLite schema, init_db
- `/home/claudeuser/sphere_docs/stitcher.py` — OpenCV stitching pipeline
- `/home/claudeuser/sphere_docs/start.sh` — startup script
- `/home/claudeuser/sphere_docs/CLAUDE.md` — governance for this project
- `templates/` — base, index, project, room, viewer (Pannellum), capture (mobile), admin
- `static/css/app.css` — full dark-theme UI
- `static/manifest.json` — PWA manifest
- `static/icons/icon-192.png`, `icon-512.png` — generated PWA icons
- `ssl/rc360.crt` + `rc360.key` — self-signed cert with IP SAN (147.182.242.54)

### Verified working
- HTTP: http://147.182.242.54:8091/
- HTTPS: https://147.182.242.54:8444/ (mobile camera works — accept cert warning once)
- All routes 200: /, /capture, /admin, /project/<slug>, /room/<id>, /view/<id>
- API: create project, create room, create scan, scan status, delete all
- End-to-end DB flow tested and clean

### Install notes
- `opencv-python-headless` installed via pip (system-wide)
- ffmpeg NOT installed (needs `! sudo apt install ffmpeg`) — video upload uses OpenCV fallback
- Nginx HTTPS not wired (no sudo) — Flask serves HTTPS natively on 8444

---

## Open items (Ridgecrest 360)
1. Auto-start on reboot (systemd service) — not yet done
2. ffmpeg install via Henry's sudo: `! sudo apt install ffmpeg`
3. DNS + nginx + Let's Encrypt when ready (instructions in sphere_docs/CLAUDE.md)

## Open items (main Ridgecrest site — carried from prior sessions)
- Portfolio featured card gradient feature — approved, needs guardrail run
- 3 missing Wix CDN images
- Render review queue
- nav prefetch slug bug (minor)
