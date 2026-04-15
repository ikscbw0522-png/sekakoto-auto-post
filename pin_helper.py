#!/usr/bin/env python3
"""初期10ピンのタイトル・説明文・画像パス・記事リンクを生成。"""
import json
from pathlib import Path

BASE = Path(__file__).parent
SLUG_MAP = json.loads((BASE / "slug_to_theme.json").read_text(encoding="utf-8"))
CAP_DIR = BASE / "captions"
CAROUSEL_DIR = BASE / "carousels_v3"

INITIAL_10 = [
    "ありがとう", "おはよう", "おいしい", "いくらですか", "ごめんなさい",
    "こんにちは", "さようなら", "乾杯", "大好き", "お疲れ様です",
]

theme_to_slug = {v: k for k, v in SLUG_MAP.items()}

print("=" * 70)
print("Pinterest 初期ピン10本 作成用データ")
print("=" * 70)

for i, theme in enumerate(INITIAL_10, 1):
    slug = theme_to_slug.get(theme, "")
    if not slug:
        print(f"\n[{i}] {theme}: 記事スラッグ未発見（スキップ）")
        continue
    url = f"https://sekai-kotoba.com/{slug}/"
    img = CAROUSEL_DIR / theme / "01_cover.jpg"
    caption_file = CAP_DIR / f"{theme}.txt"
    desc = "海外で使える多言語フレーズ集。旅行・ビジネスで役立つ一言を10言語で紹介。"
    if caption_file.exists():
        lines = caption_file.read_text(encoding="utf-8").splitlines()
        # 最初の本文部分（2〜4行目）を説明に使う
        desc_lines = [l for l in lines[2:8] if l.strip() and not l.startswith("📍")]
        if desc_lines:
            desc = " ".join(desc_lines[:2]).strip()

    print(f"\n{'=' * 70}")
    print(f"[{i}/10] テーマ: {theme}")
    print(f"{'─' * 70}")
    print(f"■ タイトル（60文字以内推奨）:")
    print(f"  「{theme}」は8言語でなんて言う？海外旅行で使えるフレーズ集")
    print(f"\n■ 説明文:")
    print(f"  {desc}")
    print(f"  #多言語 #外国語 #海外旅行 #語学学習 #世界のことば辞典 #{theme}")
    print(f"\n■ リンク先URL:")
    print(f"  {url}")
    print(f"\n■ 画像ファイル:")
    print(f"  {img}")

print(f"\n{'=' * 70}")
print("各テーマの情報をコピペしてPinterestで作成してください")
print("=" * 70)
