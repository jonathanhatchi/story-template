"""
launch_publisher.py — Orchestrateur de lancement "Agent IA Autonome"
Publie sur Instagram, Facebook, LinkedIn, TikTok (Buffer) depuis un email de lancement.
Usage : python3 launch_publisher.py
"""
import os, sys, time, json, base64, hashlib, sqlite3, subprocess, requests
sys.path.insert(0, "/opt/story-template")
sys.path.insert(0, "/opt/linkedin-oauth")
sys.path.insert(0, "/opt/video-publisher")

from gen_template import create_story
from PIL import Image, ImageDraw, ImageFont

# ── Config ────────────────────────────────────────────────────────────────────
IG_USER_ID  = "17841400014259083"
FB_TOKEN    = "EAAJm4LQ2DSoBQ5KfLiguS5HgZAonVzFHdcB04XtN5xm8OZA939m3ZASDl9ZAgmNZBjatI9dPQwUHHtIZAr8VrhGtZBj5zyWRVA8qkMG7dskC0Xsiu81lfH5oYVX1U4KpQFIOdhI6xOU1ZB2xSeJF446KJ1DYZBKJ2SjU4gRrqOq9OTI940rhp3As8YxHhErrPKxSQrA8KRKTkSWwDPDDFigZDZD"
PAGE_ID     = "505901699832393"
API         = "https://graph.facebook.com/v19.0"
UPLOADS_DIR = "/var/www/html/uploads"
BASE_URL    = "https://n8n.hatchi-media.com/uploads"
N8N_DB      = "/var/lib/docker/volumes/n8n_n8n_data/_data/database.sqlite"
N8N_KEY     = "jonathann8nkey2026"
BUFFER_KEY  = os.environ.get("BUFFER_KEY", "jPhFi5oki-VKH4O6y6JcWM5U2xBrfVGRhrZDWHqzQRL")
TIKTOK_CH   = "6a030818090476fb990f31fb"
BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ID = "7837490094"
CAMPAIGN    = "lancement-agent-ia"
BASE_SALES  = "https://formation.hatchi-media.com/agent-ia"

# ── UTM links ────────────────────────────────────────────────────────────────
def utm(source, medium, email_num):
    return f"{BASE_SALES}?utm_source={source}&utm_medium={medium}&utm_campaign={CAMPAIGN}&utm_content=email{email_num}"

# ── Instagram token ───────────────────────────────────────────────────────────
def get_ig_token():
    from Crypto.Cipher import AES
    def decrypt(b64):
        data = base64.b64decode(b64); salt = data[8:16]; ct = data[16:]
        pb = N8N_KEY.encode(); d = b""; d_i = b""
        while len(d) < 48:
            d_i = hashlib.md5(d_i + pb + salt).digest(); d += d_i
        c = AES.new(d[:32], AES.MODE_CBC, d[32:48])
        dec = c.decrypt(ct); return dec[:-dec[-1]].decode()
    conn = sqlite3.connect(N8N_DB)
    cols = [c[1] for c in conn.execute("PRAGMA table_info(credentials_entity)").fetchall()]
    row  = conn.execute("SELECT * FROM credentials_entity WHERE id='igTokenHatchi'").fetchone()
    conn.close()
    return json.loads(decrypt(dict(zip(cols, row))["data"]))["accessToken"]

# ── Telegram ──────────────────────────────────────────────────────────────────
def tg_send(text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                  data={"chat_id": TELEGRAM_ID, "text": text}, timeout=10)

def tg_photo(path, caption=""):
    with open(path, "rb") as f:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                      data={"chat_id": TELEGRAM_ID, "caption": caption},
                      files={"photo": f}, timeout=30)

def tg_video(path, caption=""):
    with open(path, "rb") as f:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo",
                      data={"chat_id": TELEGRAM_ID, "caption": caption},
                      files={"video": f}, timeout=60)

# ── Instagram Story ──────────────────────────────────────────────────────────
def post_ig_story(token, image_url, link=None):
    params = {"access_token": token, "media_type": "STORIES", "image_url": image_url}
    if link: params["link"] = link
    r = requests.post(f"{API}/{IG_USER_ID}/media", params=params, timeout=30)
    if r.status_code != 200: return False, r.text[:200]
    cid = r.json().get("id"); time.sleep(2)
    r2 = requests.post(f"{API}/{IG_USER_ID}/media_publish",
                       params={"access_token": token, "creation_id": cid}, timeout=30)
    return r2.status_code == 200, r2.json().get("id", r2.text[:100])

