#!/usr/bin/env python3
"""
アイキャッチ画像生成＆WordPressアップロードスクリプト
- 記事タイトルからサムネイル画像を自動生成（1200x630）
- WordPress にアップロード
- 該当記事に featured_media として紐付ける
"""

import os
import glob
import json
import base64
import urllib.request
import urllib.error
from PIL import Image, ImageDraw, ImageFont

# ============ 設定 ============
WP_SITE = "https://sekai-kotoba.com"
WP_USER = "ik.scbw0522@gmail.com"
WP_APP_PASSWORD = "2ABi uqcs JfQj qYMn 9lmH zSRc"
ARTICLES_DIR = os.path.join(os.path.dirname(__file__), "記事サンプル")
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "thumbnails")

FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"

# 画像サイズ（OGP標準）
WIDTH, HEIGHT = 1200, 630

# 配色（記事ごとに循環させて変化をつける）
PALETTES = [
    {"bg": (45, 52, 97), "accent": (255, 193, 7), "text": (255, 255, 255)},   # 紺×黄
    {"bg": (44, 95, 45), "accent": (255, 235, 59), "text": (255, 255, 255)},  # 緑×黄
    {"bg": (120, 40, 60), "accent": (255, 205, 160), "text": (255, 255, 255)}, # えんじ
    {"bg": (33, 102, 172), "accent": (255, 230, 100), "text": (255, 255, 255)}, # 青
    {"bg": (176, 91, 45), "accent": (255, 240, 200), "text": (255, 255, 255)}, # オレンジ茶
    {"bg": (80, 40, 120), "accent": (240, 200, 255), "text": (255, 255, 255)}, # 紫
]

# 背景に書く10言語ラベル
LANGS_LABEL = "Korean  Chinese  Thai  Vietnamese  Indonesian  Tagalog  Malay  Hindi  Arabic  Turkish"


def extract_phrase_and_title(md_path: str):
    with open(md_path, encoding="utf-8") as f:
        md = f.read()
    title = md.split("\n", 1)[0].lstrip("# ").strip()
    base = os.path.basename(md_path).replace("_外国語.md", "")
    # 「〇〇」部分を抽出
    phrase = base
    return phrase, title


def make_thumbnail(phrase: str, out_path: str, palette: dict):
    img = Image.new("RGB", (WIDTH, HEIGHT), palette["bg"])
    draw = ImageDraw.Draw(img)

    # 薄く背景にアクセント色の帯
    draw.rectangle([(0, HEIGHT - 90), (WIDTH, HEIGHT)], fill=palette["accent"])

    # 左上・右下の装飾円
    draw.ellipse([(-80, -80), (180, 180)], fill=palette["accent"])
    draw.ellipse([(WIDTH - 180, HEIGHT - 260), (WIDTH + 80, HEIGHT - 100)],
                 fill=palette["accent"])

    # メインタイトル：「おはよう」
    font_phrase = ImageFont.truetype(FONT_PATH, 180)
    phrase_text = f"「{phrase}」"
    bbox = draw.textbbox((0, 0), phrase_text, font=font_phrase)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((WIDTH - w) / 2, 180), phrase_text, font=font_phrase, fill=palette["text"])

    # サブコピー
    font_sub = ImageFont.truetype(FONT_PATH, 58)
    sub_text = "は外国語で何て言う？"
    bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
    w, _ = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((WIDTH - w) / 2, 400), sub_text, font=font_sub, fill=palette["text"])

    # 下部帯の中に「10言語まとめ」
    font_bottom = ImageFont.truetype(FONT_PATH, 44)
    bottom_text = "10言語での言い方・発音まとめ"
    bbox = draw.textbbox((0, 0), bottom_text, font=font_bottom)
    w, _ = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((WIDTH - w) / 2, HEIGHT - 75), bottom_text, font=font_bottom, fill=palette["bg"])

    img.save(out_path, "JPEG", quality=90)


def wp_upload_image(image_path: str, auth_header: str) -> int:
    """画像をWordPressにアップロードして media ID を返す"""
    url = f"{WP_SITE}/wp-json/wp/v2/media"
    filename = os.path.basename(image_path)
    with open(image_path, "rb") as f:
        data = f.read()

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": auth_header,
            "Content-Type": "image/jpeg",
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())["id"]


def wp_get_post_id_by_slug(slug: str, auth_header: str) -> int:
    url = f"{WP_SITE}/wp-json/wp/v2/posts?slug={slug}"
    req = urllib.request.Request(url, headers={"Authorization": auth_header})
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read())
        if data:
            return data[0]["id"]
    return 0


def wp_set_featured_image(post_id: int, media_id: int, auth_header: str):
    url = f"{WP_SITE}/wp-json/wp/v2/posts/{post_id}"
    payload = {"featured_media": media_id}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as res:
        return res.status == 200


# post_to_wordpress.py と同じ SLUG_MAP を参照
SLUG_MAP = {
    "おはよう": "ohayou-foreign-languages",
    "こんにちは": "konnichiwa-foreign-languages",
    "こんばんは": "konbanwa-foreign-languages",
    "さようなら": "sayounara-foreign-languages",
    "おやすみ": "oyasumi-foreign-languages",
    "はじめまして": "hajimemashite-foreign-languages",
    "お元気ですか": "ogenki-desuka-foreign-languages",
    "久しぶり": "hisashiburi-foreign-languages",
    "いってきます": "ittekimasu-foreign-languages",
    "ただいま": "tadaima-foreign-languages",
    "おかえり": "okaeri-foreign-languages",
    "よろしくお願いします": "yoroshiku-foreign-languages",
}


def main():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    token = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
    auth_header = f"Basic {token}"

    files = sorted(glob.glob(os.path.join(ARTICLES_DIR, "*.md")))
    print(f"処理対象: {len(files)} 記事\n")

    for i, path in enumerate(files, 1):
        phrase, title = extract_phrase_and_title(path)
        if phrase not in SLUG_MAP:
            print(f"[{i}] SKIP (未登録): {phrase}")
            continue

        slug = SLUG_MAP[phrase]
        palette = PALETTES[i % len(PALETTES)]
        img_path = os.path.join(IMAGES_DIR, f"{slug}.jpg")

        # 1. 画像生成
        make_thumbnail(phrase, img_path, palette)

        # 2. 記事IDを取得
        post_id = wp_get_post_id_by_slug(slug, auth_header)
        if not post_id:
            print(f"[{i}] 記事が見つからない: {slug}")
            continue

        # 3. 画像をアップロード
        try:
            media_id = wp_upload_image(img_path, auth_header)
        except urllib.error.HTTPError as e:
            print(f"[{i}] アップロード失敗: {e.code} {e.read().decode()[:200]}")
            continue

        # 4. 記事に紐付け
        try:
            wp_set_featured_image(post_id, media_id, auth_header)
            print(f"[{i}] OK  {phrase} → media#{media_id} → post#{post_id}")
        except urllib.error.HTTPError as e:
            print(f"[{i}] 紐付け失敗: {e.code}")


if __name__ == "__main__":
    main()
