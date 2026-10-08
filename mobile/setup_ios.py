"""Generate the iOS project and add what the app needs. Run once on the Mac, from mobile/:

    python3 setup_ios.py

It runs `flutter create` for iOS, then edits ios/Runner/Info.plist:
- the camera and location permission texts (without them iOS closes the app when it asks),
- plain http to the laptop (the server has no HTTPS; App Transport Security blocks it otherwise),
- the local-network text, so a real iPhone may reach the laptop on the same Wi-Fi/hotspot.
"""
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
    with PLIST.open("wb") as f:
        plistlib.dump(info, f)
    print("iOS project ready:", PLIST)


if __name__ == "__main__":
    main()
