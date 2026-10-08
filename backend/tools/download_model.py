"""Download a YOLOv8 model into backend/models/.

    python tools/download_model.py            # stock yolov8n.pt (COCO: bottles, cups... the fallback)
    python tools/download_model.py --trash    # the public trash model from Hugging Face

The trash model is turhancan97/yolov8-segment-trash-detection (YOLOv8 segmentation, MIT licence,
tagged TACO / TrashNet / COCO). Name it and TACO (CC BY 4.0) on the slides. Then start the server with
    MODEL_PATH=models/yolov8m-seg.pt LITTER_CLASSES=* python run.py
.pt files are pickles: only load ones from sources you trust.
"""
import argparse
import json
import urllib.request
from pathlib import Path

MODELS = Path(__file__).resolve().parent.parent / "models"
STOCK_URL = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt"
TRASH_REPO = "turhancan97/yolov8-segment-trash-detection"


def fetch(url, target):
    if target.exists():
        print("already there:", target)
        return target
    MODELS.mkdir(exist_ok=True)
    print("downloading", url)
    partial = target.with_suffix(".part")
    urllib.request.urlretrieve(url, partial)
    partial.rename(target)
    print("saved", target, target.stat().st_size // 1024, "KB")
    return target


def trash_files(repo):
    """The .pt files in a Hugging Face model repo (the repo decides the file name, not us)."""
    with urllib.request.urlopen(f"https://huggingface.co/api/models/{repo}", timeout=30) as res:
        info = json.load(res)
    return [s["rfilename"] for s in info.get("siblings", []) if s["rfilename"].endswith(".pt")]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trash", action="store_true", help="download the Hugging Face trash model")
    parser.add_argument("--repo", default=TRASH_REPO, help="Hugging Face repo for --trash")
    args = parser.parse_args()

    if not args.trash:
        fetch(STOCK_URL, MODELS / "yolov8n.pt")
        return
    files = trash_files(args.repo)
    if not files:
        raise SystemExit(f"no .pt file in {args.repo}")
    target = fetch(f"https://huggingface.co/{args.repo}/resolve/main/{files[0]}", MODELS / Path(files[0]).name)
    print(f"\nStart the server with:\n  MODEL_PATH=models/{target.name} LITTER_CLASSES=* python run.py")


if __name__ == "__main__":
    main()
