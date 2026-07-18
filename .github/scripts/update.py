#!/usr/bin/env python3
"""多源订阅拉取 - 用于 GitHub Actions"""
import json, base64, urllib.parse, os, subprocess
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def curl_fetch(url, timeout=25):
    cmd = f'curl -sL --max-time {timeout} "{url}"'
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout + 5)
        data = r.stdout.decode("utf-8", errors="replace").strip()
        if r.returncode == 0 and len(data) > 50:
            return data
        return None
    except:
        return None

def parse_vless_lines(data):
    nodes, raw = [], []
    for line in data.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if line.startswith("vless://"):
            raw.append(line)
        else:
            try:
                decoded = base64.b64decode(line).decode("utf-8")
                for sl in decoded.strip().splitlines():
                    sl = sl.strip()
                    if sl.startswith("vless://"):
                        raw.append(sl)
            except:
                pass
    return raw

def parse_vless_to_singbox(raw_links):
    nodes = []
    seen_tags = set()
    for link in raw_links:
        if not link.startswith("vless://"):
            continue
        try:
            uuid_part, host_part = link[8:].split("@", 1)
            name = "CF优选"
            if "#" in host_part:
                host_part, name = host_part.rsplit("#", 1)
                name = urllib.parse.unquote(name)
            server, port_str = host_part.split(":", 1)
            params = {}
            if "?" in port_str:
                port_str, query = port_str.split("?", 1)
                params = dict(urllib.parse.parse_qsl(query))
            port = int(port_str)
            node = {
                "type": "vless", "tag": name,
                "server": server, "server_port": port,
                "uuid": uuid_part, "flow": "",
                "tls": {
                    "enabled": True,
                    "server_name": params.get("sni", params.get("host", "")),
                    "insecure": False,
                    "utls": {"enabled": True, "fingerprint": params.get("fp", "chrome")},
                },
                "transport": {
                    "type": "ws",
                    "path": params.get("path", "/"),
                    "headers": {"Host": params.get("host", params.get("sni", ""))},
                },
            }
            if params.get("ech"):
                node["tls"]["ech"] = {"enabled": True}
            if params.get("flow"):
                node["flow"] = params.get("flow")
            tag = node["tag"]
            if tag in seen_tags:
                s = 1
                while f"{tag}_{s}" in seen_tags:
                    s += 1
                node["tag"] = f"{tag}_{s}"
            seen_tags.add(node["tag"])
            nodes.append(node)
        except:
            continue
    return nodes

def sanitize_node(node):
    t = node.get("type", "")
    if t == "hysteria":
        for key in ("up", "down"):
            if key in node:
                node[f"{key}_mbps"] = int(float(node.pop(key)))
    if t == "shadowsocks":
        node.pop("plugin", None)
        node.pop("plugin_opts", None)
    return node

# ====== 订阅源 ======
today = datetime.now()
ymd = today.strftime("%Y/%m/%d")
ymd2 = today.strftime("%Y%m%d")
sub_url = os.environ.get("SUB_URL", "")

SOURCES = [
    {
        "name": "yoyapai",
        "type": "vless_plain",
        "url": f"https://freenode.yoyapai.com/{ymd}-yoyapai.com-ssr-v2ray-vpn-mian-fei-jie-dian.txt",
    },
    {
        "name": "v2raynode",
        "type": "singbox_json",
        "url": f"https://node.v2raynode.cc/uploads/{ymd[:4]}/{ymd[5:7]}/{ymd2}.json",
    },
    {
        "name": "shinra",
        "type": "base64_vless",
        "url": sub_url,
    },
]

# ====== 拉取 ======
all_raw_links = []
all_nodes = []
source_order = []
MAX_NODES = 300

