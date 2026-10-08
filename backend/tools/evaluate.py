"""Score the litter model on held-out Slemani photos and print a table for the slides.

    python tools/evaluate.py datasets/slemani/test                       # model from MODEL_PATH etc.
    python tools/evaluate.py DIR --model models/yolov8m-seg.pt --model models/slemani.pt
    python tools/evaluate.py DIR --suggest-bands                         # tune the 1-5 level bands
    python tools/evaluate.py DIR --detector colorblob                    # red-paper rehearsal

DIR holds the photos and labels.csv with columns file,count,level (tools/train.py split writes it;
fill in level by hand). An empty count or level skips that score for the photo. Put a few clean
photos (count 0) in too: they show whether the model invents litter, which would give free points.
"""
import argparse
import csv
import itertools
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ai.detector import ColorBlobDetector, YoloDetector, load_bgr  # noqa: E402
from app.ai.scoring import dirtiness  # noqa: E402
from app.config import Config  # noqa: E402


def read_labels(folder):
    rows = []
    with open(Path(folder) / "labels.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            count = row.get("count", "").strip()
            level = row.get("level", "").strip()
            rows.append({"file": Path(folder) / row["file"],
                         "count": int(count) if count else None,
                         "level": int(level) if level else None})
    if not rows:
        raise SystemExit(f"{folder}/labels.csv has no rows")
    return rows


def run(detector, rows, bands):
    detector.detect(load_bgr(rows[0]["file"]))           # warm-up: the first call loads the model
    out = []
    for row in rows:
        img = load_bgr(row["file"])
        start = time.perf_counter()
        found = detector.detect(img)
        ms = (time.perf_counter() - start) * 1000
        out.append({**row, "pred_count": found.count, "coverage": found.coverage, "ms": ms,
                    "pred_level": dirtiness(found.count, found.coverage, bands)})
    return out


def score(results, bands=None):
    """Numbers for one model. bands re-scores the levels without running the model again."""
    if bands is not None:
        results = [{**r, "pred_level": dirtiness(r["pred_count"], r["coverage"], bands)} for r in results]
    counted = [r for r in results if r["count"] is not None]
    dirty = [r for r in counted if r["count"] > 0]
    clean = [r for r in counted if r["count"] == 0]
    levelled = [r for r in results if r["level"] is not None]
    pct = lambda part, whole: f"{100 * part / whole:.0f}% ({part}/{whole})" if whole else "—"  # noqa: E731
    return {
        "photos": str(len(results)),
        "litter found on dirty photos": pct(sum(r["pred_count"] > 0 for r in dirty), len(dirty)),
        "litter invented on clean photos": pct(sum(r["pred_count"] > 0 for r in clean), len(clean)),
        "count error (mean, items)": f"{statistics.mean(abs(r['pred_count'] - r['count']) for r in counted):.1f}"
                                     if counted else "—",
        "level exact": pct(sum(r["pred_level"] == r["level"] for r in levelled), len(levelled)),
        "level within ±1": pct(sum(abs(r["pred_level"] - r["level"]) <= 1 for r in levelled), len(levelled)),
        "time per photo (ms, median)": f"{statistics.median(r['ms'] for r in results):.0f}",
    }


def suggest_bands(results, current):
    """Count limits for levels 1-4 that best match the human levels (exact first, then ±1)."""
    levelled = [r for r in results if r["level"] is not None]
    if len(levelled) < 5:
        raise SystemExit("fill in the level column for at least 5 photos first")
    counts = sorted({r["pred_count"] for r in levelled} | set(current))
    if len(counts) > 30:                                  # keep the search quick: 30 quantiles
        counts = sorted({counts[round(i * (len(counts) - 1) / 29)] for i in range(30)})

    def quality(bands):
        exact = sum(dirtiness(r["pred_count"], r["coverage"], bands) == r["level"] for r in levelled)
        near = sum(abs(dirtiness(r["pred_count"], r["coverage"], bands) - r["level"]) <= 1 for r in levelled)
        drift = sum(abs(a - b) for a, b in zip(bands, current))
        return exact, near, -drift

    best = max(itertools.combinations(counts, 4), key=quality)
    return best, quality(tuple(current))[:2], quality(best)[:2], len(levelled)


def table(columns):
    names = list(columns)
    keys = list(next(iter(columns.values())))
    lines = ["| | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    lines += [f"| {k} | " + " | ".join(columns[n][k] for n in names) + " |" for k in keys]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder")
    parser.add_argument("--model", action="append", help="a .pt file; repeat to compare models")
    parser.add_argument("--classes", default=None,
                        help="litter classes (default: * with --model, else LITTER_CLASSES)")
    parser.add_argument("--detector", choices=["yolo", "colorblob"], default=os.environ.get("DETECTOR_KIND", "yolo"))
    parser.add_argument("--suggest-bands", action="store_true")
    parser.add_argument("--csv", help="write every photo's result here")
    args = parser.parse_args()

    rows = read_labels(args.folder)
    bands = Config.LEVEL_COUNT_BANDS
    if args.detector == "colorblob":
        detectors = {"colorblob": ColorBlobDetector()}
    elif args.model:
        classes = args.classes or "*"
        detectors = {Path(m).name: YoloDetector(m, classes, Config.DETECT_CONFIDENCE) for m in args.model}
    else:
        detectors = {Path(Config.MODEL_PATH).name: YoloDetector(Config.MODEL_PATH, args.classes or Config.LITTER_CLASSES,
                                                                 Config.DETECT_CONFIDENCE)}

    results = {name: run(det, rows, bands) for name, det in detectors.items()}
    print(f"\n{len(rows)} photos from {args.folder}, level bands {','.join(map(str, bands))}\n")
    print(table({name: score(res) for name, res in results.items()}))

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["model", "file", "count", "pred_count", "level", "pred_level", "ms"])
            for name, res in results.items():
                for r in res:
                    w.writerow([name, r["file"], r["count"], r["pred_count"], r["level"], r["pred_level"],
                                round(r["ms"])])
        print(f"\nper-photo results: {args.csv}")

    if args.suggest_bands:
        name, res = next(iter(results.items()))
        best, before, after, n = suggest_bands(res, bands)
        print(f"\nLevel bands for {name} on {n} hand-levelled photos:")
        print(f"  now      {','.join(map(str, bands)):<12} exact {before[0]}/{n}, within ±1 {before[1]}/{n}")
        print(f"  suggest  {','.join(map(str, best)):<12} exact {after[0]}/{n}, within ±1 {after[1]}/{n}")
        print(f"  use it:  LEVEL_COUNT_BANDS={','.join(map(str, best))} python run.py")


if __name__ == "__main__":
    main()
