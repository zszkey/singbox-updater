#!/usr/bin/env python3
"""发送 Telegram 通知 - 使用 requests 或 urllib"""
import json, os, subprocess, sys

token = os.environ.get("TG_BOT_TOKEN", "")
chat_id = os.environ.get("TG_CHAT_ID", "")

if not token or not chat_id:
    print("❌ TG_BOT_TOKEN or TG_CHAT_ID not set")
    sys.exit(0)

with open("config.json") as f:
    c = json.load(f)
nodes = [o for o in c.get("outbounds", []) if o.get("type") == "vless"]
node_count = len(nodes)

updated = subprocess.run(
    ["bash", "-c", "TZ='Asia/Shanghai' date '+%H:%M'"],
    capture_output=True, text=True
).stdout.strip()

# 用 curl 发送（避免 Python urllib 可能的问题）
text = f"✅ 代理节点已更新\n🕐 {updated}\n📦 {node_count} 个节点"
import urllib.parse
encoded = urllib.parse.quote(text)
cmd = f'curl -s --max-time 10 "https://api.telegram.org/bot{token}/sendMessage" -d "chat_id={chat_id}&text={encoded}&parse_mode=Markdown"'
r = subprocess.run(cmd, shell=True, capture_output=True, timeout=15)
result = r.stdout.decode()
if '"ok":true' in result:
    print(f"✅ Telegram 通知已发送: {node_count} 个节点")
else:
    print(f"⚠️ 通知可能失败: {result[:200]}")
