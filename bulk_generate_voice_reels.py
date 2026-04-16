#!/usr/bin/env python3
"""全テーマの音声付きリール動画を一括生成。既存分はスキップして再開可能。"""
import argparse
import sys
import time
from pathlib import Path

from generate_voice_reel import generate, REELS_DIR

BASE = Path(__file__).parent
ARTICLES = BASE / "記事サンプル"


def discover_themes():
    """記事サンプルから全テーマを取得（_外国語.md サフィックス除去）。"""
    themes = []
    for p in sorted(ARTICLES.glob("*_外国語.md")):
        themes.append(p.stem.replace("_外国語", ""))
    return themes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0,
                        help="生成する最大本数（0=全件）")
    parser.add_argument("--themes", nargs="*",
                        help="テーマ指定（スペース区切り）。指定時は --limit 無視")
    args = parser.parse_args()

    REELS_DIR.mkdir(exist_ok=True)

    themes = args.themes or discover_themes()
    total = len(themes)
    ok = skip = fail = 0
    elapsed_total = 0.0

    for i, theme in enumerate(themes, 1):
        out = REELS_DIR / f"{theme}.mp4"
        if out.exists() and out.stat().st_size > 100_000:
            skip += 1
            continue

        if args.limit and ok >= args.limit:
            break

        t0 = time.time()
        try:
            generate(theme)
            dt = time.time() - t0
            elapsed_total += dt
            ok += 1
            size_mb = out.stat().st_size / 1024 / 1024
            print(f"[{i}/{total}] ✅ {theme} ({size_mb:.1f}MB, {dt:.1f}s)")
        except SystemExit as e:
            fail += 1
            print(f"[{i}/{total}] ❌ {theme}: {e}", file=sys.stderr)
        except Exception as e:
            fail += 1
            print(f"[{i}/{total}] ❌ {theme}: {e}", file=sys.stderr)

    print(f"\n完了: 生成{ok} / スキップ{skip} / 失敗{fail}")
    if ok:
        print(f"平均生成時間: {elapsed_total/ok:.1f}s/本")


if __name__ == "__main__":
    main()
