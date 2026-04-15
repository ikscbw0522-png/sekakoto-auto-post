#!/usr/bin/env python3
"""post_order.txt を読み、未投稿テーマを1つ選んで投稿し、posted.log に記録。

GitHub Actions から定期実行される想定。環境変数 IG_USER_ID 等を利用。
"""
import datetime
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent
ORDER_FILE = BASE / "post_order.txt"
POSTED_LOG = BASE / "posted.log"
CAPTIONS_DIR = BASE / "captions"
CAROUSELS_DIR = BASE / "carousels_v3"


def load_order():
    return [t.strip() for t in ORDER_FILE.read_text(encoding="utf-8").splitlines() if t.strip()]


def load_posted():
    if not POSTED_LOG.exists():
        return set()
    posted = set()
    for line in POSTED_LOG.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split(" ", 2)
        if len(parts) >= 3:
            posted.add(parts[2].split(" (")[0])
    return posted


def pick_next():
    order = load_order()
    posted = load_posted()
    for theme in order:
        if theme in posted:
            continue
        if not (CAPTIONS_DIR / f"{theme}.txt").exists():
            print(f"skip (no caption): {theme}")
            continue
        if not (CAROUSELS_DIR / theme).is_dir():
            print(f"skip (no images): {theme}")
            continue
        return theme
    return None


def log_posted(theme: str, media_id: str):
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
    with open(POSTED_LOG, "a", encoding="utf-8") as f:
        f.write(f"{now} {theme} ({media_id})\n")


def main():
    theme = pick_next()
    if not theme:
        print("全テーマ投稿済み、またはキュー空")
        sys.exit(0)

    print(f"次の投稿テーマ: {theme}")
    result = subprocess.run(
        ["python3", str(BASE / "post_to_instagram.py"), "--theme", theme],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    media_id = "unknown"
    for line in result.stdout.splitlines():
        if "投稿ID:" in line:
            media_id = line.split("投稿ID:")[-1].strip()
    log_posted(theme, media_id)
    print(f"記録完了: {theme} ({media_id})")

    if media_id != "unknown":
        from update_ig_embed_map import update
        update(theme, media_id)


if __name__ == "__main__":
    main()
