"""Generate the Android project and add the permissions the app needs. Run once, from mobile/:

    python setup_android.py

It runs `flutter create` for Android, then edits AndroidManifest.xml to add camera, location
and internet permissions, and allows plain http (the laptop server has no HTTPS).
Works the same on Windows, macOS and Linux.

Sign in with Google needs no file here (no google-services.json: the app passes the Web client ID,
which it gets from the server's /auth/config, as serverClientId). It needs an Android OAuth client in
the same Google Cloud project, made for this package name and the signing key's SHA-1; the script
prints both.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
PACKAGE = "krd.greenlegacy.slemani_green_legacy"     # flutter create --org krd.greenlegacy
PERMISSIONS = [
    "android.permission.INTERNET",
    "android.permission.CAMERA",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
]


def main():
    if not MANIFEST.exists():
        flutter = "flutter.bat" if sys.platform.startswith("win") else "flutter"
        subprocess.run([flutter, "create", ".", "--platforms=android", "--org", "krd.greenlegacy",
                        "--project-name", "slemani_green_legacy"], cwd=HERE, check=True)
    text = MANIFEST.read_text(encoding="utf-8")
    missing = [p for p in PERMISSIONS if p not in text]
    if missing:
        lines = "".join(f'    <uses-permission android:name="{p}"/>\n' for p in missing)
        text = text.replace("<application", lines + "    <application", 1)
    if "usesCleartextTraffic" not in text:
        text = text.replace("<application", '<application android:usesCleartextTraffic="true"', 1)
    MANIFEST.write_text(text, encoding="utf-8")
    print("Android project ready:", MANIFEST)
    keystore = (r"%USERPROFILE%\.android\debug.keystore" if sys.platform.startswith("win")
                else "~/.android/debug.keystore")
    print("\nSign in with Google: in Google Cloud Console > Credentials, create an OAuth client of type Android")
    print(f"  package name: {PACKAGE}")
    print("  SHA-1 of the debug signing key (the line 'SHA1:' from):")
    print(f"    keytool -list -v -keystore {keystore} -alias androiddebugkey -storepass android -keypass android")
    print("Then put that client's ID in the server's GOOGLE_CLIENT_IDS, next to the Web client's ID.")


if __name__ == "__main__":
    main()
