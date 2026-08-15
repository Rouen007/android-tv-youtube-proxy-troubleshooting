---
name: android-tv-youtube-proxy-troubleshooting
description: >-
  Comprehensive guide, diagnostic runbook, and automation toolset for deploying and
  troubleshooting YouTube / SmartTube on Android TV (e.g., Skyworth, Coocaa, Sony, Xiaomi)
  via local native background proxy daemons (Mihomo/Clash Meta) and ADB root automation.
---

# Android TV YouTube (SmartTube) & Native Proxy Troubleshooting Skill

This skill provides a systematic diagnostic and troubleshooting methodology for running YouTube / SmartTube smoothly on Android TV devices in network environments requiring proxy/VPN. It addresses aggressive OEM process killers, Wi-Fi subnet changes, Windows Firewall blocking, internal SmartTube proxy configuration deadlocks, subscription link updating, and video decoder bottlenecks.

---

## 1. Core Architecture & Mental Model

### Why Standard GUI VPN Apps Fail on Android TV
* **OEM Aggressive Task Killers**: Android TV vendors (e.g., Skyworth `SkyRMS_Performance` / `DetectSys`, Coocaa, Xiaomi) aggressively kill background processes and accessibility services once GUI apps are minimized to the background.
* **VPN Service Teardown**: When a GUI VPN app (e.g., FlClash, v2rayNG, Clash for Android) is backgrounded, Android's `VpnService` session is forcibly terminated, breaking network access for SmartTube.

### The Robust Architecture: Linux Native Daemon + Local Proxy
```mermaid
graph TD
    subgraph Android TV [Android TV / Skyworth System]
        Mihomo[Mihomo Linux Native Daemon<br>/data/local/tmp/mihomo<br>Listens on 127.0.0.1:7890<br>Controller: 127.0.0.1:9090]
        SmartTube[SmartTube App<br>Internal Proxy: 127.0.0.1:7890<br>Decoder: 1080p AVC Hard-decode]
        Telnet[Root Telnetd<br>Port 4149]
        GlobalProxy[Android Global HTTP Proxy<br>127.0.0.1:7890]
    end

    subgraph Airport Node [Overseas Edge]
        IEPL[IEPL Dedicated Transit Node<br>HK / TW / JP Streaming AI]
    end

    SmartTube -->|HTTP/HTTPS Proxy| Mihomo
    GlobalProxy --> Mihomo
    Mihomo -->|Shadowsocks / Vmess / Trojan| IEPL
    IEPL -->|Bypass GFW| YouTube[YouTube CDN & Video Stream]
```

---

## 2. Troubleshooting Matrix: Problems & Solutions

| Symptom / Error | Root Cause | Diagnosis & Verification | Solution |
| :--- | :--- | :--- | :--- |
| **`IllegalStateException: java.net.SocketTimeoutException: failed to connect to /<IP>:<PORT> after 20000ms`** | SmartTube internal preferences (`org.smarttube.stable_preferences.xml`) or Android Global Proxy is hardcoded to a stale/offline IP (e.g., old PC IP or old subnet). | Check `logcat` for `RetrofitHelper.java:127` or check `cat /data/data/org.smarttube.stable/shared_prefs/org.smarttube.stable_preferences.xml`. | Update `web_proxy_uri` to `http://127.0.0.1:7890` via root/ADB and run `settings put global http_proxy 127.0.0.1:7890`. |
| **TV Can Ping PC, ADB Works, But TV Cannot Connect to PC Proxy (SYN_SENT)** | Windows Defender Firewall drops inbound LAN connections on proxy ports (7897 / 7890) by default on Public/Private networks. | On TV: `toybox nc -w 3 <PC_IP> 7897` fails with timeout / `SYN_SENT` in `netstat`. | In Windows Firewall, allow `Clash Verge` & `verge-mihomo` for both Private and Public profiles, OR use local TV daemon on `127.0.0.1:7890`. |
| **Infinite Spinning / "转菊花" During Video Playback** | Video player is requesting 4K AV1 / VP9 formats that exceed the TV SoC's hardware decoder capabilities, forcing software decoding stall. | In player: Format shows 4K AV1 / VP9 and `AmlogicVideoDecoderAwesome: wait timeout 10ms`. | In SmartTube: Press Down $\rightarrow$ `HQ` $\rightarrow$ Video Preset $\rightarrow$ Lock to **`1080p 60fps AVC`** (or `1080p 30fps AVC`). |
| **Home Feed Loads, But Thumbnails are Blank/Dark** | 1. DNS poisoning from domestic upstream DNS (`redir-host` resolving fake IPs for `ytimg.com`).<br>2. Local image disk cache corruption during hard shutdowns. | Check thumbnail URLs: `curl https://i.ytimg.com/...` through proxy.<br>Check Mihomo DNS config. | In `/sdcard/mihomo/config.yaml`, ensure `https://dns.google/dns-query` or `1.1.1.1` is used, or switch to `fake-ip` mode. Clean cache if needed. |
| **Subscription Nodes Expired or Need Updating** | Airport subscription links change or node IPs expire. | Run `python scripts/update_subscription.py --url "<SUB_URL>"`. | Auto-downloads, injects TV parameters, hot-reloads Mihomo, and auto-selects the fastest node. |

---

## 3. Step-by-Step Diagnostic & Repair Runbook

### Step 1: Check ADB Connection & Running Daemons
```bash
# Connect to Android TV via ADB
adb connect <TV_IP>:5555

# Verify if Mihomo daemon is alive
adb -s <TV_IP>:5555 shell "ps -ef | grep mihomo"
```

If not running, launch it:
```bash
adb -s <TV_IP>:5555 shell "nohup /data/local/tmp/mihomo -d /sdcard/mihomo > /dev/null 2>&1 &"
```

---

### Step 2: One-Click Subscription Update & Node Optimization
To update the TV's subscription link with one command:
```bash
python scripts/update_subscription.py --tv-ip <TV_IP> --url "https://your-airport.com/api/v1/client/subscribe?token=..."
```
This script will:
1. Download the latest subscription YAML.
2. Inject TV low-memory & loopback parameters.
3. Push to `/sdcard/mihomo/config.yaml`.
4. Hot-reload Mihomo via REST API (zero TV reboot needed).
5. Automatically benchmark all nodes and select the fastest node.

---

### Step 3: Repair Android System & SmartTube Internal Proxy Settings
Ensure both Android Global Proxy and SmartTube internal preferences point to `127.0.0.1:7890`:
```bash
python scripts/fix_smarttube_proxy.py --tv-ip <TV_IP>
```

---

### Step 4: Video Decoder Optimization in SmartTube
In the SmartTube UI:
1. Open any video, press **Down** on the remote.
2. Select **HQ (Playback Quality Settings)** on the far left.
3. Select **Video Preset** $\rightarrow$ Check **`1080p 60fps AVC`** (or `1080p 30fps AVC`).
4. Go to **Settings $\rightarrow$ Player settings $\rightarrow$ Buffer size** $\rightarrow$ Set to **`High`**.
5. Go to **Settings $\rightarrow$ SponsorBlock** $\rightarrow$ Set to **`Enabled`**.

---

## 4. Key Scripts Reference

* `scripts/diag_tv.py`: Full end-to-end connectivity, ADB, port, and log diagnostic script.
* `scripts/update_subscription.py`: One-click subscription updater, TV optimizer, hot-reloader, and benchmark selector.
* `scripts/fix_smarttube_proxy.py`: Root-level automated XML preference updater for SmartTube.
* `scripts/smart_node_selector.py`: Automated benchmarking and fastest-node selector via Mihomo REST API.
