"""Download stock YOLOv8n (COCO: detects bottles, cups...) into backend/models/.

    python tools/download_model.py

For the public trash model, download its .pt file from Hugging Face by hand into models/, then
start the server with MODEL_PATH=models/<file>.pt LITTER_CLASSES=*
"""
import urllib.request
from pathlib import Path

URL = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt"
TARGET = Path(__file__).resolve().parent.parent / "models" / "yolov8n.pt"


def main():
    TARGET.parent.mkdir(exist_ok=True)
    if TARGET.exists():
        print("already there:", TARGET)
        return
    print("downloading", URL)
    urllib.request.urlretrieve(URL, TARGET)
    print("saved", TARGET, TARGET.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
