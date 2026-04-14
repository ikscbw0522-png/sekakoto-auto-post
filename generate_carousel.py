#!/usr/bin/env python3
"""Instagramカルーセル画像生成（1記事→11枚）"""
import os
import re
import glob
import math
from PIL import Image, ImageDraw, ImageFont

FONT_TSUKUSHI = "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/10b097deccb3c6126d986e24b1980031ff7399da.asset/AssetData/TsukushiBMaruGothic.ttc"
FONT_HIRAGINO = "/System/Library/Fonts/Hiragino Sans GB.ttc"

# 言語ごとに現地文字対応フォントを切り替え
LANG_FONTS = {
    "韓国語": "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "中国語": "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "タイ語": "/System/Library/Fonts/Supplemental/Ayuthaya.ttf",
    "ベトナム語": FONT_TSUKUSHI,  # ラテン拡張
    "インドネシア語": FONT_TSUKUSHI,
    "タガログ語": FONT_TSUKUSHI,
    "マレー語": FONT_TSUKUSHI,
    "ヒンディー語": "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
    "アラビア語": "/System/Library/Fonts/Supplemental/GeezaPro.ttc",
    "トルコ語": FONT_TSUKUSHI,  # ラテン拡張
}

SIZE = 1080  # Instagram正方形

# 言語ごとのテーマカラー（国旗系）
LANG_THEMES = {
    "韓国語": {"bg": (206, 17, 38), "accent": (255, 255, 255)},
    "中国語": {"bg": (237, 27, 36), "accent": (255, 222, 0)},
    "タイ語": {"bg": (42, 76, 155), "accent": (255, 255, 255)},
    "ベトナム語": {"bg": (218, 37, 29), "accent": (255, 222, 0)},
    "インドネシア語": {"bg": (237, 27, 36), "accent": (255, 255, 255)},
    "タガログ語": {"bg": (0, 56, 168), "accent": (255, 222, 0)},
    "マレー語": {"bg": (1, 66, 106), "accent": (255, 205, 0)},
    "ヒンディー語": {"bg": (255, 153, 51), "accent": (19, 136, 8)},
    "アラビア語": {"bg": (0, 109, 53), "accent": (255, 255, 255)},
    "トルコ語": {"bg": (227, 10, 23), "accent": (255, 255, 255)},
}


def parse_article(md_path: str):
    """記事から各言語セクションを抽出"""
    with open(md_path, encoding="utf-8") as f:
        md = f.read()

    # タイトル
    title_match = re.search(r"^# 「(.+?)」は外国語", md)
    phrase = title_match.group(1) if title_match else os.path.basename(md_path).replace("_外国語.md", "")

    # 各言語セクションを抽出
    sections = []
    for lang in LANG_THEMES.keys():
        # 言語名の後に括弧付き説明が来ることもあるため柔軟に
        pattern = rf"##\s+{re.escape(lang)}(?:（[^）]+）)?で「.+?」\s*\n+\*\*(.+?)[（(](.+?)[）)]\*\*"
        m = re.search(pattern, md)
        if m:
            native = m.group(1).strip()
            katakana = m.group(2).strip()
            sections.append({"lang": lang, "native": native, "katakana": katakana})

    return phrase, sections


def fit_font(draw, text, max_width, initial_size, font_path):
    """指定幅に収まるまでフォントサイズを下げる"""
    size = initial_size
    while size > 30:
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font, size
        size -= 5
    return ImageFont.truetype(font_path, 30), 30


def make_cover(phrase: str, out_path: str):
    """1枚目：表紙"""
    img = Image.new("RGB", (SIZE, SIZE), (25, 35, 70))
    draw = ImageDraw.Draw(img)

    # グラデ背景
    for y in range(SIZE):
        shade = int(y * 0.05)
        draw.line([(0, y), (SIZE, y)], fill=(25 + shade, 35 + shade, 70 + shade))

    # 上部アクセント
    draw.rectangle([(0, 120), (SIZE, 130)], fill=(255, 200, 100))

    # メインタイトル「○○」
    phrase_text = f"「{phrase}」"
    font, _ = fit_font(draw, phrase_text, SIZE - 160, 200, FONT_TSUKUSHI)
    bbox = draw.textbbox((0, 0), phrase_text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 280), phrase_text, font=font, fill=(255, 255, 255))

    # サブ「は外国語で何て言う？」
    font_sub = ImageFont.truetype(FONT_TSUKUSHI, 70)
    sub = "は外国語で何て言う？"
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 540), sub, font=font_sub, fill=(200, 215, 240))

    # 中央飾り
    draw.rectangle([(SIZE // 2 - 80, 680), (SIZE // 2 + 80, 686)], fill=(255, 200, 100))

    # 下部
    font_bottom = ImageFont.truetype(FONT_TSUKUSHI, 55)
    bottom = "10言語まとめ"
    bbox = draw.textbbox((0, 0), bottom, font=font_bottom)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 740), bottom, font=font_bottom, fill=(255, 255, 255))

    # スワイプ促進
    font_tiny = ImageFont.truetype(FONT_TSUKUSHI, 40)
    swipe = "→ スワイプして見る"
    bbox = draw.textbbox((0, 0), swipe, font=font_tiny)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, SIZE - 130), swipe, font=font_tiny, fill=(255, 200, 100))

    img.save(out_path, "JPEG", quality=92)


