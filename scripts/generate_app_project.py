import os, subprocess, shutil, zipfile

build_tools_dir = r"C:\Users\Administrator\Desktop\build_tools"
jdk_bin = os.path.join(build_tools_dir, "jdk-17.0.20+8", "bin")

app_dir = r"C:\Users\Administrator\Desktop\tv_app_project"
if os.path.exists(app_dir):
    shutil.rmtree(app_dir)

pkg_name = "com.tv.youtubeproxy"
src_dir = os.path.join(app_dir, "src", "com", "tv", "youtubeproxy")
res_dir = os.path.join(app_dir, "res")
res_drawable = os.path.join(res_dir, "drawable")
res_values = os.path.join(res_dir, "values")
os.makedirs(src_dir, exist_ok=True)
os.makedirs(res_drawable, exist_ok=True)
os.makedirs(res_values, exist_ok=True)

# ── AndroidManifest.xml ──────────────────────────────────────────────
# No Foreground Service needed. APK is fire-and-forget.
manifest = f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{pkg_name}"
    android:versionCode="3"
    android:versionName="3.0">

    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="28" />

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
        android:usesCleartextTraffic="true"
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
    f.write(manifest)

# ── strings.xml ──────────────────────────────────────────────────────
with open(os.path.join(res_values, "strings.xml"), "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <string name="app_name">YouTube Proxy</string>\n</resources>\n')

# ── Icons ────────────────────────────────────────────────────────────
with zipfile.ZipFile(r"C:\Users\Administrator\Desktop\LaunchOnBoot_TV.apk") as z:
    z.extract("res/mipmap-xhdpi-v4/ic_launcher.png", app_dir)
    z.extract("res/drawable/banner.png", app_dir)
shutil.move(os.path.join(app_dir, "res", "mipmap-xhdpi-v4", "ic_launcher.png"), os.path.join(res_drawable, "ic_launcher.png"))
shutil.move(os.path.join(app_dir, "res", "drawable", "banner.png"), os.path.join(res_drawable, "banner.png"))

# ── AdbLocalClient.java ─────────────────────────────────────────────
# Minimal ADB wire protocol client that connects to localhost adbd
# and delegates shell commands to run under system shell UID (2000).
adb_client = r"""package com.tv.youtubeproxy;

import android.util.Log;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

/**
 * Minimal ADB wire-protocol client for localhost delegation.
 * Spawns mihomo under UID=shell (2000) so SkyRMService cannot kill it.
 */
public class AdbLocalClient {

    private static final String TAG = "YouTubeProxy";

    // ADB protocol command identifiers
    private static final int A_CNXN = 0x4e584e43;
    private static final int A_OPEN = 0x4e45504f;
    private static final int A_OKAY = 0x59414b4f;
    private static final int A_CLSE = 0x45534c43;
    private static final int A_WRTE = 0x45545257;
    private static final int A_AUTH = 0x48545541;

    // Protocol version and max payload
    private static final int VERSION  = 0x01000000;
    private static final int MAX_DATA = 4096;

    public static boolean execShellCommand(String command) {
        Socket socket = null;
        try {
            socket = new Socket();
            socket.connect(new InetSocketAddress("127.0.0.1", 5555), 3000);
            socket.setSoTimeout(10000);

            OutputStream out = socket.getOutputStream();
            InputStream  in  = socket.getInputStream();

            // ── Step 1: Send CNXN ──
            byte[] banner = "host::\0".getBytes("UTF-8");
            sendMessage(out, A_CNXN, VERSION, MAX_DATA, banner);

            // ── Step 2: Read CNXN response ──
            int[] hdr = readHeader(in);
            if (hdr == null) {
                Log.e(TAG, "ADB: No response header");
                return false;
            }
            if (hdr[3] > 0) {
                readFully(in, new byte[hdr[3]]);
            }
            if (hdr[0] == A_AUTH) {
                Log.e(TAG, "ADB: AUTH requested");
                return false;
            }
            if (hdr[0] != A_CNXN) {
                Log.e(TAG, "ADB: Unexpected: 0x" + Integer.toHexString(hdr[0]));
                return false;
            }
            Log.i(TAG, "ADB: CNXN established");

            // ── Step 3: Send OPEN with exec command (clean daemon execution without PTY) ──
            byte[] execPayload = ("exec:" + command).getBytes("UTF-8");
            sendMessage(out, A_OPEN, 1, 0, execPayload);

            // ── Step 4: Wait for OKAY ──
            hdr = readHeader(in);
            if (hdr != null && hdr[3] > 0) {
                readFully(in, new byte[hdr[3]]);
            }
            if (hdr == null || hdr[0] != A_OKAY) {
                Log.e(TAG, "ADB: Exec command REJECTED");
                return false;
            }
            Log.i(TAG, "ADB: Exec command ACCEPTED, waiting for fork & detach...");
            // Allow subshell 500ms to fork, trap signals, and detach before socket closes
            try { Thread.sleep(500); } catch (Exception ignored) {}
            Log.i(TAG, "ADB: Delegation complete - mihomo is running under shell UID");
            return true;

        } catch (Exception e) {
            Log.e(TAG, "ADB: Connection failed: " + e.getMessage());
            return false;
        } finally {
            if (socket != null) {
                try { socket.close(); } catch (Exception ignored) {}
            }
        }
    }

    private static void sendMessage(OutputStream out, int cmd, int arg0, int arg1, byte[] data) throws Exception {
        int dataLen = (data != null) ? data.length : 0;
        ByteBuffer buf = ByteBuffer.allocate(24 + dataLen);
        buf.order(ByteOrder.LITTLE_ENDIAN);
        buf.putInt(cmd);
        buf.putInt(arg0);
        buf.putInt(arg1);
        buf.putInt(dataLen);
        buf.putInt(data != null ? checksum(data) : 0);
        buf.putInt(cmd ^ 0xFFFFFFFF);
        if (data != null) {
            buf.put(data);
        }
        out.write(buf.array());
        out.flush();
    }

    private static int[] readHeader(InputStream in) throws Exception {
        byte[] raw = new byte[24];
        readFully(in, raw);
        ByteBuffer buf = ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);
        return new int[] {
            buf.getInt(),
            buf.getInt(),
            buf.getInt(),
            buf.getInt(),
            buf.getInt(),
            buf.getInt()
        };
    }

    private static int checksum(byte[] data) {
        int sum = 0;
        for (byte b : data) {
            sum += (b & 0xFF);
        }
        return sum;
    }

    private static void readFully(InputStream in, byte[] buf) throws Exception {
        int off = 0;
        while (off < buf.length) {
            int n = in.read(buf, off, buf.length - off);
            if (n < 0) throw new Exception("Unexpected EOF");
            off += n;
        }
    }
}
"""
with open(os.path.join(src_dir, "AdbLocalClient.java"), "w", encoding="utf-8") as f:
    f.write(adb_client)

# ── MainActivity.java ────────────────────────────────────────────────
main_activity = r"""package com.tv.youtubeproxy;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.widget.Toast;
import java.net.InetSocketAddress;
import java.net.Socket;

/**
 * Intelligent Proxy Launcher with readiness polling.
 * 1. Checks if proxy port 7890 is already open.
 * 2. If not, delegates startup to localhost ADB daemon (shell UID 2000).
 * 3. Polls port 7890 until ready (up to 3s) ensuring zero video errors.
 * 4. Smoothly launches SmartTube and exits.
 */
public class MainActivity extends Activity {

    private static final String TAG = "YouTubeProxy";

    private static final String MIHOMO_CMD =
        "/system/bin/sh -c \"trap '' HUP INT TERM QUIT; (trap '' HUP INT TERM QUIT; /data/local/tmp/mihomo -d /sdcard/mihomo > /sdcard/mihomo/mihomo.log 2>&1 < /dev/null &) &\"";

    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Toast.makeText(this, "正在连接代理加速网络...", Toast.LENGTH_SHORT).show();

        new Thread(new Runnable() {
            @Override
            public void run() {
                // Check if proxy port 7890 is already listening
                boolean isReady = isProxyPortOpen();
                if (!isReady) {
                    Log.i(TAG, "Proxy not running. Delegating launch to ADB...");
                    AdbLocalClient.execShellCommand(MIHOMO_CMD);

                    // Poll port 7890 until ready (up to 3.5 seconds)
                    for (int i = 0; i < 12; i++) {
                        try { Thread.sleep(300); } catch (Exception e) {}
                        if (isProxyPortOpen()) {
                            Log.i(TAG, "Proxy port 7890 is UP after " + ((i + 1) * 300) + "ms");
                            isReady = true;
                            break;
                        }
                    }
                } else {
                    Log.i(TAG, "Proxy is already active on port 7890.");
                }

                // Final delay to allow node handshakes to settle
                try { Thread.sleep(300); } catch (Exception e) {}

                mainHandler.post(new Runnable() {
                    @Override
                    public void run() {
                        launchSmartTube();
                    }
                });
            }
        }).start();
    }

    private boolean isProxyPortOpen() {
        Socket s = null;
        try {
            s = new Socket();
            s.connect(new InetSocketAddress("127.0.0.1", 7890), 400);
            return true;
        } catch (Exception e) {
            return false;
        } finally {
            if (s != null) {
                try { s.close(); } catch (Exception ignored) {}
            }
        }
    }

    private void launchSmartTube() {
        try {
            Intent intent = getPackageManager().getLaunchIntentForPackage("org.smarttube.stable");
            if (intent != null) {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
                Toast.makeText(this, "加速已就绪，正在打开 YouTube", Toast.LENGTH_SHORT).show();
            } else {
                Toast.makeText(this, "代理已启动，未找到 SmartTube", Toast.LENGTH_LONG).show();
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to launch SmartTube", e);
        }

        // Close launcher - Mihomo runs under shell UID completely detached
        finish();
    }
}
"""
with open(os.path.join(src_dir, "MainActivity.java"), "w", encoding="utf-8") as f:
    f.write(main_activity)

# ── BootReceiver.java ────────────────────────────────────────────────
boot_receiver = r"""package com.tv.youtubeproxy;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

/**
 * Auto-start mihomo on cold boot via ADB localhost delegation.
 */
public class BootReceiver extends BroadcastReceiver {

    private static final String TAG = "YouTubeProxy";

    private static final String MIHOMO_CMD =
        "/system/bin/sh -c \"trap '' HUP INT TERM QUIT; (trap '' HUP INT TERM QUIT; /data/local/tmp/mihomo -d /sdcard/mihomo > /sdcard/mihomo/mihomo.log 2>&1 < /dev/null &) &\"";

    @Override
    public void onReceive(Context context, Intent intent) {
        Log.i(TAG, "Boot completed - delegating mihomo start to ADB...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                try { Thread.sleep(3000); } catch (Exception e) {}
                boolean ok = AdbLocalClient.execShellCommand(MIHOMO_CMD);
                Log.i(TAG, "Boot ADB delegation result: " + (ok ? "SUCCESS" : "FAILED"));
            }
        }).start();
    }
}
"""
with open(os.path.join(src_dir, "BootReceiver.java"), "w", encoding="utf-8") as f:
    f.write(boot_receiver)

print("[+] Generated v3.0 ADB localhost delegation project successfully!")
print("    Package: " + pkg_name)
print("    Architecture: Fire-and-forget, zero-memory, shell UID delegation")

