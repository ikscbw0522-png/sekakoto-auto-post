#!/usr/bin/env python3
"""posted.log / reel_posted.log から投稿IDを抽出し、
IG API で permalink を取得して ig_embed_map.json に保存。

WordPress側のPHPで記事スラッグ → テーマ → IG URLの流れで使用。
"""
import json
import re
import sys
from pathlib import Path

import requests

BASE = Path(__file__).parent
POSTED_LOG = BASE / "posted.log"
REEL_LOG = BASE / "reel_posted.log"
OUT = BASE / "ig_embed_map.json"
ENV_PATH = BASE / ".env"


def load_env():
    env = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def parse_log(path: Path):
    """'YYYY-MM-DD HH:MM theme (media_id)' をパース。"""
    entries = []
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\S+\s+\S+\s+(\S+?)\s+\((.+?)\)", line)
        if m:
            theme, info = m.group(1), m.group(2)
            mid = info.split(" - ")[-1] if " - " in info else info
            if mid.isdigit():
                entries.append((theme, mid))
    return entries


def get_permalink(media_id: str, token: str):
    url = f"https://graph.instagram.com/v21.0/{media_id}"
    r = requests.get(url, params={"fields": "permalink,media_type", "access_token": token}, timeout=30)
    if r.status_code == 200:
        return r.json()
    print(f"  {media_id}: {r.status_code} {r.text[:100]}", file=sys.stderr)
    return None


def main():
    env = load_env()
    token = env["IG_ACCESS_TOKEN"]

    data = {}
    if OUT.exists():
        data = json.loads(OUT.read_text(encoding="utf-8"))

    posts = parse_log(POSTED_LOG) + parse_log(REEL_LOG)
    print(f"投稿ログ: {len(posts)} 件")

    for theme, mid in posts:
        if theme in data:
            continue
        info = get_permalink(mid, token)
        if info and "permalink" in info:
            data[theme] = {
                "permalink": info["permalink"],
                "media_type": info.get("media_type", ""),
                "media_id": mid,
            }
            print(f"  ✅ {theme} -> {info['permalink']}")

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n保存: {len(data)} エントリ -> {OUT}")


if __name__ == "__main__":
    main()
