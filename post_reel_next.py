#!/usr/bin/env python3
"""post_order.txt の未投稿テーマから1つ選んでReel投稿。

reel_posted.log に記録。post_next.py の Reel 版。

--voice: voice_reel_urls.json を参照して音声版Reelを投稿。
         voice版にテーマが無ければ通常版にフォールバック。
--convo: convo_reel_urls.json を参照して会話アニメ版Reelを投稿。
         convo版にテーマが無ければ通常版にフォールバック。
"""
import argparse
import datetime
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent
ORDER_FILE = BASE / "post_order.txt"
REEL_LOG = BASE / "reel_posted.log"
REEL_URLS = BASE / "reel_urls.json"
VOICE_REEL_URLS = BASE / "voice_reel_urls.json"
CONVO_REEL_URLS = BASE / "convo_reel_urls.json"


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

    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", action="store_true",
                        help="音声版Reelを優先投稿")
    parser.add_argument("--convo", action="store_true",
                        help="会話アニメ版Reelを優先投稿")
    args = parser.parse_args()

    voice_urls = {}
    convo_urls = {}
    if args.voice and VOICE_REEL_URLS.exists():
        voice_urls = json.loads(VOICE_REEL_URLS.read_text(encoding="utf-8"))
    if args.convo and CONVO_REEL_URLS.exists():
        convo_urls = json.loads(CONVO_REEL_URLS.read_text(encoding="utf-8"))
    urls = json.loads(REEL_URLS.read_text(encoding="utf-8"))
    order = [t.strip() for t in ORDER_FILE.read_text(encoding="utf-8").splitlines() if t.strip()]
    posted = load_posted()

    theme = None
    use_voice = False
    use_convo = False
    for t in order:
        if t in posted:
            continue
        if args.convo and t in convo_urls:
            theme = t
            use_convo = True
            break
        if args.voice and t in voice_urls:
            theme = t
            use_voice = True
            break
        if t in urls:
            theme = t
            break
    if not theme:
        print("全Reel投稿済み")
        sys.exit(0)

    label = '会話アニメ版' if use_convo else ('音声版' if use_voice else '通常版')
    print(f"次のReel: {theme} ({label})")
    cmd = ["python3", str(BASE / "post_reel.py"), "--theme", theme]
    if use_convo:
        cmd.append("--convo")
    elif use_voice:
        cmd.append("--voice")
    r = subprocess.run(cmd, capture_output=True, text=True)
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

    if media_id != "unknown":
        from update_ig_embed_map import update
        update(theme, media_id)


if __name__ == "__main__":
    main()
