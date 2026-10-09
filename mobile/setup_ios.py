"""Generate the iOS project and add what the app needs. Run once on the Mac, from mobile/:

    python3 setup_ios.py

It runs `flutter create` for iOS, then edits ios/Runner/Info.plist:
- the camera and location permission texts (without them iOS closes the app when it asks),
- plain http to the laptop (the server has no HTTPS; App Transport Security blocks it otherwise),
- the local-network text, so a real iPhone may reach the laptop on the same Wi-Fi/hotspot,
- sign in with Google, when GOOGLE_IOS_CLIENT_ID is set (the iOS OAuth client's ID): GIDClientID and
  the reversed client ID as a URL scheme, so Google can hand the person back to the app:

    GOOGLE_IOS_CLIENT_ID=1234-abc.apps.googleusercontent.com python3 setup_ios.py

  The server must accept that ID too: put it in GOOGLE_CLIENT_IDS next to the Web and Android ones.
"""
import os
import plistlib
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLIST = HERE / "ios" / "Runner" / "Info.plist"
TEXTS = {
    "NSCameraUsageDescription": "Take a photo of litter and record the cleanup.",
    "NSLocationWhenInUseUsageDescription": "Put the report on the map and check you are at the spot.",
    "NSLocalNetworkUsageDescription": "Reach the GreenLegacy server on this Wi-Fi.",
}


def main():
    if not PLIST.exists():
        subprocess.run(["flutter", "create", ".", "--platforms=ios", "--org", "krd.greenlegacy",
                        "--project-name", "slemani_green_legacy"], cwd=HERE, check=True)
    with PLIST.open("rb") as f:
        info = plistlib.load(f)
    for key, text in TEXTS.items():
        info.setdefault(key, text)
    ats = info.setdefault("NSAppTransportSecurity", {})
    ats["NSAllowsArbitraryLoads"] = True        # practice build only: http://<laptop>:5000
    ats["NSAllowsLocalNetworking"] = True
    google = os.environ.get("GOOGLE_IOS_CLIENT_ID", "").strip()
    if google:
        info["GIDClientID"] = google
        scheme = ".".join(reversed(google.split(".")))      # com.googleusercontent.apps.1234-abc
        types = info.setdefault("CFBundleURLTypes", [])
        if not any(scheme in t.get("CFBundleURLSchemes", []) for t in types):
            types.append({"CFBundleTypeRole": "Editor", "CFBundleURLSchemes": [scheme]})
    with PLIST.open("wb") as f:
        plistlib.dump(info, f)
    print("iOS project ready:", PLIST)
    if not google:
        print("Note: GOOGLE_IOS_CLIENT_ID is not set, so sign in with Google is not set up on iOS (the rest "
              "works). Run this again with it once the iOS OAuth client exists.")


if __name__ == "__main__":
    main()
