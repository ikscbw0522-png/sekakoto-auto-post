#!/usr/bin/env python3
"""Instagram カルーセル自動投稿スクリプト

使用例:
    python3 post_to_instagram.py --theme おはよう --caption caption_ohayou.txt
    python3 post_to_instagram.py --theme おはよう --caption caption_ohayou.txt --dry-run
"""
import argparse
import base64
import glob
import json
import os
import sys
import time
from pathlib import Path

import requests

URL_JSON = Path(__file__).parent / "image_urls.json"

ENV_PATH = Path(__file__).parent / ".env"


def load_env(path: Path) -> dict:
    required = ["IG_USER_ID", "IG_ACCESS_TOKEN", "WP_URL", "WP_USER", "WP_APP_PASSWORD"]
    env = {k: os.environ[k] for k in required if k in os.environ}
    if not all(k in env for k in required) and path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip())
    env.setdefault("WP_URL", "https://sekai-kotoba.com")
    missing = [k for k in required if not env.get(k)]
    if missing:
        sys.exit(f"Error: 環境変数または .env に次のキーが未設定です: {missing}")
    return env


def upload_to_wordpress(path: Path, env: dict, ascii_name: str) -> str:
    """WordPress メディアライブラリに画像をアップロードし公開URLを返す。"""
    url = f"{env['WP_URL']}/wp-json/wp/v2/media"
    auth_str = f"{env['WP_USER']}:{env['WP_APP_PASSWORD']}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Disposition": f'attachment; filename="{ascii_name}"',
        "Content-Type": "image/jpeg",
    }
    with open(path, "rb") as f:
        r = requests.post(url, headers=headers, data=f.read(), timeout=60)
    if r.status_code not in (200, 201):
        sys.exit(f"WPアップロード失敗 ({path.name}): {r.status_code} {r.text[:300]}")
    return r.json()["source_url"]


def create_ig_media_item(image_url: str, env: dict) -> str:
    """IG カルーセル子アイテムを作成し creation_id を返す。"""
    url = f"https://graph.instagram.com/v21.0/{env['IG_USER_ID']}/media"
    params = {
        "image_url": image_url,
        "is_carousel_item": "true",
        "access_token": env["IG_ACCESS_TOKEN"],
    }
    r = requests.post(url, params=params, timeout=30)
    if r.status_code != 200:
        sys.exit(f"IG子アイテム作成失敗: {r.status_code} {r.text[:300]}")
    return r.json()["id"]


def create_carousel_container(children_ids: list, caption: str, env: dict) -> str:
    """カルーセル親コンテナ作成。"""
    url = f"https://graph.instagram.com/v21.0/{env['IG_USER_ID']}/media"
    params = {
        "media_type": "CAROUSEL",
        "children": ",".join(children_ids),
        "caption": caption,
        "access_token": env["IG_ACCESS_TOKEN"],
    }
    r = requests.post(url, params=params, timeout=30)
    if r.status_code != 200:
        sys.exit(f"IGカルーセル作成失敗: {r.status_code} {r.text[:300]}")
    return r.json()["id"]


def publish_carousel(container_id: str, env: dict) -> str:
    """カルーセルを公開（実際に投稿）。"""
    url = f"https://graph.instagram.com/v21.0/{env['IG_USER_ID']}/media_publish"
    params = {
        "creation_id": container_id,
        "access_token": env["IG_ACCESS_TOKEN"],
    }
    r = requests.post(url, params=params, timeout=60)
    if r.status_code != 200:
        sys.exit(f"IG公開失敗: {r.status_code} {r.text[:300]}")
    return r.json()["id"]


def main():
    parser = argparse.ArgumentParser(description="Instagram カルーセル自動投稿")
    parser.add_argument("--theme", required=True, help="carousels_v3/ 内のテーマ名（例: おはよう）")
    parser.add_argument("--caption", help="キャプションtxtファイルのパス（省略時は captions/<theme>.txt）")
    parser.add_argument("--dry-run", action="store_true", help="投稿せずプレビューのみ")
    args = parser.parse_args()

    env = load_env(ENV_PATH)

    base = Path(__file__).parent
    image_dir = base / "carousels_v3" / args.theme
    if not image_dir.is_dir():
        sys.exit(f"画像フォルダなし: {image_dir}")

    image_paths = sorted(image_dir.glob("*.jpg"))
    if len(image_paths) != 10:
        sys.exit(f"画像枚数が10枚ではありません（{len(image_paths)}枚）: {image_dir}")

    if args.caption:
        caption_path = Path(args.caption)
        if not caption_path.is_absolute():
            caption_path = base / caption_path
    else:
        caption_path = base / "captions" / f"{args.theme}.txt"
    caption = caption_path.read_text(encoding="utf-8").strip()

    print(f"テーマ: {args.theme}")
    print(f"画像: {len(image_paths)}枚 ({image_dir})")
    print(f"キャプション: {caption_path} ({len(caption)}文字)")

    if args.dry_run:
        print("\n--- キャプション ---")
        print(caption)
        print("\n--- 画像一覧 ---")
        for p in image_paths:
            print(f"  {p.name}")
        print("\n[dry-run] 実投稿しませんでした。")
        return

    # image_urls.json に事前アップロード済みURLがあればそれを使う
    url_cache = {}
    if URL_JSON.exists():
        url_cache = json.loads(URL_JSON.read_text(encoding="utf-8"))

    if args.theme in url_cache and len(url_cache[args.theme]) == 10:
        print("\n[1/3] 事前アップロード済みURLを使用")
        public_urls = url_cache[args.theme]
        for i, u in enumerate(public_urls, 1):
            print(f"  {i}/10: {u}")
    else:
        print("\n[1/3] WordPressに画像をアップロード中...")
        public_urls = []
        ts = int(time.time())
        for i, p in enumerate(image_paths, 1):
            ascii_name = f"ig_{ts}_{i:02d}.jpg"
            url = upload_to_wordpress(p, env, ascii_name)
            public_urls.append(url)
            print(f"  {i}/10: {p.name} -> {url}")

    print("\n[2/3] Instagram子アイテム作成中...")
    children_ids = []
    for i, url in enumerate(public_urls, 1):
        cid = create_ig_media_item(url, env)
        children_ids.append(cid)
        print(f"  {i}/10: {cid}")
        time.sleep(1)

    print("\n[3/3] カルーセル公開中...")
    container_id = create_carousel_container(children_ids, caption, env)
    print(f"  親コンテナ: {container_id}")
    time.sleep(3)
    media_id = publish_carousel(container_id, env)
    print(f"  投稿ID: {media_id}")
    print("\n✅ 投稿完了！")


if __name__ == "__main__":
    main()