def make_language_slide(phrase: str, section: dict, slide_num: int, total: int, out_path: str):
    """2〜11枚目：各言語"""
    theme = LANG_THEMES[section["lang"]]
    img = Image.new("RGB", (SIZE, SIZE), theme["bg"])
    draw = ImageDraw.Draw(img)

    # 上部バー（言語名）
    bar_h = 160
    draw.rectangle([(0, 0), (SIZE, bar_h)], fill=theme["accent"])

    font_lang = ImageFont.truetype(FONT_TSUKUSHI, 80)
    lang_text = section["lang"]
    bbox = draw.textbbox((0, 0), lang_text, font=font_lang)
    w = bbox[2] - bbox[0]
    # アクセント色が白系ならテキストは背景色、黄色なら黒
    text_color = theme["bg"] if sum(theme["accent"]) > 500 else (20, 20, 20)
    draw.text(((SIZE - w) / 2, (bar_h - bbox[3]) / 2 - 5), lang_text, font=font_lang, fill=text_color)

    # 中央：現地文字（言語ごとに対応フォントを切替）
    native_font_path = LANG_FONTS.get(section["lang"], FONT_TSUKUSHI)
    native = section["native"]
    # アラビア語は形状変形＆RTL処理
    if section["lang"] == "アラビア語":
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            native = get_display(arabic_reshaper.reshape(native))
        except ImportError:
            pass
    font_native, _ = fit_font(draw, native, SIZE - 120, 180, native_font_path)
    bbox = draw.textbbox((0, 0), native, font=font_native)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 360), native, font=font_native, fill=(255, 255, 255))

    # カタカナ読み
    katakana = section["katakana"]
    font_kata, _ = fit_font(draw, katakana, SIZE - 160, 100, FONT_TSUKUSHI)
    bbox = draw.textbbox((0, 0), katakana, font=font_kata)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 620), katakana, font=font_kata, fill=theme["accent"])

    # 「ありがとう」（日本語意味）
    font_mean = ImageFont.truetype(FONT_TSUKUSHI, 50)
    mean = f"=「{phrase}」"
    bbox = draw.textbbox((0, 0), mean, font=font_mean)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 800), mean, font=font_mean, fill=(255, 255, 255))

    # ページ番号
    font_page = ImageFont.truetype(FONT_TSUKUSHI, 35)
    page = f"{slide_num} / {total}"
    draw.text((SIZE - 150, SIZE - 70), page, font=font_page, fill=theme["accent"])

    img.save(out_path, "JPEG", quality=92)


def make_cta(phrase: str, out_path: str):
    """最後の1枚：CTA"""
    img = Image.new("RGB", (SIZE, SIZE), (25, 35, 70))
    draw = ImageDraw.Draw(img)

    # グラデ
    for y in range(SIZE):
        shade = int(y * 0.05)
        draw.line([(0, y), (SIZE, y)], fill=(25 + shade, 35 + shade, 70 + shade))

    # メイン
    font = ImageFont.truetype(FONT_TSUKUSHI, 110)
    text = "もっと見る"
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 280), text, font=font, fill=(255, 200, 100))

    # サブ
    font_sub = ImageFont.truetype(FONT_TSUKUSHI, 70)
    sub = "世界のことば辞典"
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 430), sub, font=font_sub, fill=(255, 255, 255))

    # URL
    font_url = ImageFont.truetype(FONT_HIRAGINO, 55)
    url = "sekai-kotoba.com"
    bbox = draw.textbbox((0, 0), url, font=font_url)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 570), url, font=font_url, fill=(200, 215, 240))

    # 行動促進
    font_cta = ImageFont.truetype(FONT_TSUKUSHI, 50)
    cta = "プロフィールのリンクから"
    bbox = draw.textbbox((0, 0), cta, font=font_cta)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 720), cta, font=font_cta, fill=(255, 200, 100))

    # フォロー促進
    font_follow = ImageFont.truetype(FONT_TSUKUSHI, 45)
    follow = "フォローして毎日 1 フレーズ"
    bbox = draw.textbbox((0, 0), follow, font=font_follow)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 830), follow, font=font_follow, fill=(255, 255, 255))

    img.save(out_path, "JPEG", quality=92)


def generate_for_article(md_path: str, out_dir: str):
    """1記事分のカルーセル（11枚）を生成"""
    phrase, sections = parse_article(md_path)
    if len(sections) < 3:
        print(f"SKIP (セクション不足): {phrase} ({len(sections)}/10)")
        return False

    os.makedirs(out_dir, exist_ok=True)
    total = len(sections) + 2  # 表紙 + 言語 + CTA

    make_cover(phrase, os.path.join(out_dir, "01_cover.jpg"))
    for i, sec in enumerate(sections, 2):
        make_language_slide(phrase, sec, i, total, os.path.join(out_dir, f"{i:02d}_{sec['lang']}.jpg"))
    make_cta(phrase, os.path.join(out_dir, f"{total:02d}_cta.jpg"))

    return True


if __name__ == "__main__":
    import sys

    articles_dir = "記事サンプル"
    out_base = "carousels"

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 「ありがとう」1本だけテスト
        target = os.path.join(articles_dir, "ありがとう_外国語.md")
        generate_for_article(target, os.path.join(out_base, "arigatou"))
        print("生成完了: carousels/arigatou/")
    else:
        # 全記事
        files = sorted(glob.glob(os.path.join(articles_dir, "*.md")))
        print(f"対象: {len(files)} 記事")
        ok = 0
        for path in files:
            name = os.path.basename(path).replace("_外国語.md", "")
            out_dir = os.path.join(out_base, name)
            if generate_for_article(path, out_dir):
                ok += 1
        print(f"完了: {ok} / {len(files)}")
