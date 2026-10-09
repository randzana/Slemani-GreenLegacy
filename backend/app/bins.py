"""Trash bin management and QR code generation for waste disposal verification."""
import base64
import io
from functools import lru_cache

import qrcode
from PIL import Image, ImageDraw, ImageFont

BIN_COLUMNS = """b.id, b.code, b.name, b.bin_type, b.capacity_liters, b.status,
                 ST_Y(b.location::geometry) AS lat, ST_X(b.location::geometry) AS lon,
                 b.neighbourhood_id, n.name AS neighbourhood_name, b.qr_code_data,
                 b.created_at,
                 (SELECT COUNT(*) FROM bin_disposals d WHERE d.bin_id = b.id)::int AS disposal_count"""

BIN_TYPES_KU = {
    "general": "پاشماوەی گشتی",
    "recycle": "ڕیسایکڵین (پلاستیک و نایلۆن)",
    "organic": "ئەندامی و پاشماوەی خۆراک",
    "glass_metal": "شووشە و کانزا",
}


@lru_cache(maxsize=2048)
def generate_qr_data_url(code: str) -> str:
    """Generate high-resolution Base64 PNG data URL of the QR code for web and mobile display."""
    q = qrcode.QRCode(
        box_size=10,
        border=3,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
    )
    q.add_data(code)
    q.make(fit=True)
    img = q.make_image(fill_color="#0F2A1F", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def generate_sticker_png(code: str, name: str = "", neighbourhood: str = "", bin_type: str = "general") -> bytes:
    """Generate a printable official municipal sticker PNG (A5 / postcard size, 300 DPI style)."""
    width, height = 700, 880
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    # Outer border (Forest Green)
    draw.rectangle([12, 12, width - 13, height - 13], outline="#1E7A4A", width=8)
    draw.rectangle([20, 20, width - 21, height - 21], outline="#0F2A1F", width=2)

    # Header banner
    draw.rectangle([24, 24, width - 24, 110], fill="#0F2A1F")

    # Draw QR code
    q = qrcode.QRCode(
        box_size=12,
        border=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
    )
    q.add_data(code)
    q.make(fit=True)
    qr_img = q.make_image(fill_color="#0F2A1F", back_color="#FFFFFF").convert("RGB").resize((480, 480))
    canvas.paste(qr_img, ((width - 480) // 2, 130))

    # Code badge container
    draw.rectangle([50, 630, width - 50, 715], fill="#ECE7DA", outline="#D0C8B6", width=2)

    # Instructions box at footer
    draw.rectangle([24, 735, width - 24, height - 24], fill="#F5F2EA")

    # Texts using standard fonts or try system truetype
    try:
        font_header = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_code = ImageFont.truetype("/System/Library/Fonts/Courier.dfont", 36)
        font_text = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except Exception:
        font_header = font_sub = font_code = font_text = ImageFont.load_default()

    # Draw Header Text
    draw.text((width // 2, 50), "GreenLegacy Slemani", fill="#F2EFE6", font=font_header, anchor="mm")
    draw.text((width // 2, 85), "Municipal Smart Waste Verification", fill="#BFD3C6", font=font_sub, anchor="mm")

    # Draw Code & Type
    type_str = BIN_TYPES_KU.get(bin_type, bin_type)
    draw.text((width // 2, 660), f"{code}", fill="#0F2A1F", font=font_code, anchor="mm")
    hood_label = f" ({neighbourhood})" if neighbourhood else ""
    draw.text((width // 2, 695), f"{name}{hood_label} · {type_str}", fill="#4A5A51", font=font_sub, anchor="mm")

    # Draw Instructions
    draw.text((width // 2, 775), "Scan this QR code with GreenLegacy App", fill="#13261D", font=font_text, anchor="mm")
    draw.text((width // 2, 810), "سکان بکە لەکاتی فڕێدانی پاشماوە بۆ وەرگرتنی خاڵی سەوز", fill="#1E7A4A", font=font_text, anchor="mm")

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


def bin_json(row: dict) -> dict:
    """Format database row for JSON response."""
    data = dict(row)
    if "lat" in data and data["lat"] is not None:
        data["lat"] = round(float(data["lat"]), 5)
    if "lon" in data and data["lon"] is not None:
        data["lon"] = round(float(data["lon"]), 5)
    if "created_at" in data and data["created_at"] is not None:
        data["created_at"] = data["created_at"].isoformat()
    if "code" in data:
        data["qr_data_url"] = generate_qr_data_url(data["code"])
        data["qr_code_data"] = data["qr_data_url"]
    data["type_label"] = BIN_TYPES_KU.get(data.get("bin_type", "general"), data.get("bin_type", ""))
    return data
