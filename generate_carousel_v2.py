#!/usr/bin/env python3
"""Instagramカルーセル画像v2（1080x1350・くすみパステル・ミニマル）"""
import os
import re
import glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_TSUKUSHI = "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/10b097deccb3c6126d986e24b1980031ff7399da.asset/AssetData/TsukushiBMaruGothic.ttc"
FONT_TOPPAN = "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/0ab217c39c45c7c6acaddfa199fd32c55a7b4a19.asset/AssetData/ToppanBunkyuGothicPr6N.ttc"
FONT_HIRAGINO = "/System/Library/Fonts/Hiragino Sans GB.ttc"

# 言語ごとの現地文字フォント
LANG_FONTS = {
    "韓国語": "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "中国語": "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "タイ語": "/System/Library/Fonts/Supplemental/Ayuthaya.ttf",
    "ベトナム語": FONT_TSUKUSHI,
    "インドネシア語": FONT_TSUKUSHI,
    "タガログ語": FONT_TSUKUSHI,
    "マレー語": FONT_TSUKUSHI,
    "ヒンディー語": "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
    "アラビア語": "/System/Library/Fonts/Supplemental/GeezaPro.ttc",
    "トルコ語": FONT_TSUKUSHI,
}

# 各言語のアクセントカラー（くすみ系に調整）
LANG_ACCENT = {
    "韓国語": (200, 100, 110),      # くすみローズ
    "中国語": (210, 130, 80),       # テラコッタ
    "タイ語": (100, 140, 170),      # くすみブルー
    "ベトナム語": (180, 110, 90),   # くすみレッド
    "インドネシア語": (190, 130, 100),  # くすみオレンジ
    "タガログ語": (110, 130, 175),  # ブルーグレー
    "マレー語": (85, 120, 140),     # ダスティブルー
    "ヒンディー語": (210, 150, 90), # サフラン系
    "アラビア語": (100, 140, 110),  # セージグリーン
    "トルコ語": (180, 90, 95),      # くすみレッド
}

WIDTH, HEIGHT = 1080, 1350
BG_COLOR = (244, 239, 230)  # 温かみのあるクリーム
TEXT_PRIMARY = (55, 45, 40)  # ダークブラウン
TEXT_SECONDARY = (140, 125, 115)  # グレージュ


def parse_article(md_path: str):
    with open(md_path, encoding="utf-8") as f:
        md = f.read()
    title_match = re.search(r"^# 「(.+?)」は外国語", md)
    phrase = title_match.group(1) if title_match else os.path.basename(md_path).replace("_外国語.md", "")

    sections = []
    for lang in LANG_FONTS.keys():
        pattern = rf"##\s+{re.escape(lang)}(?:（[^）]+）)?で「.+?」\s*\n+\*\*(.+?)[（(](.+?)[）)]\*\*"
        m = re.search(pattern, md)
        if m:
            sections.append({
                "lang": lang,
                "native": m.group(1).strip(),
                "katakana": m.group(2).strip(),
            })
    return phrase, sections


def fit_font(draw, text, max_width, initial_size, font_path):
    size = initial_size
    while size > 30:
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font, size
        size -= 5
    return ImageFont.truetype(font_path, 30), 30


def reshape_if_arabic(lang: str, text: str) -> str:
    if lang == "アラビア語":
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            return get_display(arabic_reshaper.reshape(text))
        except ImportError:
            pass
    return text


