#!/usr/bin/env python3
"""指定した投稿のpermalinkをIG APIから取得し、ig_embed_map.jsonに追加。"""
import json
import os
import sys
from pathlib import Path

import requests

BASE = Path(__file__).parent
MAP_JSON = BASE / "ig_embed_map.json"


def update(theme: str, media_id: str) -> bool:
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        env_path = BASE / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("IG_ACCESS_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break
    if not token:
        print("IG_ACCESS_TOKEN が取得できません")
        return False

    url = f"https://graph.instagram.com/v21.0/{media_id}"
    r = requests.get(url, params={"fields": "permalink,media_type", "access_token": token}, timeout=30)
    if r.status_code != 200:
        print(f"permalink取得失敗: {r.status_code} {r.text[:150]}")
        return False
    info = r.json()

    data = {}
    if MAP_JSON.exists():
        data = json.loads(MAP_JSON.read_text(encoding="utf-8"))
    data[theme] = {
        "permalink": info.get("permalink", ""),
        "media_type": info.get("media_type", ""),
        "media_id": media_id,
    }
    MAP_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ig_embed_map更新: {theme} -> {info.get('permalink')}")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: update_ig_embed_map.py <theme> <media_id>")
        sys.exit(1)
    ok = update(sys.argv[1], sys.argv[2])
    sys.exit(0 if ok else 1)
