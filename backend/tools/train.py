"""Fine-tune the litter model on our own Slemani photos (day one evening, on Colab or Kaggle GPU).

1. Annotate the 300-500 photos in any tool that exports YOLO format (Label Studio, CVAT, Roboflow):
   a folder of images, a folder of .txt labels with the same names, and classes.txt.
2. Split them. The --test photos are never trained on; they are the 50 for tools/evaluate.py:
       python tools/train.py split --images export/images --labels export/labels \
           --classes export/classes.txt --out datasets/slemani --test 50
3. Train (on the GPU machine; `pip install ultralytics` first):
       python tools/train.py train --data datasets/slemani/data.yaml --base models/yolov8m-seg.pt
   The best weights are copied to models/slemani.pt and scored on the held-out test photos.
   backend/notebooks/finetune_colab.ipynb runs steps 2-4 on a free Colab GPU.
4. Compare with the general model before switching (keep the general one if it is not better):
       python tools/evaluate.py datasets/slemani/test --model models/yolov8m-seg.pt --model models/slemani.pt

The base model must fit the labels: box labels need a detection model (python tools/download_model.py
--stock yolov8s.pt, then --base models/yolov8s.pt). Polygon labels suit the Hugging Face trash model
(a segmentation model); with a detection model they are trained as boxes.
"""
import argparse
import csv
import json
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


def is_clean(labels, img):
    """No label file, or an empty one: a photo with no litter."""
    txt = Path(labels) / f"{img.stem}.txt"
    return not txt.exists() or not txt.read_text().strip()


def split(args):
    images = sorted(p for p in Path(args.images).iterdir() if p.suffix.lower() in IMAGE_TYPES)
    labels = Path(args.labels)
    if not images:
        raise SystemExit(f"no images in {args.images}")
    names = [n.strip() for n in Path(args.classes).read_text(encoding="utf-8").splitlines() if n.strip()]
    rng = random.Random(args.seed)
    rng.shuffle(images)
    # The held-out photos get their share of clean ones: they show whether the model invents
    # litter (free points), and a plain shuffle can leave none of them in the test set.
    clean = {p for p in images if is_clean(labels, p)}
    n_clean = min(len(clean), args.test, max(1 if clean else 0, round(args.test * len(clean) / len(images))))
    test = ([p for p in images if p in clean][:n_clean]
            + [p for p in images if p not in clean][:args.test - n_clean])
    held = set(test)
    rest = [p for p in images if p not in held]
    if len(rest) < 2:
        raise SystemExit(f"only {len(rest)} photos left for training after --test {args.test}")
    n_val = max(1, round(len(rest) * args.val))
    parts = {"test": test, "val": rest[:n_val], "train": rest[n_val:]}

    out = Path(args.out)
    if any((out / part).exists() for part in parts):     # old files would leak test photos into training
        raise SystemExit(f"{out} already holds a split: delete it or choose another --out")
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

    quote = lambda text: json.dumps(str(text), ensure_ascii=False)   # noqa: E731  (a JSON string is valid YAML)
    yaml = [f"path: {quote(out.resolve())}", "train: train/images", "val: val/images", "test: test/images",
            "names:"] + [f"  {i}: {quote(name)}" for i, name in enumerate(names)]
    (out / "data.yaml").write_text("\n".join(yaml) + "\n", encoding="utf-8")
    print(f"train {len(parts['train'])}, val {len(parts['val'])}, test {len(parts['test'])} "
          f"({n_clean} clean) ({label_kind(labels)}) -> {out / 'data.yaml'}")
    print(f"Fill in the level column of {out / 'test' / 'labels.csv'} for the level score.")


def check_base(kind, task, base):
    """Stop before training when the labels cannot train this base model. Uses the model's own
    task, not its file name: a Hugging Face segmentation model can be called best.pt."""
    if task not in ("detect", "segment"):
        raise SystemExit(f"{base} is a {task} model; use a detection or segmentation model")
    if kind == "boxes" and task == "segment":
        raise SystemExit(f"the labels are boxes but {base} is a segmentation model; use a detection base: "
                         "python tools/download_model.py --stock yolov8s.pt, then --base models/yolov8s.pt")
    if kind == "polygons" and task == "detect":
        print(f"note: {base} is a detection model, so the polygons are trained as boxes")


def train(args):
    try:
        from ultralytics import YOLO
    except ImportError:
        raise SystemExit("pip install ultralytics (on the GPU machine)")
    data = Path(args.data)
    base = Path(args.base)
    if base.suffix == ".pt" and not base.is_file():   # else ultralytics quietly fetches a stock model of that name
        raise SystemExit(f"no {base}: python tools/download_model.py --trash (or --stock yolov8s.pt)")
    model = YOLO(str(base))
    check_base(label_kind(data.parent / "train" / "labels"), model.task, base)
    model.train(data=str(data), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
                patience=args.patience, project=str(ROOT / "runs"), name=args.name, exist_ok=True, seed=0)
    best = Path(model.trainer.best)
    MODELS.mkdir(exist_ok=True)
    target = MODELS / f"{args.name}.pt"
    shutil.copy2(best, target)
    print("saved", target)

    has_test = any((data.parent / "test" / "images").glob("*"))
    metrics = YOLO(str(target)).val(data=str(data), split="test" if has_test else "val",
                                    project=str(ROOT / "runs"), name=f"{args.name}_test", exist_ok=True)
    masks = f"  masks mAP50 {metrics.seg.map50:.3f}" if hasattr(metrics, "seg") else ""
    print(f"mAP50 {metrics.box.map50:.3f}  mAP50-95 {metrics.box.map:.3f}{masks}  "
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
