#!/usr/bin/env python3
"""全記事から8言語のフレーズを抽出してInstagramキャプションを一括生成。"""
import glob
import os
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).parent
ARTICLES = BASE / "記事サンプル"
OUT_DIR = BASE / "captions"

LANGS = ["韓国語", "中国語", "タイ語", "ベトナム語", "インドネシア語", "ヒンディー語", "アラビア語", "トルコ語"]


def romaji(theme: str) -> str:
    """テーマ名をASCIIファイル名化（シンプルハッシュ的）。"""
    safe = re.sub(r"[^\w]", "_", theme, flags=re.UNICODE)
    ascii_only = safe.encode("ascii", "ignore").decode()
    if ascii_only:
        return ascii_only
    return f"theme_{abs(hash(theme)) % 100000}"


def extract_phrase(md: str, basename: str) -> str:
    m = re.search(r"^#\s*「(.+?)」", md, re.MULTILINE)
    if m:
        return m.group(1)
    return basename.replace("_外国語", "")


def extract_katakana(md, lang):
    # パターン1: ## {lang}語 セクション直後の **native（katakana）**
    section_re = rf"##\s+{re.escape(lang)}(?:（[^）]+）)?で「[^」]+」"
    section_match = re.search(section_re, md)
    if section_match:
        after = md[section_match.end():section_match.end() + 500]
        m = re.search(r"\*\*[^（(*]+?[（(]([^）)]+)[）)]\*\*", after)
        if m:
            return m.group(1).strip()
    # パターン2: テーブル末尾 | {lang} | native | katakana |
    table_re = rf"\|\s*{re.escape(lang)}\s*\|\s*[^|]+\s*\|\s*([^|]+?)\s*\|"
    m = re.search(table_re, md)
    if m:
        return m.group(1).strip()
    return None


def generate_caption(phrase: str, readings: dict) -> str:
    lines = [f"「{phrase}」は8言語でなんて言う？🌏\n"]
    lines.append("その国の言葉で伝えると、一気に距離が縮まる。")
    lines.append("旅行・ビジネスで使えるフレーズを集めました✈️\n")
    for lang in LANGS:
        kana = readings.get(lang, "—")
        lines.append(f"📍{lang}：{kana}")
    lines.append("")
    lines.append("💡 保存しておくと旅先・商談で便利📱")
    lines.append("")
    lines.append("▶︎ 詳しい発音と例文は sekai-kotoba.com")
    lines.append("")
    lines.append("━━━━━━━━━━━━")
    lines.append("世界のことばフレーズ辞典📚")
    lines.append("@sekakoto_dict をフォロー")
    lines.append("━━━━━━━━━━━━")
    lines.append("")
    hashtags = (
        "#世界のことば辞典 #多言語学習 #外国語 #韓国語 #中国語 #タイ語 "
        "#ベトナム語 #インドネシア語 #ヒンディー語 #アラビア語 #トルコ語 "
        f"#海外旅行 #旅行フレーズ #{phrase} #語学 #言語学習 #勉強垢"
    )
    lines.append(hashtags)
    return "\n".join(lines) + "\n"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    articles = sorted(ARTICLES.glob("*.md"))
    print(f"対象記事: {len(articles)}")

    ok, skip, partial = 0, 0, 0
    for md_path in articles:
        basename = md_path.stem
        md = md_path.read_text(encoding="utf-8")
        phrase = extract_phrase(md, basename)
        readings = {}
        missing = []
        for lang in LANGS:
            kana = extract_katakana(md, lang)
            if kana:
                readings[lang] = kana
            else:
                missing.append(lang)

        if len(readings) == 0:
            print(f"[スキップ] {phrase}: 言語データ0件")
            skip += 1
            continue
        if missing:
            print(f"[部分] {phrase}: 未取得 {missing}")
            partial += 1

        caption = generate_caption(phrase, readings)
        theme_name = basename.replace("_外国語", "")
        out_name = f"{theme_name}.txt"
        (OUT_DIR / out_name).write_text(caption, encoding="utf-8")
        ok += 1

    print(f"\n完了: 正常 {ok} / 部分 {partial} / スキップ {skip}")
    print(f"出力先: {OUT_DIR}")


if __name__ == "__main__":
    main()
