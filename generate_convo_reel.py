#!/usr/bin/env python3
"""会話風アニメリール生成。例文を吹き出しで表示＋ネイティブ音声再生。

構成:
  [0-3s] フック
  [3-51s] 8言語 × 6秒（シーン・キャラ・吹き出しタイプライター・音声）
  [51-56s] CTA
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).parent
ARTICLES = BASE / "記事サンプル"
REELS_DIR = BASE / "convo_reels"
AVATARS_DIR = BASE / "avatars"

REEL_W, REEL_H = 1080, 1920
BG_COLOR = (244, 239, 230)
TEXT_PRIMARY = (55, 45, 40)
ACCENT = (215, 165, 90)

FONT_TOPPAN = "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/0ab217c39c45c7c6acaddfa199fd32c55a7b4a19.asset/AssetData/ToppanBunkyuGothicPr6N.ttc"
FONT_TSUKUSHI = "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/10b097deccb3c6126d986e24b1980031ff7399da.asset/AssetData/TsukushiBMaruGothic.ttc"
FONT_HELVETICA = "/System/Library/Fonts/Helvetica.ttc"  # ベトナム語・トルコ語・インドネシア語の声調符号をサポート

LANG_CONFIG = {
    "韓国語": {"tts": "ko", "voice": "ko-KR-SunHiNeural", "font": "/System/Library/Fonts/AppleSDGothicNeo.ttc", "bg": (255, 228, 230), "char_color": (200, 100, 110)},
    "中国語": {"tts": "zh-CN", "voice": "zh-CN-YunxiNeural", "font": "/System/Library/Fonts/Hiragino Sans GB.ttc", "bg": (255, 235, 215), "char_color": (210, 130, 80)},
    "タイ語": {"tts": "th", "voice": "th-TH-PremwadeeNeural", "font": "/System/Library/Fonts/Supplemental/Ayuthaya.ttf", "bg": (215, 232, 245), "char_color": (100, 140, 170)},
    "ベトナム語": {"tts": "vi", "voice": "vi-VN-HoaiMyNeural", "font": FONT_HELVETICA, "bg": (245, 220, 215), "char_color": (180, 110, 90)},
    "インドネシア語": {"tts": "id", "voice": "id-ID-ArdiNeural", "font": FONT_HELVETICA, "bg": (245, 225, 210), "char_color": (190, 130, 100)},
    "ヒンディー語": {"tts": "hi", "voice": "hi-IN-MadhurNeural", "font": "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc", "bg": (250, 235, 210), "char_color": (210, 150, 90)},
    "アラビア語": {"tts": "ar", "voice": "ar-SA-ZariyahNeural", "font": "/System/Library/Fonts/Supplemental/GeezaPro.ttc", "bg": (215, 240, 225), "char_color": (100, 140, 110)},
    "トルコ語": {"tts": "tr", "voice": "tr-TR-AhmetNeural", "font": FONT_HELVETICA, "bg": (245, 215, 218), "char_color": (180, 90, 95)},
}

HOOK_DURATION = 3.0
LANG_DURATION = 6.0
CTA_DURATION = 4.0
TYPING_SECONDS = 1.5  # タイプライター表示にかける秒数


def parse_article(theme: str):
    md_path = ARTICLES / f"{theme}_外国語.md"
    if not md_path.exists():
        return theme, []
    md = md_path.read_text(encoding="utf-8")
    m = re.search(r"^#\s*「(.+?)」", md, re.MULTILINE)
    phrase = m.group(1) if m else theme

    sections = []
    for lang in LANG_CONFIG:
        section_re = rf"##\s+{re.escape(lang)}(?:（[^）]+）)?で「[^」]+」"
        sec_m = re.search(section_re, md)
        if not sec_m:
            continue
        after = md[sec_m.end():sec_m.end() + 2000]
        # フレーズ
        phrase_m = re.search(r"\*\*([^（(*]+?)[（(]([^）)]+)[）)]\*\*", after)
        # 例文ブロック: **例文：** の直後 > ... > ...
        ex_m = re.search(r"\*\*例文：\*\*\s*\n+>\s*(.+?)[（(](.+?)[）)]\s*\n+>\s*(.+?)(?:\n|$)", after)
        if phrase_m and ex_m:
            sections.append({
                "lang": lang,
                "native": phrase_m.group(1).strip(),
                "katakana": phrase_m.group(2).strip(),
                "example_native": ex_m.group(1).strip(),
                "example_kata": ex_m.group(2).strip(),
                "example_ja": ex_m.group(3).strip(),
            })
    return phrase, sections


def gen_tts(text: str, lang_code: str, out_path: Path, voice: str = None):
    """edge-tts（voice指定時）またはgTTS（フォールバック）で音声生成。"""
    if voice:
        import asyncio
        import edge_tts
        async def _gen():
            comm = edge_tts.Communicate(text, voice)
            await comm.save(str(out_path))
        asyncio.run(_gen())
    else:
        from gtts import gTTS
        gTTS(text=text, lang=lang_code).save(str(out_path))


def _load_avatar(lang: str, open_mouth: bool = False):
    """avatars/{lang}.{png,jpg,jpeg} または {lang}_open.{...} を読み込む。なければ None。"""
    suffix = "_open" if open_mouth else ""
    for ext in ("png", "jpg", "jpeg", "PNG", "JPG", "JPEG"):
        p = AVATARS_DIR / f"{lang}{suffix}.{ext}"
        if p.exists():
            return Image.open(p).convert("RGB")
    return None


def _has_open_variant(lang: str) -> bool:
    return _load_avatar(lang, open_mouth=True) is not None


def _paste_photo_avatar(canvas: Image.Image, photo: Image.Image, cx: int, cy: int,
                         cfg: dict, offset_y: int = 0, scale: float = 1.0):
    """写真を言語カラーのリング枠内に円形マスクで貼り付ける。

    offset_y: アバター全体の縦方向シフト（呼吸用、±数px）
    scale: 枠内の写真スケール倍率（1.0 = 標準、>1 で拡大）
    """
    ring_color = cfg.get("char_color", (180, 130, 140))
    outer_r = 150
    inner_r = 138
    eff_cy = cy + offset_y

    # 外枠リング（言語カラー）- 枠自体は固定、中身だけ動かす
    draw = ImageDraw.Draw(canvas)
    draw.ellipse([(cx - outer_r, eff_cy - outer_r), (cx + outer_r, eff_cy + outer_r)],
                 fill=ring_color, outline=TEXT_PRIMARY, width=5)

    # 写真を円形にマスクして貼り付け
    diameter = inner_r * 2
    # scale 反映（拡大して中央クロップ）
    photo_diameter = int(diameter * scale)

    w, h = photo.size
    side = min(w, h)
    left = (w - side) // 2
    top = max(0, (h - side) // 2 - int(side * 0.08))  # 顔を少し上寄せ
    cropped = photo.crop((left, top, left + side, top + side)).resize((photo_diameter, photo_diameter), Image.LANCZOS)

    # 円形マスク（枠内サイズ）
    mask = Image.new("L", (diameter, diameter), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse((0, 0, diameter, diameter), fill=255)

    # 中央クロップしてマスクに合わせる
    crop_off = (photo_diameter - diameter) // 2
    cropped_fit = cropped.crop((crop_off, crop_off, crop_off + diameter, crop_off + diameter))
    canvas.paste(cropped_fit, (cx - inner_r, eff_cy - inner_r), mask)


def _draw_illustrated_avatar(d: ImageDraw.ImageDraw, cx: int, cy: int, cfg: dict, reveal_chars: int):
    """イラスト風アバター（写真がない場合のフォールバック）。"""
    skin = (255, 220, 180)
    hair = (90, 60, 45)
    bg_ring = cfg.get("char_color", (180, 130, 140))

    d.ellipse([(cx - 150, cy - 150), (cx + 150, cy + 150)], fill=bg_ring, outline=TEXT_PRIMARY, width=5)
    d.ellipse([(cx - 138, cy - 138), (cx + 138, cy + 138)], fill=(255, 253, 248))
    d.ellipse([(cx - 110, cy - 100), (cx + 110, cy + 100)], fill=skin, outline=TEXT_PRIMARY, width=4)
    d.chord([(cx - 110, cy - 120), (cx + 110, cy - 10)], start=180, end=360, fill=hair, outline=TEXT_PRIMARY, width=3)
    d.ellipse([(cx - 115, cy - 70), (cx - 70, cy - 20)], fill=hair, outline=TEXT_PRIMARY, width=2)
    d.ellipse([(cx + 70, cy - 70), (cx + 115, cy - 20)], fill=hair, outline=TEXT_PRIMARY, width=2)
    for ex, ey in [(-42, -5), (42, -5)]:
        d.ellipse([(cx + ex - 15, cy + ey - 17), (cx + ex + 15, cy + ey + 17)], fill=TEXT_PRIMARY)
        d.ellipse([(cx + ex - 4, cy + ey - 12), (cx + ex + 4, cy + ey - 4)], fill=(255, 255, 255))
    d.arc([(cx - 58, cy - 45), (cx - 22, cy - 25)], start=200, end=340, fill=TEXT_PRIMARY, width=4)
    d.arc([(cx + 22, cy - 45), (cx + 58, cy - 25)], start=200, end=340, fill=TEXT_PRIMARY, width=4)
    if reveal_chars > 5:
        d.ellipse([(cx - 18, cy + 35), (cx + 18, cy + 65)], fill=(180, 80, 90), outline=TEXT_PRIMARY, width=3)
    else:
        d.arc([(cx - 25, cy + 25), (cx + 25, cy + 60)], start=0, end=180, fill=TEXT_PRIMARY, width=4)
    d.ellipse([(cx - 85, cy + 15), (cx - 60, cy + 35)], fill=(245, 180, 180))
    d.ellipse([(cx + 60, cy + 15), (cx + 85, cy + 35)], fill=(245, 180, 180))


def reshape_arabic(text: str) -> str:
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except ImportError:
        return text


def fit_text(draw, text, max_w, max_h, font_path, initial=80, wrap_width=30):
    """テキストが枠に収まるサイズと折り返しを返す。"""
    import textwrap
    size = initial
    while size > 24:
        font = ImageFont.truetype(font_path, size)
        # 簡易折り返し
        wrap_w = max(10, int(max_w / (size * 0.6)))
        lines = textwrap.wrap(text, width=wrap_w) or [text]
        bbox = draw.textbbox((0, 0), "\n".join(lines), font=font, spacing=10)
        if (bbox[2]-bbox[0]) <= max_w and (bbox[3]-bbox[1]) <= max_h:
            return font, lines, size
        size -= 4
    font = ImageFont.truetype(font_path, 24)
    return font, textwrap.wrap(text, width=30) or [text], 24


def draw_hook(phrase: str, path: Path):
    img = Image.new("RGB", (REEL_W, REEL_H), (55, 45, 40))
    d = ImageDraw.Draw(img)
    f1 = ImageFont.truetype(FONT_TOPPAN, 78)
    q = "例文で覚える"
    bbox = d.textbbox((0, 0), q, font=f1)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 420), q, font=f1, fill=(220, 210, 195))

    for sz in range(220, 80, -10):
        f2 = ImageFont.truetype(FONT_TOPPAN, sz)
        bbox = d.textbbox((0, 0), f"「{phrase}」", font=f2)
        if bbox[2]-bbox[0] <= REEL_W - 120:
            break
    pt = f"「{phrase}」"
    bbox = d.textbbox((0, 0), pt, font=f2)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 560), pt, font=f2, fill=(255, 253, 248))

    f3 = ImageFont.truetype(FONT_TOPPAN, 76)
    k = "8言語のリアル会話 ♪"
    bbox = d.textbbox((0, 0), k, font=f3)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 860), k, font=f3, fill=ACCENT)

    d.rectangle([(REEL_W/2-150, 1000), (REEL_W/2+150, 1008)], fill=ACCENT)

    f4 = ImageFont.truetype(FONT_TSUKUSHI, 58)
    d.text(((REEL_W - d.textbbox((0,0),"スワイプで正解↓",font=f4)[2]) / 2, 1080), "スワイプで正解↓", font=f4, fill=(220, 210, 195))

    f5 = ImageFont.truetype(FONT_TOPPAN, 48)
    d.text(((REEL_W - d.textbbox((0,0),"@sekakoto_dict",font=f5)[2]) / 2, REEL_H - 160), "@sekakoto_dict", font=f5, fill=(220, 210, 195))
    img.save(path, "JPEG", quality=92)


def draw_slide(phrase: str, sec: dict, idx: int, total: int, reveal_chars: int, path: Path,
               mouth_open: bool = False, avatar_offset_y: int = 0, avatar_scale: float = 1.0):
    """会話風スライド。reveal_chars: 吹き出し内の表示済み文字数（タイプライター）。
    mouth_open: 写真アバター利用時、口開き版を使うか。
    avatar_offset_y: アバター縦シフト（呼吸アニメ用、±数px）
    avatar_scale: アバター写真のスケール（呼吸アニメ用、1.00〜1.03）
    """
    cfg = LANG_CONFIG[sec["lang"]]
    img = Image.new("RGB", (REEL_W, REEL_H), cfg["bg"])
    d = ImageDraw.Draw(img)

    # 上部情報バー
    f_num = ImageFont.truetype(FONT_TOPPAN, 40)
    d.text((60, 60), f"{idx:02d} / {total:02d}   {sec['lang']}", font=f_num, fill=TEXT_PRIMARY)
    # 番号の左に小さな丸マーカー（言語カラー）
    d.ellipse([(30, 68), (48, 86)], fill=ACCENT)

    # アバター配置
    char_cx, char_cy = 200, 620
    avatar_photo = _load_avatar(sec["lang"], open_mouth=mouth_open)
    if avatar_photo is None:
        # 口開き版がない場合は閉じ版にフォールバック
        avatar_photo = _load_avatar(sec["lang"], open_mouth=False)
    if avatar_photo is not None:
        _paste_photo_avatar(img, avatar_photo, char_cx, char_cy, cfg,
                             offset_y=avatar_offset_y, scale=avatar_scale)
    else:
        _draw_illustrated_avatar(d, char_cx, char_cy, cfg, reveal_chars)

    # 吹き出し（右側・大きめ）
    bubble_x0, bubble_y0 = char_cx + 150, 370
    bubble_x1, bubble_y1 = REEL_W - 80, 880
    d.rounded_rectangle([(bubble_x0, bubble_y0), (bubble_x1, bubble_y1)], radius=40, fill=(255, 253, 248), outline=TEXT_PRIMARY, width=4)

    # 吹き出しの尾（キャラ側に向けた小さな三角）
    d.polygon([
        (bubble_x0, bubble_y0 + 200),
        (bubble_x0 - 40, bubble_y0 + 230),
        (bubble_x0, bubble_y0 + 260),
    ], fill=(255, 253, 248), outline=TEXT_PRIMARY)
    d.line([(bubble_x0, bubble_y0 + 200), (bubble_x0 - 40, bubble_y0 + 230)], fill=TEXT_PRIMARY, width=4)
    d.line([(bubble_x0 - 40, bubble_y0 + 230), (bubble_x0, bubble_y0 + 260)], fill=TEXT_PRIMARY, width=4)
    # 内側線を消すための上書き
    d.line([(bubble_x0, bubble_y0 + 200), (bubble_x0, bubble_y0 + 260)], fill=(255, 253, 248), width=5)

    # 例文（ネイティブ文字・タイプライター表示）
    full_text = reshape_arabic(sec["example_native"]) if sec["lang"] == "アラビア語" else sec["example_native"]
    visible_text = full_text[:reveal_chars]

    bubble_w = bubble_x1 - bubble_x0 - 40
    bubble_h = bubble_y1 - bubble_y0 - 40
    f_native, lines, _ = fit_text(d, full_text, bubble_w, bubble_h - 120, cfg["font"], initial=68)
    # 表示中の文字を折り返し反映
    visible_full = "\n".join(lines)
    # 何文字目までかに合わせて切り取る
    visible = visible_full[:reveal_chars + visible_full.count("\n", 0, reveal_chars)]
    d.multiline_text(
        (bubble_x0 + 20, bubble_y0 + 30), visible,
        font=f_native, fill=TEXT_PRIMARY, spacing=10,
    )

    # カタカナ読み（吹き出し下部）- 吹き出し幅に収まるよう動的計算
    kata_max_w = bubble_x1 - bubble_x0 - 40
    kata_max_h = 200  # 下部120px領域
    f_kata, kata_lines, _ = fit_text(d, sec["example_kata"], kata_max_w, kata_max_h,
                                       FONT_TSUKUSHI, initial=44)
    d.multiline_text(
        (bubble_x0 + 20, bubble_y1 - 140), "\n".join(kata_lines),
        font=f_kata, fill=(140, 125, 115), spacing=6,
    )

    # 発音中マーク（音符アイコン + テキスト）- 吹き出し右下の下外、胴体右横に配置
    if reveal_chars > 5:
        mark_x = bubble_x0 + 40
        mark_y = bubble_y1 + 25
        # 音符を3つ描画
        for i, nx in enumerate([0, 34, 68]):
            nx += mark_x
            d.ellipse([(nx, mark_y + 14), (nx + 14, mark_y + 28)], fill=ACCENT)
            d.rectangle([(nx + 12, mark_y - 2), (nx + 16, mark_y + 20)], fill=ACCENT)
        f_head = ImageFont.truetype(FONT_TSUKUSHI, 40)
        d.text((mark_x + 120, mark_y - 2), "発音再生中", font=f_head, fill=(140, 125, 115))

    # 日本語訳（下部カード）
    ja_card = (80, 1100, REEL_W - 80, 1500)
    d.rounded_rectangle(ja_card, radius=30, fill=(255, 253, 248), outline=TEXT_PRIMARY, width=3)

    f_ja_label = ImageFont.truetype(FONT_TOPPAN, 40)
    d.text((ja_card[0] + 30, ja_card[1] + 20), "意味", font=f_ja_label, fill=(140, 125, 115))

    f_ja, ja_lines, _ = fit_text(d, sec["example_ja"], REEL_W - 220, 280, FONT_TSUKUSHI, initial=62)
    d.multiline_text(
        (ja_card[0] + 30, ja_card[1] + 90), "\n".join(ja_lines),
        font=f_ja, fill=TEXT_PRIMARY, spacing=10,
    )

    # キーワード（お題）強調: 言語別フォントで現地文字を描画
    native_key = reshape_arabic(sec["native"]) if sec["lang"] == "アラビア語" else sec["native"]
    prefix = "Key: "
    middle = " = "
    suffix = f"「{phrase}」"

    # サイズを順に試して全体が横に収まるよう調整
    for sz in [52, 46, 40, 36, 32]:
        f_pre = ImageFont.truetype(FONT_TOPPAN, sz)
        f_nat = ImageFont.truetype(cfg["font"], sz)
        f_mid = ImageFont.truetype(FONT_TOPPAN, sz)
        f_suf = ImageFont.truetype(FONT_TOPPAN, sz)
        w_pre = d.textbbox((0, 0), prefix, font=f_pre)[2]
        w_nat = d.textbbox((0, 0), native_key, font=f_nat)[2]
        w_mid = d.textbbox((0, 0), middle, font=f_mid)[2]
        w_suf = d.textbbox((0, 0), suffix, font=f_suf)[2]
        total_w = w_pre + w_nat + w_mid + w_suf
        if total_w <= REEL_W - 80:
            break

    start_x = (REEL_W - total_w) / 2
    y = 1570
    d.text((start_x, y), prefix, font=f_pre, fill=ACCENT)
    d.text((start_x + w_pre, y), native_key, font=f_nat, fill=ACCENT)
    d.text((start_x + w_pre + w_nat, y), middle, font=f_mid, fill=ACCENT)
    d.text((start_x + w_pre + w_nat + w_mid, y), suffix, font=f_suf, fill=ACCENT)

    # フッター
    f_brand = ImageFont.truetype(FONT_TOPPAN, 38)
    b = "@sekakoto_dict"
    bbox = d.textbbox((0, 0), b, font=f_brand)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, REEL_H - 80), b, font=f_brand, fill=(140, 125, 115))

    img.save(path, "JPEG", quality=92)


def draw_cta(path: Path):
    img = Image.new("RGB", (REEL_W, REEL_H), BG_COLOR)
    d = ImageDraw.Draw(img)
    d.rectangle([(0, 0), (REEL_W, 700)], fill=(55, 45, 40))
    f1 = ImageFont.truetype(FONT_TOPPAN, 120)
    msg = "保存して練習"
    bbox = d.textbbox((0, 0), msg, font=f1)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 240), msg, font=f1, fill=(255, 253, 248))
    d.rectangle([(REEL_W/2-110, 410), (REEL_W/2+110, 420)], fill=ACCENT)
    f2 = ImageFont.truetype(FONT_TSUKUSHI, 54)
    s = "例文ごと覚えると忘れない"
    bbox = d.textbbox((0, 0), s, font=f2)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 470), s, font=f2, fill=(220, 210, 195))
    f3 = ImageFont.truetype(FONT_TSUKUSHI, 56)
    for i, line in enumerate(["8言語のリアル会話を", "毎週自動で配信中🎧", "旅行・ビジネスで使える"]):
        bbox = d.textbbox((0, 0), line, font=f3)
        d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 830 + i * 110), line, font=f3, fill=TEXT_PRIMARY)
    f4 = ImageFont.truetype(FONT_TOPPAN, 70)
    fb = "フォローしてね"
    bbox = d.textbbox((0, 0), fb, font=f4)
    w = bbox[2] - bbox[0]
    pad = 40
    d.rounded_rectangle([((REEL_W-w)/2 - pad, 1280), ((REEL_W+w)/2 + pad, 1400)], radius=60, fill=ACCENT)
    d.text(((REEL_W - w) / 2, 1290), fb, font=f4, fill=(255, 255, 255))
    f5 = ImageFont.truetype(FONT_TOPPAN, 60)
    d.text(((REEL_W - d.textbbox((0,0),"@sekakoto_dict",font=f5)[2]) / 2, 1480), "@sekakoto_dict", font=f5, fill=TEXT_PRIMARY)
    f6 = ImageFont.truetype(FONT_TOPPAN, 42)
    d.text(((REEL_W - d.textbbox((0,0),"sekai-kotoba.com",font=f6)[2]) / 2, 1600), "sekai-kotoba.com", font=f6, fill=(140, 125, 115))
    img.save(path, "JPEG", quality=92)


def build_typing_frames(tmp_dir: Path, phrase: str, sec: dict, idx: int, total: int, frames: int = 15):
    """タイプライター風に文字数を増やしたフレーム画像を生成。"""
    paths = []
    full_len = len(sec["example_native"])
    for i in range(frames):
        progress = (i + 1) / frames
        reveal = max(1, int(full_len * progress))
        p = tmp_dir / f"slide_{idx:02d}_f{i:02d}.jpg"
        draw_slide(phrase, sec, idx, total, reveal, p)
        paths.append(p)
    # 完全表示のフレーム（リンガー）
    p = tmp_dir / f"slide_{idx:02d}_final.jpg"
    draw_slide(phrase, sec, idx, total, full_len, p)
    paths.append(p)
    return paths


def generate(theme: str) -> Path:
    from moviepy import AudioFileClip, CompositeAudioClip, ImageClip, concatenate_videoclips

    phrase, sections = parse_article(theme)
    if len(sections) < 4:
        sys.exit(f"例文データ不足: {len(sections)}言語しか取れません")

    REELS_DIR.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        hook = tmp_dir / "hook.jpg"
        draw_hook(phrase, hook)

        total = len(sections)
        video_clips = [ImageClip(str(hook)).with_duration(HOOK_DURATION)]
        audio_clips = []
        clip_start = HOOK_DURATION

        for i, sec in enumerate(sections, 1):
            # タイプライターフレーム（口閉じ）
            typing_frames = build_typing_frames(tmp_dir, phrase, sec, i, total, frames=15)
            per_frame = TYPING_SECONDS / 15
            for p in typing_frames[:-1]:
                video_clips.append(ImageClip(str(p)).with_duration(per_frame))

            # リンガー期間: 静止（口閉じ写真、アニメーションなし）
            linger = LANG_DURATION - TYPING_SECONDS
            video_clips.append(ImageClip(str(typing_frames[-1])).with_duration(linger))

            # 例文全体の音声
            audio_path = tmp_dir / f"audio_{i:02d}.mp3"
            try:
                cfg_lang = LANG_CONFIG[sec["lang"]]
                gen_tts(sec["example_native"], cfg_lang["tts"], audio_path, voice=cfg_lang.get("voice"))
                audio = AudioFileClip(str(audio_path))
                # タイプが終わる頃に再生開始
                audio_clips.append(audio.with_start(clip_start + TYPING_SECONDS - 0.3))
            except Exception as e:
                print(f"  音声失敗 {sec['lang']}: {e}", file=sys.stderr)

            clip_start += LANG_DURATION

        cta = tmp_dir / "cta.jpg"
        draw_cta(cta)
        video_clips.append(ImageClip(str(cta)).with_duration(CTA_DURATION))

        video = concatenate_videoclips(video_clips, method="chain")
        if audio_clips:
            video = video.with_audio(CompositeAudioClip(audio_clips))

        out = REELS_DIR / f"{theme}.mp4"
        raw = REELS_DIR / f"{theme}.raw.mp4"
        video.write_videofile(
            str(raw), fps=30, codec="libx264", audio_codec="aac",
            preset="medium", logger=None,
        )
        _reencode_for_ig(raw, out)
        raw.unlink(missing_ok=True)
    return out


def _reencode_for_ig(src: Path, dst: Path):
    """Instagram Reels 仕様に合わせて再エンコード（faststart, 48kHz AAC 192k, H.264 High）。"""
    import subprocess
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ff, "-y", "-i", str(src),
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
        "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
        "-r", "30", "-g", "60", "-keyint_min", "60",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        str(dst),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg re-encode failed: {r.stderr[-500:]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", required=True)
    args = parser.parse_args()
    out = generate(args.theme)
    size_mb = out.stat().st_size / 1024 / 1024
    print(f"✅ {out.name} ({size_mb:.1f}MB)")


if __name__ == "__main__":
    main()
