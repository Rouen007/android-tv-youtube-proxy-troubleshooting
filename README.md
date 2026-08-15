# Android TV YouTube (SmartTube) & Native Daemon Proxy Troubleshooting Guide

[![Android TV](https://img.shields.io/badge/Platform-Android%20TV%20%7C%20Google%20TV-blue?logo=android)](https://github.com)
[![SmartTube](https://img.shields.io/badge/App-SmartTube%20Stable-red?logo=youtube)](https://github.com/yuliskov/SmartTube)
[![Proxy Core](https://img.shields.io/badge/Daemon-Mihomo%20(Clash%20Meta)-green)](https://github.com/MetaCubeX/mihomo)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An end-to-end, battle-tested solution and troubleshooting guide for running **YouTube (SmartTube)** with maximum stability on locked-down Android TV systems (such as Skyworth, Coocaa, Xiaomi, Sony, TCL) in regions requiring proxy/VPN bypass.

---

## 📖 Table of Contents
- [Background & Problem Statement](#-background--problem-statement)
- [Architecture Design](#-architecture-design)
- [Common Pitfalls & Troubleshooting Matrix](#-common-pitfalls--troubleshooting-matrix)
- [Quick Start: Automated Scripts](#-quick-start-automated-scripts)
  - [1. One-Click Subscription Update & Hot Reload](#1-one-click-subscription-update--hot-reload)
  - [2. TV Environment Diagnostics](#2-tv-environment-diagnostics)
  - [3. One-Click SmartTube Proxy Fix](#3-one-click-smarttube-proxy-fix)
  - [4. Automated Low-Latency Node Benchmark](#4-automated-low-latency-node-benchmark)
- [Recommended SmartTube Settings](#-recommended-smarttube-settings)
- [FAQ](#-faq)

---

## 🧩 Background & Problem Statement

Standard VPN / Proxy solutions on Android TV often suffer from severe limitations:
1. **Aggressive Background Killers**: TV OEMs (e.g. Skyworth `SkyRMS_Performance` / `DetectSys`) terminate background GUI apps (such as FlClash, v2rayNG, Clash for Android) the instant you switch away to SmartTube.
2. **PC Proxy Fragility**: Forwarding TV traffic to a PC running Clash Verge breaks whenever the PC sleeps, the Wi-Fi IP changes, or Windows Defender Firewall blocks inbound LAN connections.
3. **Internal App Deadlocks**: SmartTube caches proxy configurations in internal SQLite/XML storage (`org.smarttube.stable_preferences.xml`), resulting in 20-second timeout loops if the upstream proxy changes.
4. **Hardware Decoding Stalls**: YouTube defaults to 4K AV1 / VP9 formats, overwhelming budget TV chipsets (e.g., Amlogic) and causing persistent buffering / spinning ("转菊花").

---

## 🏗️ Architecture Design

To achieve **100% independent, zero-PC-dependency, uninterruptible background operation**, we run the native Linux binary of **Mihomo (Clash Meta)** directly inside the TV filesystem as a background daemon:

```mermaid
flowchart TD
    subgraph TV [Android TV System]
        Daemon[Mihomo Native Linux Daemon<br><code>/data/local/tmp/mihomo</code><br>Port: 127.0.0.1:7890 | API: 9090]
        SmartTube[SmartTube App<br>Web Proxy: http://127.0.0.1:7890<br>Codec: 1080p AVC Hard-decode]
        GlobalProxy[Android Global HTTP Proxy<br>127.0.0.1:7890]
    end

    subgraph Airport [High Speed Transit Nodes]
        IEPL[IEPL Dedicated Transit Tunnel<br>Hong Kong / Taiwan / Japan]
    end

    SmartTube -->|Local Loopback Proxy| Daemon
    GlobalProxy --> Daemon
    Daemon -->|Encrypted ShadowSocks / Vmess| IEPL
    IEPL -->|Bypass GFW| YouTube[YouTube Video Stream & CDN]
```

### Key Advantages:
- **No Background Termination**: Running as a pure command-line binary (`/data/local/tmp/mihomo`) completely bypasses Android ActivityManager and OEM task-killer hooks.
- **Boot-Persistent**: Auto-starts on TV boot.
- **Fast Loopback Latency**: Traffic forwards via `127.0.0.1` inside the kernel, saving Wi-Fi bandwidth.

---

## 🛠️ Common Pitfalls & Troubleshooting Matrix

| Problem | Root Cause | Solution |
| :--- | :--- | :--- |
| **`SocketTimeoutException: failed to connect to /<IP>:<Port> after 20000ms`** | SmartTube internal preferences (`org.smarttube.stable_preferences.xml`) or Android Global Proxy points to a dead/old IP. | Use `fix_smarttube_proxy.py` to point `web_proxy_uri` and `http_proxy` back to `127.0.0.1:7890`. |
| **TV pings PC OK, but proxy is unreachable (`SYN_SENT`)** | Windows Firewall blocks incoming TCP connections on port `7897` / `7890`. | Allow `Clash Verge` / `verge-mihomo` in Windows Firewall, or migrate to local TV daemon. |
| **Video keeps buffering / spinning endlessly** | TV hardware cannot decode 4K AV1 / VP9; CPU throttles. | In SmartTube: Press Down $\rightarrow$ `HQ` $\rightarrow$ Video Preset $\rightarrow$ Lock to **`1080p 60fps AVC`**. |
| **Thumbnails / covers are slow or fail to load** | Upstream domestic DNS is poisoning `*.ytimg.com` under `redir-host` mode. | In `/sdcard/mihomo/config.yaml`, use `fake-ip` mode or pure encrypted DNS (`https://dns.google/dns-query`). |
| **Airport Subscription Changes / Node Expired** | Nodes expire or airport updates subscription URL. | Run `python scripts/update_subscription.py --url "<SUB_URL>"`. |

---

## ⚡ Quick Start: Automated Scripts

All helper scripts are located in the [`scripts/`](./scripts/) folder.

### 1. One-Click Subscription Update & Hot Reload
Update the TV's proxy nodes directly from an airport subscription link:
```bash
python scripts/update_subscription.py --tv-ip 192.168.0.116 --url "https://your-airport.com/api/v1/client/subscribe?token=..."
```
* Supports local file: `python scripts/update_subscription.py --tv-ip 192.168.0.116 --file ./my_config.yaml`
* Auto-injects TV performance & loopback settings (`127.0.0.1:7890`, external API `9090`).
* Hot-reloads Mihomo without requiring a TV reboot.
* Runs latency tests on new nodes and binds the fastest one automatically.

### 2. TV Environment Diagnostics
Inspect TV ADB status, running proxy processes, open ports, and system proxies:
```bash
python scripts/diag_tv.py --tv-ip 192.168.0.116
```

### 3. One-Click SmartTube Proxy Fix
Directly patches SmartTube's internal preferences file via root/ADB to bind to `127.0.0.1:7890` without manual TV menu clicking:
```bash
python scripts/fix_smarttube_proxy.py --tv-ip 192.168.0.116
```

### 4. Automated Low-Latency Node Benchmark
Benchmarks all airport nodes via Mihomo REST API and automatically switches to the fastest dedicated transit node:
```bash
python scripts/smart_node_selector.py --tv-ip 192.168.0.116
```

---

## 📺 Recommended SmartTube Settings

For optimal performance on TV hardware:
1. **Video Format**: Lock to `1080p 60fps AVC` (Hardware acceleration enabled, 5% CPU usage).
2. **Buffer Size**: Set to `High` in **Settings $\rightarrow$ Player settings $\rightarrow$ Buffer size**.
3. **SponsorBlock**: Enable in **Settings $\rightarrow$ SponsorBlock** to automatically skip sponsor segments and promos.
4. **Account Sync**: Log in via `youtube.com/activate` to sync subscriptions and playlists.

---

## 📄 License
MIT License. Feel free to use and contribute!
