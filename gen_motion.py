"""
gen_motion.py — Story animée : texte Caveat + planète en orbite
Génère un MP4 1080x1920 de 6 secondes, loop parfait.
"""
from PIL import Image, ImageDraw, ImageFont
import math, os, sys, time, subprocess, shutil

FONT_FILE    = "/opt/story-template/fonts/caveat2.ttf"
FONT_SIZE    = 82
W, H         = 1080, 1920
FPS          = 30
DURATION     = 6        # secondes
PADDING      = 90
LINE_SPACING = 1.4
FRAMES_DIR   = "/tmp/story_frames"


def wrap_text(text, font, max_w, draw):
    words = text.split()
    lines = []; current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > max_w and current:
            lines.append(current); current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def draw_planet(draw, cx, cy, radius, color, glow_color, trail_positions):
    """Dessine la planète avec glow + traînée."""
    # Traînée (trail) — points qui s'estompent
    for i, (tx, ty) in enumerate(trail_positions):
        alpha = int(80 * (i / len(trail_positions)))
        r_trail = max(2, int(radius * 0.4 * (i / len(trail_positions))))
        draw.ellipse([tx - r_trail, ty - r_trail, tx + r_trail, ty + r_trail],
                     fill=glow_color + f"{alpha:02x}")

    # Glow (halo autour de la planète)
    for g in range(6, 0, -1):
        gr = radius + g * 5
        alpha = int(15 * (7 - g))
        draw.ellipse([cx - gr, cy - gr, cx + gr, cy + gr],
                     fill=glow_color + f"{alpha:02x}")

    # Planète principale
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)

    # Reflet (petit point blanc en haut à gauche)
    rx, ry = cx - radius * 0.3, cy - radius * 0.3
    rr = max(2, radius // 4)
    draw.ellipse([rx - rr, ry - rr, rx + rr, ry + rr], fill="#FFFFFF88")


def generate_video(text, out_path, planet_color="#8B5CF6", glow_hex="#8B5CF6"):
    """
    planet_color : couleur principale de la planète
    glow_hex     : couleur du halo (sans alpha, ex: '#8B5CF6')
    """
    os.makedirs(FRAMES_DIR, exist_ok=True)
    font = ImageFont.truetype(FONT_FILE, FONT_SIZE)

    # Pré-calcul du bloc texte
    dummy_img  = Image.new("RGB", (W, H))
    dummy_draw = ImageDraw.Draw(dummy_img)
    max_w = W - PADDING * 2
    lines = []
    for para in text.split("\n"):
        if para.strip() == "":
            lines.append("")
        else:
            lines.extend(wrap_text(para, font, max_w, dummy_draw))

    line_h  = int(FONT_SIZE * LINE_SPACING)
    total_h = len(lines) * line_h
    text_top    = (H - total_h) // 2
    text_bottom = text_top + total_h
    text_cx     = W // 2
    text_cy     = (text_top + text_bottom) // 2

    # Orbite elliptique autour du bloc texte
    orbit_rx = (max_w // 2) + 120   # demi-axe horizontal
    orbit_ry = (total_h // 2) + 140  # demi-axe vertical
    planet_r  = 22
    trail_len = 12

    total_frames = FPS * DURATION
    trail_positions = []

    print(f"Génération de {total_frames} frames...")
    for frame_i in range(total_frames):
        img  = Image.new("RGBA", (W, H), "#000000FF")
        draw = ImageDraw.Draw(img)

        # Angle (sens horaire, boucle parfaite)
        angle = (2 * math.pi * frame_i / total_frames) - math.pi / 2
        px = int(text_cx + orbit_rx * math.cos(angle))
        py = int(text_cy + orbit_ry * math.sin(angle))

        # Traînée
        trail_positions.append((px, py))
        if len(trail_positions) > trail_len:
            trail_positions.pop(0)

        # — Planète DERRIÈRE le texte si py < text_cy (haut de l'orbite)
        # On dessine d'abord la planète si elle est "derrière"
        behind = py < text_cy
        if behind:
            draw_planet(draw, px, py, planet_r, planet_color, glow_hex, list(trail_positions[:-1]))

        # Texte
        y = text_top
        for line in lines:
            if line == "":
                y += line_h; continue
            draw.text((PADDING, y), line, font=font, fill="#FFFFFFFF")
            y += line_h

        # Planète DEVANT si elle est "devant"
        if not behind:
            draw_planet(draw, px, py, planet_r, planet_color, glow_hex, list(trail_positions[:-1]))

        # Convertir en RGB et sauvegarder
        frame = img.convert("RGB")
        frame.save(f"{FRAMES_DIR}/frame_{frame_i:04d}.jpg", "JPEG", quality=92)

        if frame_i % 30 == 0:
            print(f"  Frame {frame_i}/{total_frames}")

    # Compiler avec ffmpeg
    print("Compilation MP4...")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", f"{FRAMES_DIR}/frame_%04d.jpg",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "20",
        "-movflags", "+faststart",
        out_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    shutil.rmtree(FRAMES_DIR, ignore_errors=True)
    print(f"Vidéo générée : {out_path}")
    return out_path


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else \
        "Les gens pensent qu'on fait une fausse scarcity autour de l'IA,\non se rejoint dans un ou deux ans."
    out = f"/var/www/html/uploads/story_motion_{int(time.time())}.mp4"
    generate_video(text, out)
    print(out)
