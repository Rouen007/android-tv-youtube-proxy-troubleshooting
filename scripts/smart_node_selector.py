#!/usr/bin/env python3
"""
Automated low-latency node selector for Mihomo REST API on Android TV.
Benchmarks all nodes and auto-switches to the fastest responsive node for YouTube.
"""

import argparse
import urllib.request
import json
import time
import os

def benchmark_and_switch(tv_ip, api_port=9090, proxy_port=7890, group_name="Proxy"):
    print(f"[*] Querying proxies from Mihomo API at http://{tv_ip}:{api_port}...")
    req = urllib.request.Request(f"http://{tv_ip}:{api_port}/proxies")
    with urllib.request.urlopen(req, timeout=3) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        proxies = data.get("proxies", {})

    candidates = [
        name for name, p in proxies.items()
        if p.get("type") in ["Shadowsocks", "Vmess", "Trojan", "Hysteria2"]
    ]

    print(f"[*] Found {len(candidates)} candidate proxy nodes. Testing top dedicated nodes...")
    
    # Prioritize dedicated / transit / IEPL nodes
    priority_candidates = [n for n in candidates if any(k in n for k in ["IEPL", "专线", "HK", "TW", "JP", "香港", "台湾", "日本"])]
    if not priority_candidates:
        priority_candidates = candidates

    results = []
    for name in priority_candidates[:20]:
        # Switch group to candidate
        put_data = json.dumps({"name": name}).encode("utf-8")
        s_req = urllib.request.Request(
            f"http://{tv_ip}:{api_port}/proxies/{group_name}",
            data=put_data,
            method="PUT",
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(s_req, timeout=2):
                pass
            
            # Benchmark latency to YouTube
            proxy_handler = urllib.request.ProxyHandler({'http': f'http://{tv_ip}:{proxy_port}', 'https': f'http://{tv_ip}:{proxy_port}'})
            opener = urllib.request.build_opener(proxy_handler)
            test_req = urllib.request.Request("https://www.youtube.com", headers={"User-Agent": "Mozilla/5.0"})
            
            t0 = time.time()
            with opener.open(test_req, timeout=3) as r:
                d = r.read()
                dur = time.time() - t0
                speed_mbps = (len(d) * 8 / (1024 * 1024)) / dur
                print(f"    [+] [{name}]: Response in {dur:.2f}s ({speed_mbps:.2f} Mbps)")
                results.append((dur, name))
        except Exception as e:
            print(f"    [-] [{name}] Failed: {e}")

    if results:
        results.sort()
        best_dur, best_node = results[0]
        print(f"\n[★] Selected fastest node: '{best_node}' (Latency: {best_dur:.2f}s)")
        
        # Apply best node
        put_data = json.dumps({"name": best_node}).encode("utf-8")
        s_req = urllib.request.Request(
            f"http://{tv_ip}:{api_port}/proxies/{group_name}",
            data=put_data,
            method="PUT",
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(s_req, timeout=2)
        print("[+] Optimal node applied successfully!")
    else:
        print("[-] No working nodes found during benchmark.")

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
    parser = argparse.ArgumentParser(description="Smart Low-Latency Node Benchmark & Selector")
    default_ip = get_default_tv_ip()
    parser.add_argument("--tv-ip", default=default_ip, help=f"Android TV IP address (default: {default_ip})")
    parser.add_argument("--api-port", type=int, default=9090, help="Mihomo REST API port")
    parser.add_argument("--proxy-port", type=int, default=7890, help="Mihomo Proxy port")
    parser.add_argument("--group", default="Proxy", help="Proxy group name in Mihomo")
    args = parser.parse_args()

    benchmark_and_switch(args.tv_ip, args.api_port, args.proxy_port, args.group)

if __name__ == "__main__":
    main()
