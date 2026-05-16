"""
post_stories.py — Publie une liste de stories sur Instagram + Facebook
Utilise le template validé : fond noir, Caveat, texte blanc.
Usage : python3 post_stories.py
"""
import os, sys, time, json, base64, hashlib, sqlite3, requests
sys.path.insert(0, "/opt/story-template")
from gen_template import create_story

IG_USER_ID  = "17841400014259083"
FB_TOKEN    = "EAAJm4LQ2DSoBQ5KfLiguS5HgZAonVzFHdcB04XtN5xm8OZA939m3ZASDl9ZAgmNZBjatI9dPQwUHHtIZAr8VrhGtZBj5zyWRVA8qkMG7dskC0Xsiu81lfH5oYVX1U4KpQFIOdhI6xOU1ZB2xSeJF446KJ1DYZBKJ2SjU4gRrqOq9OTI940rhp3As8YxHhErrPKxSQrA8KRKTkSWwDPDDFigZDZD"
PAGE_ID     = "505901699832393"
API         = "https://graph.facebook.com/v19.0"
UPLOADS_DIR = "/var/www/html/uploads"
BASE_URL    = "https://n8n.hatchi-media.com/uploads"
N8N_DB      = "/var/lib/docker/volumes/n8n_n8n_data/_data/database.sqlite"
N8N_KEY     = "jonathann8nkey2026"


def get_ig_token():
    from Crypto.Cipher import AES
    def decrypt(b64_data):
        data = base64.b64decode(b64_data)
        salt = data[8:16]; ct = data[16:]
        pb = N8N_KEY.encode(); d = b""; d_i = b""
        while len(d) < 48:
            d_i = hashlib.md5(d_i + pb + salt).digest(); d += d_i
        cipher = AES.new(d[:32], AES.MODE_CBC, d[32:48])
        dec = cipher.decrypt(ct)
        return dec[:-dec[-1]].decode()
    conn = sqlite3.connect(N8N_DB)
    cols = [c[1] for c in conn.execute("PRAGMA table_info(credentials_entity)").fetchall()]
    row  = conn.execute("SELECT * FROM credentials_entity WHERE id='igTokenHatchi'").fetchone()
    conn.close()
    return json.loads(decrypt(dict(zip(cols, row))["data"]))["accessToken"]


def post_ig_story(token, image_url, link=None):
    params = {
        "access_token": token,
        "media_type": "STORIES",
        "image_url": image_url,
    }
    if link:
        params["link"] = link
    r = requests.post(f"{API}/{IG_USER_ID}/media", params=params, timeout=30)
    if r.status_code != 200:
        return False, r.text[:200]
    creation_id = r.json().get("id")
    time.sleep(2)
    r2 = requests.post(f"{API}/{IG_USER_ID}/media_publish", params={
        "access_token": token, "creation_id": creation_id,
    }, timeout=30)
    if r2.status_code != 200:
        return False, r2.text[:200]
    return True, r2.json().get("id")


def post_fb_story(image_path):
    with open(image_path, "rb") as f:
        r = requests.post(f"{API}/{PAGE_ID}/photo_stories", params={
            "access_token": FB_TOKEN,
        }, files={"source": f}, timeout=60)
    if r.status_code == 200:
        return True, r.json()
    # Fallback : post photo normale
    with open(image_path, "rb") as f:
        r2 = requests.post(f"{API}/{PAGE_ID}/photos", params={
            "access_token": FB_TOKEN, "published": "true",
        }, files={"source": f}, timeout=60)
    return r2.status_code == 200, r2.json()


def publish_stories(stories, instagram=True, facebook=True):
    """
    stories : liste de strings OU liste de dicts {"text": "...", "link": "https://..."}
              Le lien est optionnel — s'il est absent, story sans lien cliquable.
    """
    token = get_ig_token()
    ig_ok = fb_ok = 0

    for i, item in enumerate(stories, 1):
        # Accepte string simple ou dict {"text": ..., "link": ...}
        if isinstance(item, str):
            text = item
            link = None
        else:
            text = item["text"]
            link = item.get("link")

        print(f"\n--- Story {i}/{len(stories)} ---")
        if link:
            print(f"  Lien: {link}")

        # Générer l'image
        filename = f"story_{int(time.time())}_{i}.jpg"
        img_path = os.path.join(UPLOADS_DIR, filename)
        create_story(text, out_path=img_path)
        img_url  = f"{BASE_URL}/{filename}"
        print(f"  Image: {filename}")

        if instagram:
            ok, res = post_ig_story(token, img_url, link=link)
            print(f"  IG: {'OK' if ok else 'ECHEC — ' + str(res)}")
            if ok: ig_ok += 1

        if facebook:
            ok, res = post_fb_story(img_path)
            print(f"  FB: {'OK' if ok else 'ECHEC'}")
            if ok: fb_ok += 1

        time.sleep(3)

    print(f"\nRésultat — IG: {ig_ok}/{len(stories)} · FB: {fb_ok}/{len(stories)}")
    return ig_ok, fb_ok


if __name__ == "__main__":
    # Exemple d'utilisation
    stories = [
        "Les gens pensent qu'on fait une fausse scarcity autour de l'IA,\non se rejoint dans un ou deux ans.",
    ]
    publish_stories(stories)
