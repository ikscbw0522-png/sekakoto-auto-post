#!/usr/bin/env python3
"""output/*.mp4 を一括でWPアップロード＋hyperframes_reel_urls.jsonを更新。

既に登録済（再投稿防止）のテーマはスキップ。
"""
import base64
import hashlib
import json
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
ROOT = HERE.parent
ENV_PATH = ROOT / ".env"
OUTPUT_DIR = HERE / "output"
URL_JSON = HERE / "hyperframes_reel_urls.json"


def load_env():
    env = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def ascii_name(theme: str) -> str:
    h = hashlib.md5(theme.encode()).hexdigest()[:8]
    return f"hf_{int(time.time())}_{h}.mp4"


def upload(path: Path, fn: str, env: dict) -> str:
    url = f"{env['WP_URL']}/wp-json/wp/v2/media"
    auth_b64 = base64.b64encode(f"{env['WP_USER']}:{env['WP_APP_PASSWORD']}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Disposition": f'attachment; filename="{fn}"',
        "Content-Type": "video/mp4",
    }
    with open(path, "rb") as f:
        r = requests.post(url, headers=headers, data=f.read(), timeout=300)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    return r.json()["source_url"]


def main():
    env = load_env()
    urls = json.loads(URL_JSON.read_text(encoding="utf-8")) if URL_JSON.exists() else {}

    mp4s = sorted(OUTPUT_DIR.glob("*.mp4"))
    print(f"🎬 output/: {len(mp4s)}本")

    for mp4 in mp4s:
        theme = mp4.stem
        if theme in urls:
            print(f"  ⏭️  {theme} (登録済)")
            continue
        print(f"  ⬆️  {theme}... ", end="", flush=True)
        try:
            fn = ascii_name(theme)
            wp_url = upload(mp4, fn, env)
            urls[theme] = wp_url
            URL_JSON.write_text(json.dumps(urls, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"✅ {wp_url.rsplit('/', 1)[-1]}")
            time.sleep(1)
        except Exception as e:
            print(f"❌ {e}")

    print(f"\n🗂️  {URL_JSON.name}: {len(urls)}本")


if __name__ == "__main__":
    main()
