#!/usr/bin/env python3
"""post_order.txt の未投稿テーマのうち、Hyperframes URL登録済のものを1本投稿。

reel_posted.log をチェックして同テーマの重複投稿を避ける。

Usage:
    python3 publish_hf_next.py           # 次の未投稿Hyperframesテーマを投稿
    python3 publish_hf_next.py --dry-run # 対象テーマだけ表示
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
ORDER_FILE = ROOT / "post_order.txt"
REEL_LOG = ROOT / "reel_posted.log"
HF_URLS = HERE / "hyperframes_reel_urls.json"
OUTPUT_DIR = HERE / "output"


def load_posted_themes() -> set:
    """reel_posted.log から投稿済テーマを収集。"""
    if not REEL_LOG.exists():
        return set()
    posted = set()
    for line in REEL_LOG.read_text(encoding="utf-8").splitlines():
        # 例: 2026-04-20 13:55 おはよう (18086233694525406) [hyperframes]
        m = re.match(r"^\S+\s+\S+\s+(.+?)\s+\(\d+\)", line)
        if m:
            posted.add(m.group(1))
    return posted


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--caption-file", help="明示指定時のキャプションtxt")
    args = p.parse_args()

    if not HF_URLS.exists():
        sys.exit(f"{HF_URLS} が存在しません")
    urls = json.loads(HF_URLS.read_text(encoding="utf-8"))
    order = [t.strip() for t in ORDER_FILE.read_text(encoding="utf-8").splitlines() if t.strip()]
    posted = load_posted_themes()

    # 次の未投稿かつHyperframes URL登録済のテーマ
    target = None
    for t in order:
        if t in posted:
            continue
        if t in urls:
            target = t
            break

    if not target:
        print("❌ 対象テーマなし（全テーマ投稿済 or URL未登録）")
        print(f"  登録済URL: {len(urls)}本")
        print(f"  投稿済: {len(posted)}本")
        sys.exit(0)

    print(f"🎯 次のHyperframes投稿対象: {target}")
    print(f"   URL: {urls[target]}")

    if args.dry_run:
        print("\n[dry-run] 実投稿なし")
        return

    # MP4ファイルパスを特定（output/{theme}.mp4 があるはず）
    mp4 = OUTPUT_DIR / f"{target}.mp4"
    if not mp4.exists():
        print(f"⚠️  MP4ローカル無し: {mp4}")
        print(f"   WP上にはあるのでskip-upload経由で投稿可能")

    # publish_hf.py を --skip-upload で呼ぶ
    cmd = [
        "python3", str(HERE / "publish_hf.py"),
        "--mp4", str(mp4) if mp4.exists() else str(OUTPUT_DIR / f"{target}.mp4"),
        "--theme", target,
        "--skip-upload",
    ]
    if args.caption_file:
        cmd.extend(["--caption-file", args.caption_file])

    print(f"\n▶ {' '.join(cmd)}\n")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
