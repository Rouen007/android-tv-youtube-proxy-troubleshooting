#!/usr/bin/env python3
"""
Automated SmartTube internal preference fix script.
Connects via Root Telnet / ADB to update SmartTube proxy configuration to 127.0.0.1:7890.
"""

import argparse
import socket
import time
import subprocess

def run_telnet_root(tv_ip, port, cmd):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(4)
        s.connect((tv_ip, port))
        time.sleep(0.2)
        s.sendall((cmd + "\n").encode("utf-8"))
        time.sleep(0.5)
        s.sendall(b"exit\n")
        out = b""
        while True:
            try:
                d = s.recv(4096)
                if not d:
                    break
                out += d
            except:
                break
        s.close()
        return out.decode("utf-8", errors="ignore")
    except Exception as e:
        return f"Error: {e}"

def fix_smarttube(tv_ip, telnet_port=4149, proxy_uri="http://127.0.0.1:7890"):
    print(f"[*] Stopping SmartTube on TV ({tv_ip})...")
    run_telnet_root(tv_ip, telnet_port, "am force-stop org.smarttube.stable")
    time.sleep(1)

    pref_file = "/data/data/org.smarttube.stable/shared_prefs/org.smarttube.stable_preferences.xml"
    print(f"[*] Patching {pref_file} to use {proxy_uri}...")
    
    # Use sed to replace proxy URI
    patch_cmd = f"sed -i 's|http://[0-9.]*:[0-9]*|{proxy_uri}|g' {pref_file}"
    run_telnet_root(tv_ip, telnet_port, patch_cmd)

    # Verify content
    res = run_telnet_root(tv_ip, telnet_port, f"cat {pref_file}")
    print("[*] Verified preferences:\n", res.strip())

    # Set Android global proxy
    print("[*] Setting Android Global HTTP Proxy to 127.0.0.1:7890...")
    subprocess.run(["adb", "-s", f"{tv_ip}:5555", "shell", "settings", "put", "global", "http_proxy", "127.0.0.1:7890"], capture_output=True)
    subprocess.run(["adb", "-s", f"{tv_ip}:5555", "shell", "settings", "put", "global", "global_http_proxy_host", "127.0.0.1"], capture_output=True)
    subprocess.run(["adb", "-s", f"{tv_ip}:5555", "shell", "settings", "put", "global", "global_http_proxy_port", "7890"], capture_output=True)

    # Restart SmartTube
    print("[*] Restarting SmartTube...")
    subprocess.run(["adb", "-s", f"{tv_ip}:5555", "shell", "monkey", "-p", "org.smarttube.stable", "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
    print("[+] Done! SmartTube is now hooked to local proxy daemon.")

def main():
    parser = argparse.ArgumentParser(description="Fix SmartTube Proxy Preferences")
    parser.add_argument("--tv-ip", default="192.168.0.116", help="Android TV IP address")
    parser.add_argument("--telnet-port", type=int, default=4149, help="Root telnet port on TV")
    parser.add_argument("--proxy-uri", default="http://127.0.0.1:7890", help="Proxy URI")
    args = parser.parse_args()

    fix_smarttube(args.tv_ip, args.telnet_port, args.proxy_uri)

if __name__ == "__main__":
    main()
