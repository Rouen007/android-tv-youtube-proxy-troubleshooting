#!/usr/bin/env python3
"""
Automated Subscription Updater for Android TV Mihomo (Clash Meta) Daemon.
Downloads a subscription URL, optimizes it for Android TV, pushes it via ADB/Root,
hot-reloads the core, and auto-switches to the fastest responsive node.
"""

import argparse
import urllib.request
import urllib.parse
import json
import time
import subprocess
import os
import re

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

def get_default_tv_ip():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                c = json.load(f)
                if c.get("tv_ip"):
                    return c.get("tv_ip")
        except Exception:
            pass
    return "192.168.1.100"

TV_HEADER_TEMPLATE = """# Auto-generated & optimized for Android TV Mihomo
mixed-port: 7890
allow-lan: true
mode: rule
log-level: silent
ipv6: false
tcp-concurrent: true
keep-alive-idle: 600
find-process-mode: "off"
external-controller: 0.0.0.0:9090
secret: ''

dns:
  enable: true
  ipv6: false
  enhanced-mode: redir-host
  nameserver:
    - 8.8.8.8
    - 1.1.1.1
    - 119.29.29.29
    - https://dns.google/dns-query

"""

def fetch_subscription(sub_url):
    print(f"[*] Downloading subscription from: {sub_url} ...")
    headers = {
        "User-Agent": "ClashMeta; ClashVerge; ClashforWindows/0.20.39"
    }
    req = urllib.request.Request(sub_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode("utf-8", errors="ignore")
        print(f"[+] Downloaded subscription successfully ({len(content) / 1024:.1f} KB)")
        return content

def optimize_config_for_tv(raw_yaml):
    print("[*] Injecting TV-optimized parameters (port 7890, API 9090, DNS, loopback)...")
    
    # Check if raw_yaml already contains proxies:
    if "proxies:" not in raw_yaml:
        raise ValueError("Invalid subscription YAML: 'proxies:' section not found!")

    # Find the start of proxies / proxy-groups / rules
    # We strip any conflicting top-level ports and replace with TV_HEADER_TEMPLATE
    match = re.search(r'\n(?=(proxies:|proxy-providers:))', raw_yaml)
    if match:
        body = raw_yaml[match.start():]
    else:
        # Fallback to appending
        body = raw_yaml

    optimized_yaml = TV_HEADER_TEMPLATE.strip() + "\n\n" + body.lstrip()
    return optimized_yaml

def push_config_to_tv(tv_ip, config_text, adb_path="adb"):
    target = f"{tv_ip}:5555"
    local_temp = os.path.join(os.path.dirname(__file__), "temp_tv_config.yaml")
    with open(local_temp, "w", encoding="utf-8") as f:
        f.write(config_text)
    
    print(f"[*] Connecting to TV via ADB ({target})...")
    subprocess.run([adb_path, "connect", target], capture_output=True)

    print(f"[*] Pushing new config to /sdcard/mihomo/config.yaml...")
    subprocess.run([adb_path, "-s", target, "push", local_temp, "/sdcard/mihomo/config.yaml"], capture_output=True)

    # Clean up local temp
    if os.path.exists(local_temp):
        os.remove(local_temp)
    print("[+] Config pushed to TV successfully!")

def reload_mihomo_daemon(tv_ip, adb_path="adb", api_port=9090):
    print(f"[*] Hot-reloading Mihomo configuration via REST API (http://{tv_ip}:{api_port}/configs)...")
    try:
        payload = json.dumps({"path": "/sdcard/mihomo/config.yaml"}).encode("utf-8")
        req = urllib.request.Request(
            f"http://{tv_ip}:{api_port}/configs",
            data=payload,
            method="PUT",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.getcode() in [200, 204]:
                print("[+] Mihomo hot-reloaded successfully!")
                return True
    except Exception as e:
        print(f"[!] REST hot-reload failed ({e}), falling back to process restart...")

    # Fallback: restart process via ADB
    target = f"{tv_ip}:5555"
    subprocess.run([adb_path, "-s", target, "shell", "killall mihomo 2>/dev/null || true"], capture_output=True)
    time.sleep(1)
    subprocess.run([adb_path, "-s", target, "shell", "nohup /data/local/tmp/mihomo -d /sdcard/mihomo > /dev/null 2>&1 &"], capture_output=True)
    time.sleep(2)
    print("[+] Mihomo process restarted!")
    return True

def auto_select_best_node(tv_ip, api_port=9090, proxy_port=7890, group_name="Proxy"):
    print("[*] Running smart latency test on new nodes...")
    try:
        req = urllib.request.Request(f"http://{tv_ip}:{api_port}/proxies")
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            proxies = data.get("proxies", {})
    except Exception as e:
        print(f"[-] Could not query proxies: {e}")
        return

    candidates = [name for name, p in proxies.items() if p.get("type") in ["Shadowsocks", "Vmess", "Trojan", "Hysteria2"]]
    priority_candidates = [n for n in candidates if any(k in n for k in ["IEPL", "专线", "HK", "TW", "JP", "香港", "台湾", "日本"])]
    if not priority_candidates:
        priority_candidates = candidates

    results = []
    for name in priority_candidates[:15]:
        put_data = json.dumps({"name": name}).encode("utf-8")
        s_req = urllib.request.Request(
            f"http://{tv_ip}:{api_port}/proxies/{group_name}",
            data=put_data,
            method="PUT",
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(s_req, timeout=2): pass
            
            proxy_handler = urllib.request.ProxyHandler({'http': f'http://{tv_ip}:{proxy_port}', 'https': f'http://{tv_ip}:{proxy_port}'})
            opener = urllib.request.build_opener(proxy_handler)
            test_req = urllib.request.Request("https://www.youtube.com", headers={"User-Agent": "Mozilla/5.0"})
            
            t0 = time.time()
            with opener.open(test_req, timeout=3) as r:
                dur = time.time() - t0
                print(f"    [+] Node '{name}': {dur:.2f}s")
                results.append((dur, name))
        except Exception:
            pass

    if results:
        results.sort()
        best_dur, best_node = results[0]
        print(f"\n[★] Automatically selected fastest node: '{best_node}' ({best_dur:.2f}s)")
        put_data = json.dumps({"name": best_node}).encode("utf-8")
        s_req = urllib.request.Request(
            f"http://{tv_ip}:{api_port}/proxies/{group_name}",
            data=put_data,
            method="PUT",
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(s_req, timeout=2)
    else:
        print("[-] Could not determine best node, leaving current selection.")

def main():
    parser = argparse.ArgumentParser(description="Android TV Mihomo Subscription Updater")
    parser.add_argument("--url", help="Subscription link (URL)")
    parser.add_argument("--file", help="Local Clash YAML file path")
    parser.add_argument("--tv-ip", default=DEFAULT_TV_IP, help=f"Android TV IP address (default: {DEFAULT_TV_IP})")
    parser.add_argument("--adb-path", default="adb", help="Path to adb executable")
    parser.add_argument("--no-auto-select", action="store_true", help="Disable auto-selecting fastest node after update")
    args = parser.parse_args()

    # Find adb if default is not in path
    if args.adb_path == "adb" and not subprocess.run(["where", "adb"], capture_output=True).stdout:
        candidate_adb = r"C:\Users\Administrator\Desktop\adb_tools\platform-tools\adb.exe"
        if os.path.exists(candidate_adb):
            args.adb_path = candidate_adb

    print("=" * 60)
    print(" Android TV Mihomo Subscription Updater")
    print(f" Target TV IP: {args.tv_ip}")
    print("=" * 60)

    raw_content = ""
    if args.url:
        raw_content = fetch_subscription(args.url)
    elif args.file:
        if not os.path.exists(args.file):
            print(f"[!] Error: File '{args.file}' not found!")
            return
        with open(args.file, "r", encoding="utf-8", errors="ignore") as f:
            raw_content = f.read()
    else:
        # Prompt user interactively
        user_input = input("Enter your subscription URL or local YAML file path: ").strip()
        if not user_input:
            print("[!] No input provided. Exiting.")
            return
        if user_input.startswith("http://") or user_input.startswith("https://"):
            raw_content = fetch_subscription(user_input)
        elif os.path.exists(user_input):
            with open(user_input, "r", encoding="utf-8", errors="ignore") as f:
                raw_content = f.read()
        else:
            print(f"[!] Invalid URL or file path: {user_input}")
            return

    # 1. Optimize
    optimized_yaml = optimize_config_for_tv(raw_content)

    # 2. Push to TV
    push_config_to_tv(args.tv_ip, optimized_yaml, adb_path=args.adb_path)

    # 3. Reload
    reload_mihomo_daemon(args.tv_ip, adb_path=args.adb_path)

    # 4. Auto select fastest node
    if not args.no_auto_select:
        auto_select_best_node(args.tv_ip)

    print("\n" + "=" * 60)
    print(" [✓] Subscription update complete! TV YouTube is ready to use.")
    print("=" * 60)

if __name__ == "__main__":
    main()
