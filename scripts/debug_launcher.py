import subprocess
import time
import urllib.request
import json

adb = r"C:\Users\Administrator\Desktop\adb_tools\platform-tools\adb.exe"
tv = "192.168.0.116:5555"

print("[1] Connecting to TV...")
subprocess.run([adb, "connect", tv])

def run_adb(cmd_list):
    full_cmd = [adb, "-s", tv] + cmd_list
    res = subprocess.run(full_cmd, capture_output=True, text=True, errors="ignore")
    return res.stdout.strip()

print("\n[2] Checking processes...")
ps_out = run_adb(["shell", "ps -ef"])
mihomo_procs = [line for line in ps_out.splitlines() if "mihomo" in line]
print(f"Mihomo process count: {len(mihomo_procs)}")
for p in mihomo_procs:
    print("  ->", p)

print("\n[3] Checking binary & config...")
print(run_adb(["shell", "ls -la /data/local/tmp/mihomo"]))
print(run_adb(["shell", "ls -la /sdcard/mihomo/"]))

print("\n[4] Testing local ports on TV...")
print(run_adb(["shell", "netstat -an"]))

print("\n[5] Checking YouTube-Proxy-Launcher logcat...")
log_out = run_adb(["shell", "logcat", "-d", "-s", "YouTubeProxy:V", "Mihomo:V", "AndroidRuntime:E"])
for line in log_out.splitlines()[-40:]:
    print("  logcat:", line)

print("\n[6] Checking SmartTube preferences...")
print(run_adb(["shell", "cat /data/data/org.smarttube.stable/shared_prefs/org.smarttube.stable_preferences.xml"]))