def make_cover(phrase: str, out_path: str):
    """表紙：クリーム背景＋大きなタイトル"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 上部に横ライン（10色の細い帯＝10言語の示唆）
    bar_top = 120
    stripe_h = 14
    stripe_w = (WIDTH - 200) // 10
    colors = list(LANG_ACCENT.values())
    for i, c in enumerate(colors):
        x0 = 100 + i * stripe_w
        draw.rectangle([(x0, bar_top), (x0 + stripe_w - 6, bar_top + stripe_h)], fill=c)

    # サブキャッチ（上）
    font_small = ImageFont.truetype(FONT_TOPPAN, 44)
    pre = "世界10言語で覚える"
    bbox = draw.textbbox((0, 0), pre, font=font_small)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, 220), pre, font=font_small, fill=TEXT_SECONDARY)

    # メインタイトル
    phrase_text = f"「{phrase}」"
    font_main, _ = fit_font(draw, phrase_text, WIDTH - 160, 200, FONT_TOPPAN)
    bbox = draw.textbbox((0, 0), phrase_text, font=font_main)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((WIDTH - w) / 2, 340), phrase_text, font=font_main, fill=TEXT_PRIMARY)

    # サブタイトル
    font_sub = ImageFont.truetype(FONT_TSUKUSHI, 58)
    sub = "って外国語で何て言う？"
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, 570), sub, font=font_sub, fill=TEXT_PRIMARY)

    # 中央装飾：黄色い下線
    draw.rectangle(
        [(WIDTH // 2 - 100, 680), (WIDTH // 2 + 100, 686)],
        fill=(215, 165, 90),
    )

    # 10ヶ国リスト（小さく）
    font_list = ImageFont.truetype(FONT_TSUKUSHI, 42)
    row1 = "韓 / 中 / タイ / ベト / インドネシア"
    row2 = "タガログ / マレー / ヒンディー / アラビア / トルコ"
    for i, line in enumerate([row1, row2]):
        bbox = draw.textbbox((0, 0), line, font=font_list)
        w = bbox[2] - bbox[0]
        draw.text(((WIDTH - w) / 2, 750 + i * 60), line, font=font_list, fill=TEXT_SECONDARY)

    # 下部：スワイプ促進
    swipe_y = HEIGHT - 240

    # 小さなドット
    for i in range(3):
        draw.ellipse(
            [(WIDTH // 2 - 30 + i * 30, swipe_y - 10), (WIDTH // 2 - 10 + i * 30, swipe_y + 10)],
            fill=(215, 165, 90) if i == 0 else (220, 210, 195),
        )

    font_swipe = ImageFont.truetype(FONT_TSUKUSHI, 38)
    swipe = "スワイプして見る →"
    bbox = draw.textbbox((0, 0), swipe, font=font_swipe)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, swipe_y + 50), swipe, font=font_swipe, fill=(215, 165, 90))

    # フッター
    font_brand = ImageFont.truetype(FONT_TOPPAN, 34)
    brand = "@sekakoto_dict"
    bbox = draw.textbbox((0, 0), brand, font=font_brand)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, HEIGHT - 90), brand, font=font_brand, fill=TEXT_SECONDARY)

    img.save(out_path, "JPEG", quality=92)


def make_language_slide(phrase: str, section: dict, slide_num: int, total: int, out_path: str):
    """各言語スライド：クリーム背景＋アクセントカラー"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    accent = LANG_ACCENT[section["lang"]]

    # 上部：アクセントカラーの帯（細め）＋言語名
    band_h = 260
    draw.rectangle([(0, 0), (WIDTH, band_h)], fill=accent)

    # 番号（左上）
    font_num = ImageFont.truetype(FONT_TOPPAN, 32)
    num = f"{slide_num - 1:02d} / 10"
    draw.text((60, 50), num, font=font_num, fill=(255, 255, 255, 200))

    # 言語名（中央大きく）
    font_lang = ImageFont.truetype(FONT_TOPPAN, 88)
    lang = section["lang"]
    bbox = draw.textbbox((0, 0), lang, font=font_lang)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, 110), lang, font=font_lang, fill=(255, 255, 255))

    # 中央：カード（白背景）
    card_x0, card_y0 = 80, 330
    card_x1, card_y1 = WIDTH - 80, HEIGHT - 280
    draw.rounded_rectangle(
        [(card_x0, card_y0), (card_x1, card_y1)],
        radius=40,
        fill=(255, 253, 248),
    )

    # カード内：現地文字（アラビア語はRTL処理）
    native = reshape_if_arabic(section["lang"], section["native"])
    native_font_path = LANG_FONTS.get(section["lang"], FONT_TSUKUSHI)
    font_native, _ = fit_font(draw, native, card_x1 - card_x0 - 80, 170, native_font_path)
    bbox = draw.textbbox((0, 0), native, font=font_native)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, card_y0 + 100), native, font=font_native, fill=TEXT_PRIMARY)

    # 区切り線
    draw.rectangle(
        [(WIDTH // 2 - 60, card_y0 + 360), (WIDTH // 2 + 60, card_y0 + 364)],
        fill=accent,
    )

    # カタカナ読み
    katakana = section["katakana"]
    font_kata, _ = fit_font(draw, katakana, card_x1 - card_x0 - 80, 95, FONT_TSUKUSHI)
    bbox = draw.textbbox((0, 0), katakana, font=font_kata)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, card_y0 + 420), katakana, font=font_kata, fill=accent)

    # 意味
    font_mean = ImageFont.truetype(FONT_TSUKUSHI, 48)
    mean = f"意味：「{phrase}」"
    bbox = draw.textbbox((0, 0), mean, font=font_mean)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, card_y0 + 570), mean, font=font_mean, fill=TEXT_SECONDARY)

    # 下部：フッター
    font_brand = ImageFont.truetype(FONT_TOPPAN, 30)
    brand = "@sekakoto_dict"
    bbox = draw.textbbox((0, 0), brand, font=font_brand)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, HEIGHT - 80), brand, font=font_brand, fill=TEXT_SECONDARY)

    img.save(out_path, "JPEG", quality=92)