# ── Facebook Story ───────────────────────────────────────────────────────────
def post_fb_story(image_path):
    with open(image_path, "rb") as f:
        r = requests.post(f"{API}/{PAGE_ID}/photo_stories",
                          params={"access_token": FB_TOKEN},
                          files={"source": f}, timeout=60)
    if r.status_code == 200: return True, r.json()
    with open(image_path, "rb") as f:
        r2 = requests.post(f"{API}/{PAGE_ID}/photos",
                           params={"access_token": FB_TOKEN, "published": "true"},
                           files={"source": f}, timeout=60)
    return r2.status_code == 200, r2.json()

# ── LinkedIn image + texte ───────────────────────────────────────────────────
def create_linkedin_image(title_line1, title_line2, subtitle, out_path):
    W, H = 1200, 627
    FONT_TITLE = "/opt/story-template/fonts/caveat2.ttf"
    FONT_BODY  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    FONT_BOLD  = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    img  = Image.new("RGB", (W, H), "#050510")
    draw = ImageDraw.Draw(img)
    # Dégradé
    for i in range(H//2, 0, -8):
        a = int(25 * (1 - i/(H//2)))
        draw.ellipse([W-i, H-i, W, H], fill=f"#6D28D9{a:02x}")
    draw.rectangle([0, 0, W, 4], fill="#8B5CF6")
    # Badge
    bf = ImageFont.truetype(FONT_BOLD, 16)
    draw.rounded_rectangle([40, 24, 248, 48], radius=20, fill="#8B5CF6")
    draw.text((50, 28), "🤖 AGENT IA AUTONOME", font=bf, fill="#FFFFFF")
    # Titre
    tf = ImageFont.truetype(FONT_TITLE, 68)
    draw.text((40, H//2 - 90), title_line1, font=tf, fill="#FFFFFF")
    draw.text((40, H//2 - 90 + 80), title_line2, font=tf, fill="#FFFFFF")
    # Sous-titre
    sf = ImageFont.truetype(FONT_BODY, 20)
    draw.text((40, H - 80), subtitle, font=sf, fill="#94A3B8")
    # Orbe
    cx, cy, r = W - 120, H//2, 75
    for g in range(5, 0, -1):
        a = 8 * (6-g)
        draw.ellipse([cx-r-g*12, cy-r-g*12, cx+r+g*12, cy+r+g*12], fill=f"#8B5CF6{a:02x}")
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill="#7C3AED")
    draw.ellipse([cx-r//3, cy-r//2, cx, cy-r//4], fill="#FFFFFF22")
    img.save(out_path, "JPEG", quality=95)
    return out_path

def post_linkedin(text, image_path=None):
    from linkedin_poster import post_text_linkedin, _load_token, _auth_header, _member_urn
    import mimetypes
    if not image_path:
        return post_text_linkedin(text)
    # Upload image
    headers = {**_auth_header(), "Content-Type": "application/json", "X-Restli-Protocol-Version": "2.0.0"}
    reg = requests.post("https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=headers,
        json={"registerUploadRequest": {
            "owner": _member_urn(),
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "serviceRelationships": [{"identifier":"urn:li:userGeneratedContent","relationshipType":"OWNER"}]
        }}, timeout=30)
    if reg.status_code not in (200, 201):
        return post_text_linkedin(text)
    upload_url = reg.json()["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset = reg.json()["value"]["asset"]
    with open(image_path, "rb") as f:
        requests.put(upload_url, data=f, headers={"Authorization": _auth_header()["Authorization"]}, timeout=60)
    time.sleep(2)
    body = {
        "author": _member_urn(), "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "IMAGE",
            "media": [{"status": "READY", "media": asset}]
        }},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    r = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=body, timeout=30)
    return r.status_code in (200, 201), r.headers.get("x-restli-id", r.text[:100])

# ── TikTok via Buffer (vidéo générée depuis story image) ─────────────────────
def post_tiktok_buffer(video_url, caption):
    from datetime import datetime, timezone, timedelta
    due_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    r = requests.post("https://mcp.buffer.com/mcp",
        headers={"Authorization": f"Bearer {BUFFER_KEY}", "Content-Type": "application/json"},
        json={"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"create_post","arguments":{
            "channelId": TIKTOK_CH, "schedulingType": "automatic",
            "dueAt": due_at, "text": caption,
            "assets": [{"video": {"url": video_url}}]
        }}}, timeout=30)
    return "status" in r.text, r.text[:150]

def story_image_to_video(image_path, out_path, duration=5):
    """Convertit une image story en vidéo 5sec pour TikTok."""
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", image_path,
        "-c:v", "libx264", "-t", str(duration), "-pix_fmt", "yuv420p",
        "-vf", "scale=1080:1920", "-r", "30", out_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return out_path

# ── MAIN : publier un email de lancement ─────────────────────────────────────
def publish_launch_email(email_num, story_texts, linkedin_text,
                         linkedin_title1, linkedin_title2, linkedin_subtitle,
                         has_link=False):
    """
    email_num     : numéro de l'email (int) — détermine si on met des liens UTM
    story_texts   : liste de strings pour les stories IG/FB
    linkedin_text : texte adapté LinkedIn
    has_link      : True à partir de l'email 4 (ouverture du panier)
    """
    print(f"\n{'='*50}")
    print(f"PUBLICATION — Email {email_num}")
    print('='*50)

    link_ig  = utm("instagram", "story", email_num) if has_link else None
    link_fb  = utm("facebook", "story", email_num) if has_link else None
    link_li  = utm("linkedin", "post", email_num) if has_link else None
    link_tt  = utm("tiktok", "video", email_num) if has_link else None

    ig_token = get_ig_token()
    ts = int(time.time())

    results = {}

    # ── Instagram + Facebook Stories ─────────────────────────────────────────
    for i, text in enumerate(story_texts, 1):
        filename = f"launch_e{email_num}_s{i}_{ts}.jpg"
        img_path = os.path.join(UPLOADS_DIR, filename)
        create_story(text, out_path=img_path)
        img_url  = f"{BASE_URL}/{filename}"

        ok_ig, _ = post_ig_story(ig_token, img_url, link=link_ig)
        ok_fb, _ = post_fb_story(img_path)
        print(f"  Story {i} — IG: {'✅' if ok_ig else '❌'} · FB: {'✅' if ok_fb else '❌'}")
        results[f"story_{i}"] = {"ig": ok_ig, "fb": ok_fb}
        time.sleep(3)

    # ── LinkedIn ──────────────────────────────────────────────────────────────
    li_img_path = os.path.join(UPLOADS_DIR, f"launch_li_e{email_num}_{ts}.jpg")
    create_linkedin_image(linkedin_title1, linkedin_title2, linkedin_subtitle, li_img_path)
    li_text = linkedin_text
    if has_link:
        li_text += f"\n\n👉 {link_li}"
    ok_li, _ = post_linkedin(li_text, li_img_path)
    print(f"  LinkedIn: {'✅' if ok_li else '❌'}")
    results["linkedin"] = ok_li

    # ── TikTok via Buffer ─────────────────────────────────────────────────────
    # Utilise la 1ère story image convertie en vidéo
    first_img = os.path.join(UPLOADS_DIR, f"launch_e{email_num}_s1_{ts}.jpg")
    tt_video  = os.path.join(UPLOADS_DIR, f"launch_tt_e{email_num}_{ts}.mp4")
    story_image_to_video(first_img, tt_video)
    tt_caption = story_texts[0]
    if has_link: tt_caption += f"\n\n{link_tt}"
    ok_tt, _ = post_tiktok_buffer(f"{BASE_URL}/launch_tt_e{email_num}_{ts}.mp4", tt_caption)
    print(f"  TikTok: {'✅' if ok_tt else '❌'}")
    results["tiktok"] = ok_tt

    # ── Telegram recap ────────────────────────────────────────────────────────
    recap = f"✅ Email {email_num} publié !\n"
    recap += f"Instagram: {'✅' if results.get('story_1',{}).get('ig') else '❌'}\n"
    recap += f"Facebook: {'✅' if results.get('story_1',{}).get('fb') else '❌'}\n"
    recap += f"LinkedIn: {'✅' if results.get('linkedin') else '❌'}\n"
    recap += f"TikTok: {'✅' if results.get('tiktok') else '❌'}\n"
    if not has_link:
        recap += "\n(Pas de lien UTM — email de contenu)"
    tg_send(recap)

    return results


if __name__ == "__main__":
    # Exemple email 2 (pas de lien)
    publish_launch_email(
        email_num=2,
        story_texts=[
            "La plupart des gens utilisent l'IA comme un simple chatbot.\n\nIls passent à côté de l'essentiel.",
        ],
        linkedin_text="La plupart des gens utilisent encore ChatGPT comme un simple chatbot.\n\nAlors qu'on peut construire de vrais systèmes autonomes qui travaillent 24h/24.\n\nC'est exactement ce que j'ai fait ces derniers mois.",
        linkedin_title1="L'IA, c'est pas",
        linkedin_title2="juste ChatGPT.",
        linkedin_subtitle="Construis un vrai système autonome.",
        has_link=False,
    )
