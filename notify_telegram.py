#!/usr/bin/env python3
"""发送 Telegram 通知"""
import json, os, urllib.request, urllib.parse

token = os.environ.get("TG_BOT_TOKEN", "")
chat_id = os.environ.get("TG_CHAT_ID", "")

with open("config.json") as f:
    c = json.load(f)
nodes = [o for o in c.get("outbounds", []) if o.get("type") == "vless"]
node_count = len(nodes)

import subprocess
updated = subprocess.run(
    ["bash", "-c", "TZ='Asia/Shanghai' date '+%H:%M'"],
    capture_output=True, text=True
).stdout.strip()

text = f"✅ *代理节点已更新*\n🕐 {updated}\n📦 {node_count} 个节点"
data = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()
req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
urllib.request.urlopen(req, timeout=10)
print(f"✅ Telegram 通知已发送: {node_count} 个节点")
