"""The image half of the cleanup verification chain (the API runs the database checks first:
challenge, GPS radius and repeated media). Order matters: the first failure stops the chain
and becomes the reason shown to the user.

    4. static frames   — a real video has motion; identical frames are a still photo
    5. instruction     — the bin QR appears where the random instruction asked
    6. same place      — the non-QR frames match the before photo (ORB inliers)
    7. litter gone     — YOLOv8 counts on the best-matching frames drop by ~80%
"""
from dataclasses import dataclass, field

from .detector import load_bgr
from .hashing import hamming
from .qr import instruction_followed, read_qr
from .same_place import orb_inliers


@dataclass
class ChainResult:
    verdict: str                 # verified | review | rejected
    reason_code: str
    litter_after: int = None
    similarity: float = None
    details: dict = field(default_factory=dict)
    best_frame: int = None       # index of the frame that best shows the spot (for reviewers)


def qr_flags_for(frames, prefix):
    """Which frames show a bin QR sticker. The API needs this before the repeat check: two honest
    cleanups at the same bin film the same sticker, so QR frames must not count as reused media."""
    return [read_qr(f, prefix) is not None for f in frames]


def analyse_cleanup(before_photo, before_count, frames, frame_hashes, instruction, detector, cfg,
                    qr_flags=None):
    images = [load_bgr(f) for f in frames]

    # 4. static frames: every frame identical means a still image was submitted, not a video
    if max(hamming(frame_hashes[0], h) for h in frame_hashes) == 0:
        return ChainResult("rejected", "static_frames")

    # 5. instruction
    if qr_flags is None:
        qr_flags = qr_flags_for(images, cfg["QR_PREFIX"])
    if not instruction_followed(qr_flags, instruction):
        return ChainResult("rejected", "instruction_not_followed", details={"qr_flags": qr_flags})

    # 6. same place: compare the before photo with every frame that does not show the QR sticker
    scene = [(i, img) for i, img in enumerate(images) if not qr_flags[i]]
    scored = sorted(((orb_inliers(before_photo, img), i) for i, img in scene), reverse=True)
    best_inliers = scored[0][0] if scored else 0
    details = {"qr_flags": qr_flags, "inliers": {i: s for s, i in scored}}

    # 7. litter gone: count on the three frames that best match the spot
    best_frames = [images[i] for _s, i in scored[:3]]
    litter_after = max((detector.detect(img).count for img in best_frames), default=0)
    drop = 1 - (litter_after / before_count) if before_count else 1.0
    details["drop"] = round(drop, 2)

    best = scored[0][1] if scored else None
    if best_inliers < cfg["SAME_PLACE_MIN_INLIERS"]:
        verdict, code = "review", "same_place_unsure"
    elif drop >= cfg["LITTER_DROP_VERIFIED"]:
        verdict, code = "verified", "verified"
    elif drop >= cfg["LITTER_DROP_REVIEW"]:
        verdict, code = "review", "litter_partly_remaining"
    else:
        verdict, code = "rejected", "litter_still_there"
    return ChainResult(verdict, code, litter_after, best_inliers, details, best)
