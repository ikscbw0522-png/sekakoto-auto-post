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


CAPTION_PATTERNS = {
    0: "travel",     # 旅行実用型
    1: "quiz",       # クイズ型
    2: "empathy",    # 共感型
    3: "trivia",     # 豆知識型
}


def _lang_list_block(readings: dict) -> list[str]:
    """8言語のカタカナ読みリストを返す共通パーツ。"""
    lines = []
    for lang in LANGS:
        kana = readings.get(lang, "—")
        lines.append(f"📍{lang}：{kana}")
    return lines


def _footer_block(phrase: str) -> list[str]:
    """キャプション末尾の共通フッターブロック。"""
    return [
        "",
        "▶︎ 発音・例文・文化背景もっと詳しく👇",
        "プロフィールのリンクからブログへ🔗",
        "",
        "━━━━━━━━━━━━",
        "世界のことばフレーズ辞典📚",
        "@sekakoto_dict をフォロー",
        "━━━━━━━━━━━━",
        "",
        (
            "#世界のことば辞典 #多言語学習 #外国語 #韓国語 #中国語 #タイ語 "
            "#ベトナム語 #インドネシア語 #ヒンディー語 #アラビア語 #トルコ語 "
            f"#海外旅行 #旅行フレーズ #{phrase} #語学 #言語学習 #勉強垢"
        ),
    ]


def _caption_travel(phrase: str, readings: dict) -> str:
    """パターン1: 旅行実用型"""
    lines = [f"✈️ 旅先で「{phrase}」って言いたい！\n"]
    lines.append("🔖 旅行前に保存しておくと現地で慌てない\n")
    lines.append("現地の言葉でひとこと伝えるだけで、")
    lines.append("お店の人の笑顔が変わります。\n")
    lines += _lang_list_block(readings)
    lines.append("")
    lines.append("💡 スクショ保存しておけば旅先でサッと使える📱")
    lines += _footer_block(phrase)
    return "\n".join(lines) + "\n"


def _caption_quiz(phrase: str, readings: dict) -> str:
    """パターン2: クイズ型"""
    lines = [f"🤔 「{phrase}」の発音、全部わかる？\n"]
    lines.append("🔖 スクショして答え合わせ→後で見返せる\n")
    lines.append("8言語のうち何個読めるかチャレンジ！")
    lines.append("答え合わせしてみて👇\n")
    lines += _lang_list_block(readings)
    lines.append("")
    lines.append("🎯 全問正解できた人はコメントで教えて！")
    lines += _footer_block(phrase)
    return "\n".join(lines) + "\n"


def _caption_empathy(phrase: str, readings: dict) -> str:
    """パターン3: 共感型"""
    lines = [f"😅 海外で「{phrase}」が言えなくて困った経験ありませんか？\n"]
    lines.append("🔖 次こそ言えるように、今のうちに保存しておこう\n")
    lines.append("実はカタカナ読みを覚えるだけで通じるんです。\n")
    lines += _lang_list_block(readings)
    lines.append("")
    lines.append("💬 あなたの「言えなくて困った」エピソード、コメントで聞かせて！")
    lines += _footer_block(phrase)
    return "\n".join(lines) + "\n"


def _caption_trivia(phrase: str, readings: dict) -> str:
    """パターン4: 豆知識型"""
    lines = [f"📚 8言語で「{phrase}」を比べてみたら面白い発見が！\n"]
    lines.append("🔖 保存して、ゆっくり見比べてみて\n")
    lines.append("同じ意味でも、言語によって音の響きが全然違う。")
    lines.append("似てる言語・全く違う言語、見比べてみて👀\n")
    lines += _lang_list_block(readings)
    lines.append("")
    lines.append("💡 言語の違いを知ると世界の見え方が変わる🌍")
    lines += _footer_block(phrase)
    return "\n".join(lines) + "\n"


_CAPTION_FUNCS = [_caption_travel, _caption_quiz, _caption_empathy, _caption_trivia]


def generate_caption(phrase: str, readings: dict, pattern_idx: int = 0) -> str:
    """パターン番号に応じたキャプションを生成。"""
    func = _CAPTION_FUNCS[pattern_idx % len(_CAPTION_FUNCS)]
    return func(phrase, readings)


def _load_post_order() -> list[str]:
    """post_order.txt を読み込み、テーマ名のリストを返す。"""
    order_path = BASE / "post_order.txt"
    if order_path.exists():
        return [line.strip() for line in order_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return []


def main():
    OUT_DIR.mkdir(exist_ok=True)
    articles = sorted(ARTICLES.glob("*.md"))
    print(f"対象記事: {len(articles)}")

    # post_order.txt からテーマ順を取得し、パターン割り当てマップを作成
    post_order = _load_post_order()
    theme_to_pattern: dict[str, int] = {}
    for i, theme in enumerate(post_order):
        theme_to_pattern[theme] = i % len(_CAPTION_FUNCS)

    pattern_names = ["旅行実用型", "クイズ型", "共感型", "豆知識型"]

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

        theme_name = basename.replace("_外国語", "")
        # post_order に載っていればその順番でパターン決定、なければハッシュで
        pattern_idx = theme_to_pattern.get(theme_name, hash(theme_name) % len(_CAPTION_FUNCS))
        caption = generate_caption(phrase, readings, pattern_idx=pattern_idx)
        out_name = f"{theme_name}.txt"
        (OUT_DIR / out_name).write_text(caption, encoding="utf-8")
        print(f"  [{pattern_names[pattern_idx % len(pattern_names)]}] {theme_name}")
        ok += 1

    print(f"\n完了: 正常 {ok} / 部分 {partial} / スキップ {skip}")
    print(f"パターン: {' / '.join(pattern_names)} を順番にローテーション")
    print(f"出力先: {OUT_DIR}")


if __name__ == "__main__":
    main()
