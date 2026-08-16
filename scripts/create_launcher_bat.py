bat_content = """@echo off
setlocal
title 一键唤醒电视代理 (Mihomo)
color 0A

set ADB=C:\\Users\\Administrator\\Desktop\\adb_tools\\platform-tools\\adb.exe
set TV_IP=192.168.0.116

echo ======================================================
echo   正在唤醒电视代理守护进程 (Mihomo)...
echo ======================================================
echo.

echo [*] 正在连接电视 (%TV_IP%)...
"%ADB%" connect %TV_IP%:5555 >nul 2>&1

echo [*] 正在启动底层代理守护进程...
"%ADB%" -s %TV_IP%:5555 shell "pkill -9 mihomo 2>/dev/null ; nohup /data/local/tmp/mihomo -d /sdcard/mihomo > /sdcard/mihomo/mihomo.log 2>&1 &" >nul 2>&1

echo.
echo ======================================================
echo   [OK] 电视端 Mihomo 代理已成功唤醒！
echo   现在拿起遥控器在电视上点开 SmartTube 即可秒看！
echo ======================================================
echo.
timeout /t 3
exit
"""

target = r"C:\Users\Administrator\Desktop\🚀 一键唤醒电视代理(Mihomo).bat"
with open(target, "w", encoding="gbk", errors="ignore") as f:
    f.write(bat_content)

print("[+] Desktop shortcut created successfully!")
