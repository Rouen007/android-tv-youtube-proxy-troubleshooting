import os, subprocess, shutil, zipfile

build_tools_dir = r"C:\Users\Administrator\Desktop\build_tools"
jdk_bin = os.path.join(build_tools_dir, "jdk-17.0.20+8", "bin")
javac = os.path.join(jdk_bin, "javac.exe")
java = os.path.join(jdk_bin, "java.exe")
d8_jar = os.path.join(build_tools_dir, "d8.jar")
android_jar = os.path.join(build_tools_dir, "android.jar")
aapt2 = os.path.join(build_tools_dir, "aapt2.exe")
signer_jar = os.path.join(build_tools_dir, "uber-apk-signer.jar")

app_dir = r"C:\Users\Administrator\Desktop\tv_app_project"
if os.path.exists(app_dir):
    shutil.rmtree(app_dir)

src_dir = os.path.join(app_dir, "src", "com", "tv", "youtubeproxy")
res_dir = os.path.join(app_dir, "res")
res_drawable = os.path.join(res_dir, "drawable")
res_values = os.path.join(res_dir, "values")
os.makedirs(src_dir, exist_ok=True)
os.makedirs(res_drawable, exist_ok=True)
os.makedirs(res_values, exist_ok=True)

# 1. AndroidManifest.xml
manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.tv.youtubeproxy"
    android:versionCode="1"
    android:versionName="1.0">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    <uses-feature android:name="android.software.leanback" android:required="false" />
    <uses-feature android:name="android.hardware.touchscreen" android:required="false" />

    <application
        android:label="@string/app_name"
        android:icon="@drawable/ic_launcher"
        android:banner="@drawable/banner"
        android:isGame="false"
        android:extractNativeLibs="true">
        
        <activity
            android:name=".MainActivity"
            android:label="@string/app_name"
            android:theme="@android:style/Theme.Translucent.NoTitleBar.Fullscreen"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
                <category android:name="android.intent.category.LEANBACK_LAUNCHER" />
            </intent-filter>
        </activity>

        <receiver
            android:name=".BootReceiver"
            android:enabled="true"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
                <action android:name="android.intent.action.QUICKBOOT_POWERON" />
            </intent-filter>
        </receiver>

    </application>
</manifest>
"""
with open(os.path.join(app_dir, "AndroidManifest.xml"), "w", encoding="utf-8") as f:
    f.write(manifest_content)

# 2. strings.xml
strings_content = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">启动 YouTube</string>
</resources>
"""
with open(os.path.join(res_values, "strings.xml"), "w", encoding="utf-8") as f:
    f.write(strings_content)

# 3. Copy Icon from SmartTube or ADBKeyboard
with zipfile.ZipFile(r"C:\Users\Administrator\Desktop\LaunchOnBoot_TV.apk") as z:
    z.extract("res/mipmap-xhdpi-v4/ic_launcher.png", app_dir)
    z.extract("res/drawable/banner.png", app_dir)

shutil.move(os.path.join(app_dir, "res", "mipmap-xhdpi-v4", "ic_launcher.png"), os.path.join(res_drawable, "ic_launcher.png"))
shutil.move(os.path.join(app_dir, "res", "drawable", "banner.png"), os.path.join(res_drawable, "banner.png"))

# 4. Java source files
main_activity = """package com.tv.youtubeproxy;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.widget.Toast;
import java.io.File;

public class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        try {
            String nativeLib = getApplicationInfo().nativeLibraryDir + "/libmihomo.so";
            File f = new File(nativeLib);
            if (f.exists()) {
                f.setExecutable(true, false);
            }
            
            // Execute native mihomo daemon if not already running
            String[] cmd = {
                "/system/bin/sh", "-c",
                "if ! ps -ef 2>/dev/null | grep -v grep | grep -q mihomo; then " +
                "nohup " + nativeLib + " -d /sdcard/mihomo > /sdcard/mihomo/mihomo.log 2>&1 & " +
                "fi"
            };
            Runtime.getRuntime().exec(cmd);
        } catch (Exception e) {}

        // Launch SmartTube
        try {
            Intent intent = getPackageManager().getLaunchIntentForPackage("org.smarttube.stable");
            if (intent != null) {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
            } else {
                Toast.makeText(this, "正在启动后台代理...", Toast.LENGTH_SHORT).show();
            }
        } catch (Exception e) {}

        finish();
    }
}
"""
with open(os.path.join(src_dir, "MainActivity.java"), "w", encoding="utf-8") as f:
    f.write(main_activity)

boot_receiver = """package com.tv.youtubeproxy;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import java.io.File;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        try {
            String nativeLib = context.getApplicationInfo().nativeLibraryDir + "/libmihomo.so";
            File f = new File(nativeLib);
            if (f.exists()) {
                f.setExecutable(true, false);
            }
            String[] cmd = {
                "/system/bin/sh", "-c",
                "nohup " + nativeLib + " -d /sdcard/mihomo > /sdcard/mihomo/mihomo.log 2>&1 &"
            };
            Runtime.getRuntime().exec(cmd);
        } catch (Exception e) {}
    }
}
"""
with open(os.path.join(src_dir, "BootReceiver.java"), "w", encoding="utf-8") as f:
    f.write(boot_receiver)

print("[+] Project files generated successfully!")