for src in SOURCES:
    if not src["url"]:
        continue
    url = src["url"]
    log(f"📡 {src['name']}: 拉取...")

    data = curl_fetch(url)
    if not data:
        log(f"  ❌ 拉取失败")
        continue

    if src["type"] == "vless_plain":
        raw_links = parse_vless_lines(data)
        nodes = parse_vless_to_singbox(raw_links)
        all_raw_links.extend(raw_links)
        all_nodes.extend(nodes)
        log(f"  ✅ {len(nodes)} 个 VLESS")

    elif src["type"] == "singbox_json":
        try:
            cfg = json.loads(data)
            skip = {"selector", "urltest", "direct", "block", "dns"}
            nodes = []
            for ob in cfg.get("outbounds", []):
                if ob.get("type") in skip:
                    continue
                ob = sanitize_node(ob)
                nodes.append(ob)
                # 生成 vless 链接
                if ob.get("type") == "vless":
                    u = ob.get("uuid", "")
                    sv = ob.get("server", "")
                    pt = ob.get("server_port", 443)
                    tg = ob.get("tag", "")
                    ps = {}
                    tl = ob.get("tls", {})
                    ws = ob.get("transport", {})
                    if tl.get("enabled"):
                        ps["security"] = "tls"
                        if tl.get("server_name"):
                            ps["sni"] = tl["server_name"]
                    if ws.get("type") == "ws":
                        ps["type"] = "ws"
                        if ws.get("path"):
                            ps["path"] = ws["path"]
                        if ws.get("headers", {}).get("Host"):
                            ps["host"] = ws["headers"]["Host"]
                    if ob.get("flow"):
                        ps["flow"] = ob["flow"]
                    q = urllib.parse.urlencode(ps)
                    link = f"vless://{u}@{sv}:{pt}?{q}#{urllib.parse.quote(tg)}"
                    all_raw_links.append(link)
            all_nodes.extend(nodes)
            log(f"  ✅ {len(nodes)} 个混合节点")
        except Exception as e:
            log(f"  ⚠️ JSON 解析失败: {e}")

    elif src["type"] == "base64_vless":
        try:
            decoded = base64.b64decode(data).decode("utf-8")
            raw_links = parse_vless_lines(decoded)
        except:
            raw_links = parse_vless_lines(data)
        nodes = parse_vless_to_singbox(raw_links)
        all_raw_links.extend(raw_links)
        all_nodes.extend(nodes)
        log(f"  ✅ {len(nodes)} 个 VLESS")

    source_order.append(src["name"])
    if len(all_nodes) >= MAX_NODES:
        all_nodes = all_nodes[:MAX_NODES]
        break

if not all_nodes:
    log("❌ 所有源均未获取到节点")
    exit(1)

# ====== 去重 ======
seen_key = set()
deduped = []
for n in all_nodes:
    key = f"{n.get('server', '')}:{n.get('server_port', '')}:{n.get('type', '')}"
    if key not in seen_key:
        seen_key.add(key)
        deduped.append(n)
all_nodes = deduped[:MAX_NODES]

log(f"\n📊 最终: {len(all_nodes)} 个节点")
type_counts = {}
for n in all_nodes:
    t = n.get("type", "?")
    type_counts[t] = type_counts.get(t, 0) + 1
for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
    log(f"  {t}: {c}")
log(f"  来源: {' → '.join(source_order)}")

# ====== 生成 sub.txt (base64 vless) ======
seen_links = set()
unique_raw = []
for l in all_raw_links:
    if l not in seen_links:
        seen_links.add(l)
        unique_raw.append(l)

# 按 server:port 去重
server_seen = set()
final_links = []
for l in unique_raw:
    try:
        rest = l[8:].split("@", 1)[1] if "@" in l[8:] else ""
        key = rest.split("?")[0] if "?" in rest else rest
    except:
        key = l
    if key not in server_seen:
        server_seen.add(key)
        final_links.append(l)

plain_text = "\n".join(final_links)
b64_data = base64.b64encode(plain_text.encode()).decode()

with open("sub.txt", "w") as f:
    f.write(b64_data)
log(f"📄 sub.txt: {len(final_links)} 个节点 ({len(b64_data)} bytes)")

# ====== 生成 config.json ======
priority = {"vless": 0, "hysteria": 0, "hysteria2": 0, "tuic": 1, "vmess": 2, "shadowsocks": 3, "trojan": 4}
all_nodes.sort(key=lambda n: (priority.get(n.get("type", ""), 5), n.get("tag", "")))
tags = [n["tag"] for n in all_nodes]

config = {
    "log": {"level": "warn"},
    "inbounds": [{"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 7890}],
    "outbounds": [
        {"type": "selector", "tag": "proxy-out", "outbounds": tags + ["auto"], "default": "auto"},
        {"type": "urltest", "tag": "auto", "outbounds": tags, "url": "https://www.gstatic.com/generate_204", "interval": "5m", "tolerance": 50},
    ] + all_nodes,
}

with open("config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)
log(f"📄 config.json: {len(all_nodes)} 个节点")

# 节点数量和来源（用于通知）
with open("node_count.txt", "w") as f:
    f.write(str(len(all_nodes)))
with open("source_order.txt", "w") as f:
    f.write(" → ".join(source_order))

log("✅ 完成")
