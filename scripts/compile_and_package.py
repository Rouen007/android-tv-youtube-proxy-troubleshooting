import os, subprocess, shutil, zipfile, glob

build_tools_dir = r"C:\Users\Administrator\Desktop\build_tools"
jdk_bin = os.path.join(build_tools_dir, "jdk-17.0.20+8", "bin")
javac = os.path.join(jdk_bin, "javac.exe")
java = os.path.join(jdk_bin, "java.exe")
d8_jar = os.path.join(build_tools_dir, "d8.jar")
android_jar = os.path.join(build_tools_dir, "android.jar")
aapt2 = os.path.join(build_tools_dir, "aapt2.exe")
signer_jar = os.path.join(build_tools_dir, "uber-apk-signer.jar")

app_dir = r"C:\Users\Administrator\Desktop\tv_app_project"
bin_dir = os.path.join(app_dir, "bin")
os.makedirs(bin_dir, exist_ok=True)

# 1. Compile Resources with aapt2
print("[1/5] Compiling resources with aapt2...")
res_zip = os.path.join(bin_dir, "res.zip")
r = subprocess.run([
    aapt2, "compile", "--dir", os.path.join(app_dir, "res"),
    "-o", res_zip
], capture_output=True, text=True)
print(r.stdout, r.stderr)

# 2. Link resources and generate R.java + unaligned APK
print("[2/5] Linking resources and generating R.java...")
unaligned_apk = os.path.join(bin_dir, "unaligned.apk")
r_java_dir = os.path.join(app_dir, "gen")
os.makedirs(r_java_dir, exist_ok=True)

# Find all compiled flats in res_zip
flat_files = []
with zipfile.ZipFile(res_zip, 'r') as z:
    z.extractall(os.path.join(bin_dir, "flats"))

flats = glob.glob(os.path.join(bin_dir, "flats", "*.flat"))
link_cmd = [
    aapt2, "link",
    "-I", android_jar,
    "--manifest", os.path.join(app_dir, "AndroidManifest.xml"),
    "--java", r_java_dir,
    "-o", unaligned_apk,
    "--auto-add-overlay"
] + flats

r = subprocess.run(link_cmd, capture_output=True, text=True)
print(r.stdout, r.stderr)

# 3. Compile Java sources with javac
print("[3/5] Compiling Java classes with javac...")
classes_dir = os.path.join(bin_dir, "classes")
os.makedirs(classes_dir, exist_ok=True)

java_files = glob.glob(os.path.join(app_dir, "src", "**", "*.java"), recursive=True) + \
             glob.glob(os.path.join(r_java_dir, "**", "*.java"), recursive=True)

javac_cmd = [
    javac,
    "-cp", android_jar,
    "-d", classes_dir,
    "-source", "1.8",
    "-target", "1.8"
] + java_files

r = subprocess.run(javac_cmd, capture_output=True, text=True)
print(r.stdout, r.stderr)

# 4. Dex classes with d8
print("[4/5] Dexing classes with D8...")
class_files = glob.glob(os.path.join(classes_dir, "**", "*.class"), recursive=True)
dex_cmd = [
    java, "-cp", d8_jar, "com.android.tools.r8.D8",
    "--lib", android_jar,
    "--output", bin_dir
] + class_files

r = subprocess.run(dex_cmd, capture_output=True, text=True)
print(r.stdout, r.stderr)

# Add classes.dex into unaligned.apk + add native libmihomo.so
print("[4.5/5] Adding classes.dex and libmihomo.so into APK...")
mihomo_bin = r"e:\AiDoc\release_assets\mihomo"

with zipfile.ZipFile(unaligned_apk, 'a') as z:
    z.write(os.path.join(bin_dir, "classes.dex"), "classes.dex")
    # Native libs for arm64-v8a and armeabi-v7a
    z.write(mihomo_bin, "lib/arm64-v8a/libmihomo.so")
    z.write(mihomo_bin, "lib/armeabi-v7a/libmihomo.so")

# 5. Sign APK with uber-apk-signer
print("[5/5] Signing APK with uber-apk-signer...")
out_dir = r"C:\Users\Administrator\Desktop\output_apk"
os.makedirs(out_dir, exist_ok=True)

sign_cmd = [
    java, "-jar", signer_jar,
    "-a", unaligned_apk,
    "-o", out_dir
]

r = subprocess.run(sign_cmd, capture_output=True, text=True)
print(r.stdout, r.stderr)

# Output final APK path
signed_apk = glob.glob(os.path.join(out_dir, "*.apk"))[0]
dest_final = r"C:\Users\Administrator\Desktop\YouTube启动器.apk"
shutil.copy(signed_apk, dest_final)
print(f"[+] SUCCESS! Final Signed APK generated at: {dest_final}")
print(f"[+] APK File Size: {os.path.getsize(dest_final)} bytes")
