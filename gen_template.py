"""
gen_template.py — Template story Instagram de Jonathan Hatchi
Template validé : fond noir, Caveat, texte blanc, rien d'autre.
"""
from PIL import Image, ImageDraw, ImageFont
import os, sys, time

FONT_FILE  = "/opt/story-template/fonts/caveat2.ttf"
FONT_SIZE  = 82
BG_COLOR   = "#000000"
TEXT_COLOR = "#FFFFFF"
PADDING    = 90
LINE_SPACING = 1.4
W, H       = 1080, 1920
OUT_DIR    = "/var/www/html/uploads"


def wrap_text(text, font, max_w, draw):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > max_w and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def create_story(text, out_path=None):
    img  = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_FILE, FONT_SIZE)

    max_w = W - PADDING * 2
    lines = []
    for para in text.split("\n"):
        if para.strip() == "":
            lines.append("")
        else:
            lines.extend(wrap_text(para, font, max_w, draw))

    line_h  = int(FONT_SIZE * LINE_SPACING)
    total_h = len(lines) * line_h
    y = (H - total_h) // 2

    for line in lines:
        if line == "":
            y += line_h
            continue
        draw.text((PADDING, y), line, font=font, fill=TEXT_COLOR)
        y += line_h

    if not out_path:
        out_path = os.path.join(OUT_DIR, f"story_{int(time.time())}.jpg")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "JPEG", quality=97)
    return out_path


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "Test du template."
    path = create_story(text)
    print(path)
