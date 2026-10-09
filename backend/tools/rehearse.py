"""Run the demo loop against a running server with synthetic images, and print every step.

    OTP_REQUIRED=0 DETECTOR_KIND=colorblob python run.py   # terminal 1 (red rectangles count as litter;
                                                            # its people sign up without an email code)
    python tools/rehearse.py                      # terminal 2

Then open http://localhost:5000/dashboard (staff 07500000000 / staff1234) and watch it change.
"""
import random
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import synthetic  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
SPOT = (35.5631, 45.4335)   # Hawari Shar park area (approximate)


def step(title, response):
    data = response.json()
    message = data.get("message") or data.get("reason_code") or data.get("verdict") or ""
    print(f"  {title:<34} {response.status_code}  {message}")
    return data


def signup(name):
    phone = "07" + random.choice("5789") + "".join(random.choice("0123456789") for _ in range(8))
    r = requests.post(f"{BASE}/auth/signup", json={"name": name, "phone": phone,
                                                    "password": "secret123", "neighbourhood_id": 2})
    if r.status_code == 401:
        sys.exit("The server wants an email code for every new account: start it with OTP_REQUIRED=0 "
                 "for this rehearsal (see the top of this file).")
    r.raise_for_status()
    return {"Authorization": "Bearer " + r.json()["token"]}


def report(headers, image, lat, lon):
    files = {"photo": ("photo.jpg", synthetic.encode(image), "image/jpeg")}
    return requests.post(f"{BASE}/reports", headers=headers, files=files, data={"lat": lat, "lon": lon})


def cleanup(headers, report_id, challenge_id, frames, lat, lon):
    files = [("frames", (f"f{i}.jpg", synthetic.encode(f), "image/jpeg")) for i, f in enumerate(frames)]
    return requests.post(f"{BASE}/reports/{report_id}/cleanup", headers=headers, files=files,
                         data={"lat": lat, "lon": lon, "challenge_id": challenge_id})


def main():
    seed = random.randint(1, 10_000)
    scene = synthetic.place(seed)
    lat, lon = SPOT[0] + random.uniform(-0.004, 0.004), SPOT[1] + random.uniform(-0.004, 0.004)

    print("1. A citizen reports a littered spot")
    reporter, cleaner = signup("ئاراس"), signup("شنە")
    data = step("report", report(reporter, synthetic.with_litter(scene, 9, seed), lat, lon))
    rid = data["report"]["id"]
    print(f"     dirtiness {data['report']['dirtiness']}, litter {data['report']['litter_count']}, "
          f"pending points {data['points_pending']}")

    print("2. The reporter tries to clean their own spot")
    step("claim by reporter", requests.post(f"{BASE}/reports/{rid}/claim", headers=reporter))

    print("3. Another citizen claims it and gets a random instruction")
    ch = step("claim", requests.post(f"{BASE}/reports/{rid}/claim", headers=cleaner))
    print(f"     instruction: {ch['instruction']} — {ch['instruction_text']}")

    print("4. Wrong order first (fraud-ish), then the real after-video")
    wrong = "qr_last" if ch["instruction"] == "qr_first" else "qr_first"
    step("cleanup, wrong order", cleanup(cleaner, rid, ch["id"], synthetic.cleanup_frames(scene, wrong), lat, lon))
    ch = requests.post(f"{BASE}/reports/{rid}/claim", headers=cleaner).json()
    frames = synthetic.cleanup_frames(scene, ch["instruction"])
    result = step("cleanup, correct", cleanup(cleaner, rid, ch["id"], frames, lat, lon))
    print(f"     points now {result.get('points_now')}, pending {result.get('points_pending')}")

    print("5. The same video reused on another spot")
    scene2 = synthetic.place(seed + 1)
    lat2 = lat + 0.01
    rid2 = report(signup("کاوە"), synthetic.with_litter(scene2, 4, seed), lat2, lon).json()["report"]["id"]
    ch2 = requests.post(f"{BASE}/reports/{rid2}/claim", headers=cleaner).json()
    step("cleanup with old video", cleanup(cleaner, rid2, ch2["id"], frames, lat2, lon))

    print("6. A cleanup filmed somewhere else goes to the review queue")
    ch2 = requests.post(f"{BASE}/reports/{rid2}/claim", headers=cleaner).json()
    elsewhere = synthetic.cleanup_frames(synthetic.place(seed + 2), ch2["instruction"])
    step("cleanup, other place", cleanup(cleaner, rid2, ch2["id"], elsewhere, lat2, lon))

    me = requests.get(f"{BASE}/me", headers=cleaner).json()
    print(f"\nCleaner: released {me['released']}, pending {me['pending']}")
    print(f"Dashboard: {BASE}/dashboard")


if __name__ == "__main__":
    main()
