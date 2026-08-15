#!/usr/bin/env python3
"""
Android TV YouTube & Native Proxy Unified Management CLI Tool.
Interactive terminal dashboard + script dispatcher for Mainland China Android TV setup.
"""

import os
import sys
import subprocess
import time
import argparse
import webbrowser
import json
import urllib.request
import re

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")
sys.path.insert(0, SCRIPTS_DIR)

DEFAULT_TV_IP = "192.168.0.116"

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

def auto_detect_tv_ip():
    adb = get_adb_cmd()
    r = subprocess.run([adb, "devices"], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    lines = [l.split("\t")[0].strip() for l in r.stdout.splitlines() if "\tdevice" in l]
    for l in lines:
        if ":" in l:
            return l.split(":")[0]
    return DEFAULT_TV_IP

def banner():
    print(r"""
======================================================================
  📺 Android TV YouTube & Native Proxy Daemon Manager
  💡 "Believe that programming can change everything."
======================================================================
    """)

def run_diagnostic(tv_ip):
    from diag_tv import check_adb, check_tv_daemons, check_tv_proxy_api, check_youtube_speed
    print(f"\n[*] 正在对电视 ({tv_ip}) 进行全面体检...\n")
    adb_ok = check_adb(tv_ip)
    if adb_ok:
        check_tv_daemons(tv_ip)
        check_tv_proxy_api(tv_ip)
        check_youtube_speed(tv_ip)
    input("\n按回车键返回主菜单...")

def run_setup(tv_ip):
    from setup_tv import setup_tv
    sub_url = input("\n请输入你的机场 Clash 订阅链接 (直接回车保持现有配置): ").strip()
    setup_tv(tv_ip, sub_url=sub_url if sub_url else None)
    input("\n按回车键返回主菜单...")

def run_sub_update(tv_ip):
    from update_subscription import fetch_subscription, optimize_config_for_tv, push_config_to_tv, reload_mihomo_daemon, auto_select_best_node
    sub_url = input("\n请输入新的机场 Clash 订阅链接: ").strip()
    if not sub_url:
        print("[!] 订阅链接不能为空！")
        return
    try:
        raw_yaml = fetch_subscription(sub_url)
        opt_yaml = optimize_config_for_tv(raw_yaml)
        adb = get_adb_cmd()
        push_config_to_tv(tv_ip, opt_yaml, adb_path=adb)
        reload_mihomo_daemon(tv_ip, adb_path=adb)
        auto_select_best_node(tv_ip)
        print("\n[✓] 订阅更新与节点优选全部完成！")
    except Exception as e:
        print(f"[!] 更新失败: {e}")
    input("\n按回车键返回主菜单...")

def run_benchmark(tv_ip):
    from smart_node_selector import benchmark_and_switch
    benchmark_and_switch(tv_ip)
    input("\n按回车键返回主菜单...")

def run_fix_proxy(tv_ip):
    from fix_smarttube_proxy import fix_smarttube
    fix_smarttube(tv_ip)
    input("\n按回车键返回主菜单...")

def open_web_dashboard(tv_ip):
    url = f"https://yacd.metacubex.one/?hostname={tv_ip}&port=9090&secret="
    print(f"\n[*] 正在浏览器中打开可视化控制面板: {url}")
    webbrowser.open(url)
    input("\n按回车键返回主菜单...")

def run_remote_control(tv_ip):
    adb = get_adb_cmd()
    target = f"{tv_ip}:5555"
    print("\n" + "=" * 60)
    print(" 🎮 电脑键盘无线遥控器模式 (输入按键后回车生效)")
    print("   w: 上 | s: 下 | a: 左 | d: 右 | j / 空格: 确定")
    print("   b: 返回 | h: 主页 | q: 退出遥控模式")
    print("=" * 60)
    
    key_map = {
        'w': '19', 's': '20', 'a': '21', 'd': '22',
        'j': '23', ' ': '23', 'b': '4', 'h': '3'
    }
    
    while True:
        k = input("Remote > ").strip().lower()
        if k == 'q':
            break
        if k in key_map:
            subprocess.run([adb, "-s", target, "shell", "input", "keyevent", key_map[k]], capture_output=True)
            print(f"Sent keycode {key_map[k]}")
        else:
            print("未知按键。输入 w/s/a/d (移动), j (确定), b (返回), q (退出)")

def main_menu():
    tv_ip = auto_detect_tv_ip()
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        banner()
        print(f" 当前目标电视 IP: \033[92m{tv_ip}\033[0m (如需修改请输入 0)\n")
        print(" [1] 🚀 一键全自动部署 (安装SmartTube + 部署后台守护进程 + 导入订阅)")
        print(" [2] 📡 电视环境一键全面体检 (检查ADB、Mihomo进程、API、YouTube连通性)")
        print(" [3] 🔄 一键更新机场订阅并热重载 (自动测速优选最快节点)")
        print(" [4] ⚡ 实时并发节点测速与智能优选 (将YouTube出口切换至极速专线)")
        print(" [5] 🛠️ 一键修复 SmartTube 代理死锁 (消除20秒超时卡死)")
        print(" [6] 📊 在浏览器中打开可视化控制面板 (Yacd Dashboard)")
        print(" [7] 🎮 电脑无线遥控器模式 (用电脑键盘控制电视)")
        print(" [0] ⚙️ 修改目标电视 IP 地址")
        print(" [q] 🚪 退出程序\n")

        choice = input("请选择功能 [1-7/0/q]: ").strip()
        if choice == '1':
            run_setup(tv_ip)
        elif choice == '2':
            run_diagnostic(tv_ip)
        elif choice == '3':
            run_sub_update(tv_ip)
        elif choice == '4':
            run_benchmark(tv_ip)
        elif choice == '5':
            run_fix_proxy(tv_ip)
        elif choice == '6':
            open_web_dashboard(tv_ip)
        elif choice == '7':
            run_remote_control(tv_ip)
        elif choice == '0':
            new_ip = input("请输入新的电视 IP 地址: ").strip()
            if new_ip:
                tv_ip = new_ip
        elif choice.lower() == 'q':
            print("\n感谢使用！祝你观影愉快！🍿")
            break

if __name__ == "__main__":
    main_menu()
