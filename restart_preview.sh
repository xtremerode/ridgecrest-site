#!/bin/bash
pkill -f "preview_server" 2>/dev/null
sleep 2
nohup /root/agent/venv/bin/python /home/claudeuser/agent/preview_server.py > /tmp/preview81.log 2>&1 &
echo "Done. PID: $!"
