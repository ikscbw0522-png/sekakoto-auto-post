#!/usr/bin/env python3
"""全テーマのリール動画を一括生成。既存分はスキップして再開可能。"""
import sys
from pathlib import Path

from generate_reel import generate_reel, CAROUSELS_DIR, REELS_DIR

BASE = Path(__file__).parent


def main():
    REELS_DIR.mkdir(exist_ok=True)
    themes = sorted([p.name for p in CAROUSELS_DIR.iterdir() if p.is_dir()])
    total = len(themes)
    ok = skip = fail = 0
    for i, theme in enumerate(themes, 1):
        out = REELS_DIR / f"{theme}.mp4"
        if out.exists() and out.stat().st_size > 100_000:
            skip += 1
            continue
        try:
            generate_reel(theme)
            ok += 1
            print(f"[{i}/{total}] ✅ {theme}")
        except SystemExit as e:
            print(f"[{i}/{total}] ❌ {theme}: {e}", file=sys.stderr)
            fail += 1
        except Exception as e:
            print(f"[{i}/{total}] ❌ {theme}: {e}", file=sys.stderr)
            fail += 1
    print(f"\n完了: 生成{ok} / スキップ{skip} / 失敗{fail}")


if __name__ == "__main__":
    main()
