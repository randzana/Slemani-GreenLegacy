"""Print QR stickers for the bins: an A4 sheet (PNG) of codes GL-BIN-001, GL-BIN-002, ...

    python tools/make_qr_stickers.py 12          # writes qr_stickers.png
"""
import sys

import qrcode
from PIL import Image, ImageDraw

COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 12
PAGE = (2480, 3508)                    # A4 at 300 dpi
COLS, SIZE, MARGIN = 3, 700, 90


def sticker(code):
    q = qrcode.QRCode(border=4, box_size=20, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(code)
    q.make(fit=True)
    img = q.make_image(fill_color="black", back_color="white").convert("RGB").resize((SIZE, SIZE))
    canvas = Image.new("RGB", (SIZE, SIZE + 70), "white")
    canvas.paste(img, (0, 0))
    ImageDraw.Draw(canvas).text((SIZE // 2 - 70, SIZE + 15), code, fill="black")
    return canvas


def main():
    page = Image.new("RGB", PAGE, "white")
    for i in range(COUNT):
        row, col = divmod(i, COLS)
        x = MARGIN + col * (SIZE + MARGIN)
        y = MARGIN + row * (SIZE + 70 + MARGIN)
        if y + SIZE > PAGE[1]:
            break
        page.paste(sticker(f"GL-BIN-{i + 1:03d}"), (x, y))
    page.save("qr_stickers.png", dpi=(300, 300))
    print("qr_stickers.png written")


if __name__ == "__main__":
    main()
