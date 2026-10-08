"""Fine-tune the litter model on our own Slemani photos (day one evening, on Colab or Kaggle GPU).

1. Annotate the 300-500 photos in any tool that exports YOLO format (Label Studio, CVAT, Roboflow):
   a folder of images, a folder of .txt labels with the same names, and classes.txt.
2. Split them. The --test photos are never trained on; they are the 50 for tools/evaluate.py:
       python tools/train.py split --images export/images --labels export/labels \
           --classes export/classes.txt --out datasets/slemani --test 50
3. Train (on the GPU machine; `pip install ultralytics` first):
       python tools/train.py train --data datasets/slemani/data.yaml --base models/yolov8m-seg.pt
   The best weights are copied to models/slemani.pt and scored on the held-out test photos.
4. Compare with the general model before switching (keep the general one if it is not better):
       python tools/evaluate.py datasets/slemani/test --model models/yolov8m-seg.pt --model models/slemani.pt

The base model must match the labels: polygon labels -> a segmentation model (*-seg.pt, like the
Hugging Face trash model); box labels -> a detection model (yolov8n.pt / yolov8s.pt).
"""
import argparse
import csv
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def label_kind(label_dir):
    """'polygons' when any label line has more than the 5 numbers of a box, else 'boxes'."""
    for txt in Path(label_dir).rglob("*.txt"):
        for line in txt.read_text().splitlines():
            if len(line.split()) > 5:
                return "polygons"
    return "boxes"


def split(args):
    images = sorted(p for p in Path(args.images).iterdir() if p.suffix.lower() in IMAGE_TYPES)
    labels = Path(args.labels)
    if not images:
        raise SystemExit(f"no images in {args.images}")
    names = [n.strip() for n in Path(args.classes).read_text(encoding="utf-8").splitlines() if n.strip()]
    rng = random.Random(args.seed)
    rng.shuffle(images)
    test, rest = images[:args.test], images[args.test:]
    n_val = max(1, round(len(rest) * args.val))
    parts = {"test": test, "val": rest[:n_val], "train": rest[n_val:]}

    out = Path(args.out)
    for part, files in parts.items():
        (out / part / "images").mkdir(parents=True, exist_ok=True)
        (out / part / "labels").mkdir(parents=True, exist_ok=True)
        for img in files:
            shutil.copy2(img, out / part / "images" / img.name)
            txt = labels / f"{img.stem}.txt"          # no label file = a photo with no litter
            target = out / part / "labels" / f"{img.stem}.txt"
            target.write_text(txt.read_text() if txt.exists() else "")

    # labels.csv for tools/evaluate.py: the annotated count is known; the 1-5 level is a human
    # judgement, so fill that column in by hand (leave it empty to skip the level score).
    with open(out / "test" / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "count", "level"])
        for img in test:
            lines = (out / "test" / "labels" / f"{img.stem}.txt").read_text().splitlines()
            w.writerow([f"images/{img.name}", sum(1 for line in lines if line.strip()), ""])

    yaml = [f"path: {out.resolve()}", "train: train/images", "val: val/images", "test: test/images",
            "names:"] + [f"  {i}: {name}" for i, name in enumerate(names)]
    (out / "data.yaml").write_text("\n".join(yaml) + "\n", encoding="utf-8")
    print(f"train {len(parts['train'])}, val {len(parts['val'])}, test {len(parts['test'])} "
          f"({label_kind(labels)}) -> {out / 'data.yaml'}")
    print(f"Fill in the level column of {out / 'test' / 'labels.csv'} for the level score.")


def train(args):
    try:
        from ultralytics import YOLO
    except ImportError:
        raise SystemExit("pip install ultralytics (on the GPU machine)")
    data = Path(args.data)
    kind = label_kind(data.parent / "train" / "labels")
    is_seg = "-seg" in Path(args.base).name
    if (kind == "polygons") != is_seg:
        raise SystemExit(f"the labels are {kind} but {args.base} is a "
                         f"{'segmentation' if is_seg else 'detection'} model; see the top of this file")

    model = YOLO(args.base)
    model.train(data=str(data), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
                patience=args.patience, project=str(ROOT / "runs"), name=args.name, exist_ok=True, seed=0)
    best = Path(model.trainer.best)
    MODELS.mkdir(exist_ok=True)
    target = MODELS / f"{args.name}.pt"
    shutil.copy2(best, target)
    print("saved", target)

    has_test = any((data.parent / "test" / "images").glob("*"))
    metrics = YOLO(str(target)).val(data=str(data), split="test" if has_test else "val")
    print(f"mAP50 {metrics.box.map50:.3f}  mAP50-95 {metrics.box.map:.3f}  "
          f"({'held-out test photos' if has_test else 'validation photos'})")
    print(f"Use it: MODEL_PATH=models/{target.name} LITTER_CLASSES=* python run.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split", help="split a YOLO export into train / val / held-out test")
    s.add_argument("--images", required=True)
    s.add_argument("--labels", required=True)
    s.add_argument("--classes", required=True, help="classes.txt, one class name per line")
    s.add_argument("--out", default="datasets/slemani")
    s.add_argument("--test", type=int, default=50, help="photos kept out of training")
    s.add_argument("--val", type=float, default=0.15, help="share of the rest used for validation")
    s.add_argument("--seed", type=int, default=7)
    t = sub.add_parser("train", help="fine-tune with ultralytics")
    t.add_argument("--data", required=True)
    t.add_argument("--base", default=str(MODELS / "yolov8m-seg.pt"))
    t.add_argument("--epochs", type=int, default=60)
    t.add_argument("--imgsz", type=int, default=640)
    t.add_argument("--batch", type=int, default=16)
    t.add_argument("--patience", type=int, default=15)
    t.add_argument("--name", default="slemani")
    args = parser.parse_args()
    split(args) if args.cmd == "split" else train(args)


if __name__ == "__main__":
    sys.exit(main())
