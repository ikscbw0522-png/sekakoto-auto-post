#!/usr/bin/env python3
"""全テーマの画像をWPに一括アップロードし、URL一覧をimage_urls.jsonに保存。

中断時はimage_urls.jsonを読み込んで続きから再開。
"""
import base64
import json
import sys
import time
from pathlib import Path

import requests

BASE = Path(__file__).parent
CAROUSELS_DIR = BASE / "carousels_v3"
URL_JSON = BASE / "image_urls.json"
ENV_PATH = BASE / ".env"


def load_env():
    env = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def upload(path: Path, ascii_name: str, env: dict) -> str:
    url = f"{env['WP_URL']}/wp-json/wp/v2/media"
    auth_b64 = base64.b64encode(f"{env['WP_USER']}:{env['WP_APP_PASSWORD']}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Disposition": f'attachment; filename="{ascii_name}"',
        "Content-Type": "image/jpeg",
    }
    with open(path, "rb") as f:
        r = requests.post(url, headers=headers, data=f.read(), timeout=120)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    return r.json()["source_url"]


def main():
    env = load_env()
    data = {}
    if URL_JSON.exists():
        data = json.loads(URL_JSON.read_text(encoding="utf-8"))
        print(f"既存データ読込: {len(data)} テーマ")

    themes = sorted([p.name for p in CAROUSELS_DIR.iterdir() if p.is_dir()])
    total = len(themes)
    ts = int(time.time())

    for idx, theme in enumerate(themes, 1):
        if theme in data and len(data[theme]) == 10:
            continue
        images = sorted((CAROUSELS_DIR / theme).glob("*.jpg"))
        if len(images) != 10:
            print(f"[{idx}/{total}] skip {theme} ({len(images)}枚)")
            continue
        urls = []
        try:
            for i, img in enumerate(images, 1):
                ascii_name = f"ig_{ts}_{idx:03d}_{i:02d}.jpg"
                url = upload(img, ascii_name, env)
                urls.append(url)
            data[theme] = urls
            URL_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{idx}/{total}] ✅ {theme}")
        except Exception as e:
            print(f"[{idx}/{total}] ❌ {theme}: {e}", file=sys.stderr)
            print(f"途中保存済み: {len(data)} テーマ")
            time.sleep(5)
            continue
        time.sleep(0.2)

    print(f"\n完了: {len(data)} / {total} テーマ")


if __name__ == "__main__":
    main()
