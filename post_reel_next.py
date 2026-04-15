#!/usr/bin/env python3
"""post_order.txt の未投稿テーマから1つ選んでReel投稿。

reel_posted.log に記録。post_next.py の Reel 版。
"""
import datetime
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent
ORDER_FILE = BASE / "post_order.txt"
REEL_LOG = BASE / "reel_posted.log"
REEL_URLS = BASE / "reel_urls.json"


def load_posted():
    if not REEL_LOG.exists():
        return set()
    posted = set()
    for line in REEL_LOG.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split(" ", 2)
        if len(parts) >= 3:
            posted.add(parts[2].split(" (")[0])
    return posted


def main():
    import json
    urls = json.loads(REEL_URLS.read_text(encoding="utf-8"))
    order = [t.strip() for t in ORDER_FILE.read_text(encoding="utf-8").splitlines() if t.strip()]
    posted = load_posted()

    theme = None
    for t in order:
        if t not in posted and t in urls:
            theme = t
            break
    if not theme:
        print("全Reel投稿済み")
        sys.exit(0)

    print(f"次のReel: {theme}")
    r = subprocess.run(
        ["python3", str(BASE / "post_reel.py"), "--theme", theme],
        capture_output=True, text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)

    media_id = "unknown"
    for line in r.stdout.splitlines():
        if "投稿ID:" in line:
            media_id = line.split("投稿ID:")[-1].strip()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
    with open(REEL_LOG, "a", encoding="utf-8") as f:
        f.write(f"{now} {theme} ({media_id})\n")
    print(f"記録: {theme} ({media_id})")


if __name__ == "__main__":
    main()
