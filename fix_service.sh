#!/bin/bash
sed -i 's|/root/agent/venv/bin/python|/home/claudeuser/agent/venv/bin/python|g' /etc/systemd/system/preview_server.service
systemctl daemon-reload
systemctl restart preview_server
systemctl status preview_server --no-pager | head -10
