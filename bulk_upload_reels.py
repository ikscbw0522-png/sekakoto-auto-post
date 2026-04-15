#!/usr/bin/env python3
"""全リールMP4をWPに一括アップロードし、URL一覧をreel_urls.jsonに保存。"""
import base64
import json
import sys
import time
from pathlib import Path

import requests

BASE = Path(__file__).parent
REELS_DIR = BASE / "reels"
URL_JSON = BASE / "reel_urls.json"
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
        "Content-Type": "video/mp4",
    }
    with open(path, "rb") as f:
        r = requests.post(url, headers=headers, data=f.read(), timeout=180)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    return r.json()["source_url"]


def main():
    env = load_env()
    data = {}
    if URL_JSON.exists():
        data = json.loads(URL_JSON.read_text(encoding="utf-8"))
        print(f"既存: {len(data)} テーマ")

    mp4s = sorted(REELS_DIR.glob("*.mp4"))
    total = len(mp4s)
    ts = int(time.time())

    for idx, path in enumerate(mp4s, 1):
        theme = path.stem
        if theme in data:
            continue
        try:
            ascii_name = f"reel_{ts}_{idx:03d}.mp4"
            url = upload(path, ascii_name, env)
            data[theme] = url
            URL_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{idx}/{total}] ✅ {theme}")
        except Exception as e:
            print(f"[{idx}/{total}] ❌ {theme}: {e}", file=sys.stderr)
            time.sleep(3)
        time.sleep(0.3)

    print(f"\n完了: {len(data)} / {total}")


if __name__ == "__main__":
    main()
