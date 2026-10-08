"""Print QR stickers for the bins: A4 sheets (PNG, 300 dpi) of codes GL-BIN-001, GL-BIN-002, ...

    python tools/make_qr_stickers.py 12          # qr_stickers.png, qr_stickers_2.png, ...

Each sticker is about 9.3 cm wide (four per page). A 5.9 cm sticker only read reliably from about
20 cm away (docs/VERIFICATION.md); print at 100% scale, film it from about 30 cm and hold it still.
"""
import sys

import qrcode
from PIL import Image, ImageDraw

COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 12
PAGE = (2480, 3508)                    # A4 at 300 dpi
COLS, SIZE, MARGIN = 2, 1100, 90       # 1100 px at 300 dpi = 9.3 cm
ROWS = 2


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
    per_page = COLS * ROWS
    names = []
    for first in range(0, COUNT, per_page):
        page = Image.new("RGB", PAGE, "white")
        for i in range(first, min(first + per_page, COUNT)):
            row, col = divmod(i - first, COLS)
            x = MARGIN + col * (SIZE + MARGIN)
            y = MARGIN + row * (SIZE + 70 + MARGIN)
            page.paste(sticker(f"GL-BIN-{i + 1:03d}"), (x, y))
        name = "qr_stickers.png" if not names else f"qr_stickers_{len(names) + 1}.png"
        page.save(name, dpi=(300, 300))
        names.append(name)
    print(f"{COUNT} stickers on {len(names)} page(s): {', '.join(names)}")


if __name__ == "__main__":
    main()
