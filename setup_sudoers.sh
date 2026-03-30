#!/bin/bash
echo "claudeuser ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart preview_server, /usr/bin/systemctl start preview_server, /usr/bin/systemctl stop preview_server" > /etc/sudoers.d/preview_server
chmod 440 /etc/sudoers.d/preview_server
systemctl restart preview_server
systemctl status preview_server --no-pager | head -5
echo "Setup complete."
