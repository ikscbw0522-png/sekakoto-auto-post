#!/usr/bin/env python3
"""Instagram Reel 自動投稿スクリプト

使用例:
    python3 post_reel.py --theme ごめんなさい
    python3 post_reel.py --theme ごめんなさい --dry-run
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = Path(__file__).parent
REEL_URLS = BASE / "reel_urls.json"
CAPTIONS_DIR = BASE / "captions"
ENV_PATH = BASE / ".env"


def load_env():
    required = ["IG_USER_ID", "IG_ACCESS_TOKEN"]
    env = {k: os.environ[k] for k in required if k in os.environ}
    if not all(k in env for k in required) and ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
    missing = [k for k in required if not env.get(k)]
    if missing:
        sys.exit(f"環境変数未設定: {missing}")
    return env


def create_reel_container(video_url: str, caption: str, env: dict) -> str:
    url = f"https://graph.instagram.com/v21.0/{env['IG_USER_ID']}/media"
    params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": env["IG_ACCESS_TOKEN"],
    }
    r = requests.post(url, params=params, timeout=60)
    if r.status_code != 200:
        sys.exit(f"Reelコンテナ作成失敗: {r.status_code} {r.text[:300]}")
    return r.json()["id"]


def wait_for_processing(container_id: str, env: dict, timeout: int = 300) -> bool:
    """動画のアップロード・エンコード完了を待つ。"""
    url = f"https://graph.instagram.com/v21.0/{container_id}"
    params = {"fields": "status_code", "access_token": env["IG_ACCESS_TOKEN"]}
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            status = r.json().get("status_code", "")
            print(f"  status: {status}")
            if status == "FINISHED":
                return True
            if status == "ERROR":
                print(f"  詳細: {r.text}")
                return False
        time.sleep(5)
    return False


def publish_reel(container_id: str, env: dict) -> str:
    url = f"https://graph.instagram.com/v21.0/{env['IG_USER_ID']}/media_publish"
    params = {"creation_id": container_id, "access_token": env["IG_ACCESS_TOKEN"]}
    r = requests.post(url, params=params, timeout=60)
    if r.status_code != 200:
        sys.exit(f"Reel公開失敗: {r.status_code} {r.text[:300]}")
    return r.json()["id"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", required=True)
    parser.add_argument("--caption", help="キャプションtxt（省略時は captions/<theme>.txt）")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env = load_env()

    if not REEL_URLS.exists():
        sys.exit("reel_urls.json がありません。bulk_upload_reels.py を先に実行してください。")
    urls = json.loads(REEL_URLS.read_text(encoding="utf-8"))
    if args.theme not in urls:
        sys.exit(f"reel_urls.json に {args.theme} のURLなし")
    video_url = urls[args.theme]

    caption_path = Path(args.caption) if args.caption else (CAPTIONS_DIR / f"{args.theme}.txt")
    caption = caption_path.read_text(encoding="utf-8").strip()

    print(f"テーマ: {args.theme}")
    print(f"動画URL: {video_url}")
    print(f"キャプション: {len(caption)}文字")

    if args.dry_run:
        print(caption)
        print("\n[dry-run] 実投稿なし")
        return

    print("\n[1/3] Reelコンテナ作成中...")
    container_id = create_reel_container(video_url, caption, env)
    print(f"  container: {container_id}")

    print("\n[2/3] エンコード待機中...")
    if not wait_for_processing(container_id, env):
        sys.exit("エンコード失敗またはタイムアウト")

    print("\n[3/3] 公開中...")
    media_id = publish_reel(container_id, env)
    print(f"  投稿ID: {media_id}")
    print("\n✅ Reel投稿完了！")


if __name__ == "__main__":
    main()
