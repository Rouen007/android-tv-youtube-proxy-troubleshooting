#!/usr/bin/env python3
"""
Diagnostic script for Android TV YouTube / Proxy environment.
Checks ADB connection, TV processes, listening ports, and proxy reachability.
"""

import argparse
import subprocess
import socket
import urllib.request
import json
import time
import os

def get_adb_cmd():
    if subprocess.run(["where", "adb"], capture_output=True).stdout:
        return "adb"
    candidates = [
        r"C:\Users\Administrator\Desktop\adb_tools\platform-tools\adb.exe",
        r"D:\adb\adb.exe",
        r"C:\adb\adb.exe"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "adb"

def check_adb(tv_ip, port=5555):
    adb = get_adb_cmd()
    target = f"{tv_ip}:{port}"
    print(f"[*] Checking ADB connection to {target}...")
    subprocess.run([adb, "connect", target], capture_output=True)
    r = subprocess.run([adb, "devices"], capture_output=True, text=True)
    connected = target in r.stdout
    print(f"    ADB Status: {'CONNECTED' if connected else 'DISCONNECTED'}")
    return connected

def check_tv_daemons(tv_ip, port=5555):
    adb = get_adb_cmd()
    target = f"{tv_ip}:{port}"
    print("[*] Inspecting TV running processes...")
    r = subprocess.run([adb, "-s", target, "shell", "ps -ef || ps"], capture_output=True, text=True)
    mihomo_running = False
    for line in r.stdout.splitlines():
        if "mihomo" in line.lower():
            print(f"    [+] Found daemon: {line.strip()}")
            mihomo_running = True
    if not mihomo_running:
        print("    [-] Mihomo daemon is NOT running!")
    return mihomo_running

def check_tv_proxy_api(tv_ip, api_port=9090):
    print(f"[*] Checking Mihomo REST API at http://{tv_ip}:{api_port}/version...")
    try:
        req = urllib.request.Request(f"http://{tv_ip}:{api_port}/version")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"    [+] Mihomo Core Version: {data.get('version')} (Meta: {data.get('meta')})")
            return True
    except Exception as e:
        print(f"    [-] Failed to reach Mihomo API: {e}")
        return False

def check_youtube_speed(tv_ip, proxy_port=7890):
    print(f"[*] Testing YouTube access through TV proxy (http://{tv_ip}:{proxy_port})...")
    proxy_handler = urllib.request.ProxyHandler({'http': f'http://{tv_ip}:{proxy_port}', 'https': f'http://{tv_ip}:{proxy_port}'})
    opener = urllib.request.build_opener(proxy_handler)
    try:
        t0 = time.time()
        req = urllib.request.Request("https://www.youtube.com", headers={"User-Agent": "Mozilla/5.0"})
        with opener.open(req, timeout=5) as r:
            dur = time.time() - t0
            print(f"    [+] YouTube Connection OK! HTTP {r.getcode()} in {dur:.2f}s")
            return True
    except Exception as e:
        print(f"    [-] YouTube Connection FAILED: {e}")
        return False

def get_default_tv_ip():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                c = json.load(f)
                if c.get("tv_ip"):
                    return c.get("tv_ip")
        except Exception:
            pass
    return "192.168.1.100"

def main():
    parser = argparse.ArgumentParser(description="Android TV YouTube & Proxy Diagnostic Tool")
    default_ip = get_default_tv_ip()
    parser.add_argument("--tv-ip", default=default_ip, help=f"Android TV IP address (default: {default_ip})")
    args = parser.parse_args()

    print("=" * 60)
    print(f" Android TV Diagnostic Tool - Target: {args.tv_ip}")
    print("=" * 60)

    check_adb(args.tv_ip)
    check_tv_daemons(args.tv_ip)
    check_tv_proxy_api(args.tv_ip)
    check_youtube_speed(args.tv_ip)
    print("=" * 60)

if __name__ == "__main__":
    main()