def make_cta(phrase: str, out_path: str):
    """CTA：保存とフォロー促進"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 上部：彩色ブロック
    block_h = 500
    draw.rectangle([(0, 0), (WIDTH, block_h)], fill=(55, 45, 40))

    # 上部メイン
    font_save = ImageFont.truetype(FONT_TOPPAN, 110)
    save_text = "保存しておこう"
    bbox = draw.textbbox((0, 0), save_text, font=font_save)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, 140), save_text, font=font_save, fill=(255, 253, 248))

    # アクセントライン
    draw.rectangle(
        [(WIDTH // 2 - 100, 290), (WIDTH // 2 + 100, 296)],
        fill=(215, 165, 90),
    )

    # サブ
    font_sub = ImageFont.truetype(FONT_TSUKUSHI, 52)
    sub = "旅行で使えるフレーズ"
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, 340), sub, font=font_sub, fill=(220, 210, 195))

    # 中央：メッセージ
    font_msg = ImageFont.truetype(FONT_TSUKUSHI, 48)
    messages = [
        "世界10言語のフレーズを",
        "毎日1つ更新中",
        "旅行・ビジネスで使える表現",
    ]
    for i, msg in enumerate(messages):
        bbox = draw.textbbox((0, 0), msg, font=font_msg)
        w = bbox[2] - bbox[0]
        draw.text(((WIDTH - w) / 2, 620 + i * 80), msg, font=font_msg, fill=TEXT_PRIMARY)

    # フォローCTA
    font_follow = ImageFont.truetype(FONT_TOPPAN, 56)
    follow = "フォローしてね"
    bbox = draw.textbbox((0, 0), follow, font=font_follow)
    w = bbox[2] - bbox[0]
    # 黄色いボックス
    pad = 30
    box_x0 = (WIDTH - w) / 2 - pad
    box_x1 = (WIDTH + w) / 2 + pad
    box_y0 = 960
    box_y1 = 1060
    draw.rounded_rectangle(
        [(box_x0, box_y0), (box_x1, box_y1)],
        radius=50,
        fill=(215, 165, 90),
    )
    draw.text(((WIDTH - w) / 2, box_y0 + 18), follow, font=font_follow, fill=(255, 255, 255))

    # アカウント
    font_brand = ImageFont.truetype(FONT_TOPPAN, 44)
    brand = "@sekakoto_dict"
    bbox = draw.textbbox((0, 0), brand, font=font_brand)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, 1120), brand, font=font_brand, fill=TEXT_PRIMARY)

    # サイトURL
    font_url = ImageFont.truetype(FONT_TOPPAN, 34)
    url = "sekai-kotoba.com"
    bbox = draw.textbbox((0, 0), url, font=font_url)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, 1200), url, font=font_url, fill=TEXT_SECONDARY)

    img.save(out_path, "JPEG", quality=92)


def generate_for_article(md_path: str, out_dir: str):
    phrase, sections = parse_article(md_path)
    if len(sections) < 3:
        return False

    os.makedirs(out_dir, exist_ok=True)
    total = len(sections) + 2

    make_cover(phrase, os.path.join(out_dir, "01_cover.jpg"))
    for i, sec in enumerate(sections, 2):
        make_language_slide(phrase, sec, i, total, os.path.join(out_dir, f"{i:02d}_{sec['lang']}.jpg"))
    make_cta(phrase, os.path.join(out_dir, f"{total:02d}_cta.jpg"))
    return True


if __name__ == "__main__":
    import sys
    articles_dir = "記事サンプル"
    out_base = "carousels_v2"

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        target = os.path.join(articles_dir, "ありがとう_外国語.md")
        generate_for_article(target, os.path.join(out_base, "arigatou"))
        print("生成完了: carousels_v2/arigatou/")
    else:
        files = sorted(glob.glob(os.path.join(articles_dir, "*.md")))
        print(f"対象: {len(files)} 記事")
        ok = 0
        for path in files:
            name = os.path.basename(path).replace("_外国語.md", "")
            out_dir = os.path.join(out_base, name)
            if generate_for_article(path, out_dir):
                ok += 1
        print(f"完了: {ok} / {len(files)}")
