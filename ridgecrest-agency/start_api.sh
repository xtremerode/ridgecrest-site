#!/bin/bash
# Ridgecrest Agency Knowledge Base API — start script
# Runs the Flask API in a detached screen session named "ridgecrest-api"
# Usage: bash start_api.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION="ridgecrest-api"

if screen -list | grep -q "$SESSION"; then
    echo "Already running in screen session '$SESSION'."
    echo "To attach: screen -r $SESSION"
    echo "To stop:   screen -S $SESSION -X quit"
    exit 0
fi

screen -dmS "$SESSION" /home/claudeuser/agent/venv/bin/python "$SCRIPT_DIR/api_server.py"
sleep 1

if screen -list | grep -q "$SESSION"; then
    echo "Started: screen session '$SESSION' on port 8765"
    echo "To attach: screen -r $SESSION"
    echo "To stop:   screen -S $SESSION -X quit"
else
    echo "ERROR: screen session failed to start"
    exit 1
fi
