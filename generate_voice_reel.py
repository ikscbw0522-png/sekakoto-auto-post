#!/usr/bin/env python3
"""音声付きリール動画生成。各言語スライドでネイティブ発音を再生。

構成:
  [0-2.5s] フック
  [2.5-34.5s] 8言語 × 4秒（表示1s + 音声再生 + 翻訳）
  [34.5-38s] CTA
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).parent
CAROUSELS_DIR = BASE / "carousels_v3"
ARTICLES = BASE / "記事サンプル"
REELS_DIR = BASE / "voice_reels"

REEL_W, REEL_H = 1080, 1920
BG_COLOR = (244, 239, 230)
TEXT_PRIMARY = (55, 45, 40)
ACCENT = (215, 165, 90)

FONT_TOPPAN = "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/0ab217c39c45c7c6acaddfa199fd32c55a7b4a19.asset/AssetData/ToppanBunkyuGothicPr6N.ttc"
FONT_TSUKUSHI = "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/10b097deccb3c6126d986e24b1980031ff7399da.asset/AssetData/TsukushiBMaruGothic.ttc"

LANG_CONFIG = {
    "韓国語": {"tts": "ko", "flag": "🇰🇷", "font": "/System/Library/Fonts/AppleSDGothicNeo.ttc", "accent": (200, 100, 110)},
    "中国語": {"tts": "zh-CN", "flag": "🇨🇳", "font": "/System/Library/Fonts/Hiragino Sans GB.ttc", "accent": (210, 130, 80)},
    "タイ語": {"tts": "th", "flag": "🇹🇭", "font": "/System/Library/Fonts/Supplemental/Ayuthaya.ttf", "accent": (100, 140, 170)},
    "ベトナム語": {"tts": "vi", "flag": "🇻🇳", "font": FONT_TSUKUSHI, "accent": (180, 110, 90)},
    "インドネシア語": {"tts": "id", "flag": "🇮🇩", "font": FONT_TSUKUSHI, "accent": (190, 130, 100)},
    "ヒンディー語": {"tts": "hi", "flag": "🇮🇳", "font": "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc", "accent": (210, 150, 90)},
    "アラビア語": {"tts": "ar", "flag": "🇸🇦", "font": "/System/Library/Fonts/Supplemental/GeezaPro.ttc", "accent": (100, 140, 110)},
    "トルコ語": {"tts": "tr", "flag": "🇹🇷", "font": FONT_TSUKUSHI, "accent": (180, 90, 95)},
}

HOOK_DURATION = 2.5
LANG_DURATION = 4.0
CTA_DURATION = 3.5


def parse_article(theme: str):
    """記事から phrase, sections 抽出。"""
    md_path = ARTICLES / f"{theme}_外国語.md"
    if not md_path.exists():
        return theme, []
    md = md_path.read_text(encoding="utf-8")
    m = re.search(r"^#\s*「(.+?)」", md, re.MULTILINE)
    phrase = m.group(1) if m else theme

    sections = []
    for lang in LANG_CONFIG:
        # メイン本文の **native（katakana）** を抽出
        section_re = rf"##\s+{re.escape(lang)}(?:（[^）]+）)?で「[^」]+」"
        sec_m = re.search(section_re, md)
        native = katakana = None
        if sec_m:
            after = md[sec_m.end():sec_m.end() + 500]
            m2 = re.search(r"\*\*([^（(*]+?)[（(]([^）)]+)[）)]\*\*", after)
            if m2:
                native = m2.group(1).strip()
                katakana = m2.group(2).strip()
        # テーブル末尾からのフォールバック
        if not native:
            t_m = re.search(rf"\|\s*{re.escape(lang)}\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", md)
            if t_m:
                native = t_m.group(1).strip()
                katakana = t_m.group(2).strip()
        if native and katakana:
            sections.append({"lang": lang, "native": native, "katakana": katakana})
    return phrase, sections


def gen_tts(text: str, lang_code: str, out_path: Path):
    from gtts import gTTS
    gTTS(text=text, lang=lang_code).save(str(out_path))


HOOK_PATTERNS = [
    {"top": "旅先でこれ言えなかったら…", "bottom": "8言語ネイティブ発音"},
    {"top": "これ、8言語で言える？", "bottom": "全部聞いてみて"},
    {"top": "1つだけ発音が超意外", "bottom": "どの言語かわかる？"},
    {"top": "海外で一番使うフレーズ", "bottom": "8言語マスターしよう"},
]


def draw_hook(phrase: str, path: Path, pattern_idx: int = 0):
    pat = HOOK_PATTERNS[pattern_idx % len(HOOK_PATTERNS)]
    img = Image.new("RGB", (REEL_W, REEL_H), (55, 45, 40))
    d = ImageDraw.Draw(img)

    # 上部テキスト（感情フック）
    f1 = ImageFont.truetype(FONT_TOPPAN, 78)
    q = pat["top"]
    bbox = d.textbbox((0, 0), q, font=f1)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 360), q, font=f1, fill=(220, 210, 195))

    # フレーズ（大きく目立つ）
    for sz in range(220, 80, -10):
        f2 = ImageFont.truetype(FONT_TOPPAN, sz)
        bbox = d.textbbox((0, 0), f"「{phrase}」", font=f2)
        if bbox[2]-bbox[0] <= REEL_W - 120:
            break
    pt = f"「{phrase}」"
    bbox = d.textbbox((0, 0), pt, font=f2)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 530), pt, font=f2, fill=(255, 253, 248))

    # 下部テキスト（行動促進）
    f3 = ImageFont.truetype(FONT_TOPPAN, 78)
    k = pat["bottom"]
    bbox = d.textbbox((0, 0), k, font=f3)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 810), k, font=f3, fill=ACCENT)

    d.rectangle([(REEL_W/2-150, 960), (REEL_W/2+150, 968)], fill=ACCENT)

    f5 = ImageFont.truetype(FONT_TOPPAN, 48)
    d.text(((REEL_W - d.textbbox((0,0),"@sekakoto_dict",font=f5)[2]) / 2, REEL_H - 160), "@sekakoto_dict", font=f5, fill=(220, 210, 195))
    img.save(path, "JPEG", quality=92)


def draw_language_slide(phrase: str, sec: dict, idx: int, total: int, path: Path):
    img = Image.new("RGB", (REEL_W, REEL_H), BG_COLOR)
    d = ImageDraw.Draw(img)
    cfg = LANG_CONFIG[sec["lang"]]
    accent = cfg["accent"]

    # 上部帯：言語名 + 国旗
    d.rectangle([(0, 0), (REEL_W, 340)], fill=accent)
    f_num = ImageFont.truetype(FONT_TOPPAN, 40)
    d.text((60, 60), f"{idx:02d} / {total:02d}", font=f_num, fill=(255, 255, 255))

    # 国旗絵文字はPILで描画が不安定なので省略

    f_lang = ImageFont.truetype(FONT_TOPPAN, 110)
    bbox = d.textbbox((0, 0), sec["lang"], font=f_lang)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 170), sec["lang"], font=f_lang, fill=(255, 255, 255))

    # カード
    card = (80, 460, REEL_W - 80, REEL_H - 400)
    d.rounded_rectangle(card, radius=40, fill=(255, 253, 248))

    # 現地文字（大きく）
    native = sec["native"]
    if sec["lang"] == "アラビア語":
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            native = get_display(arabic_reshaper.reshape(native))
        except ImportError:
            pass

    for sz in range(220, 80, -10):
        f_native = ImageFont.truetype(cfg["font"], sz)
        bbox = d.textbbox((0, 0), native, font=f_native)
        if bbox[2]-bbox[0] <= card[2] - card[0] - 80:
            break
    bbox = d.textbbox((0, 0), native, font=f_native)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 580), native, font=f_native, fill=TEXT_PRIMARY)

    # 区切り線
    d.rectangle([(REEL_W/2 - 80, 900), (REEL_W/2 + 80, 906)], fill=accent)

    # カタカナ読み
    f_kata = ImageFont.truetype(FONT_TSUKUSHI, 100)
    bbox = d.textbbox((0, 0), sec["katakana"], font=f_kata)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 960), sec["katakana"], font=f_kata, fill=accent)

    # 意味
    f_mean = ImageFont.truetype(FONT_TSUKUSHI, 64)
    mean = f"意味：「{phrase}」"
    bbox = d.textbbox((0, 0), mean, font=f_mean)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 1200), mean, font=f_mean, fill=TEXT_PRIMARY)

    # 🎧 マーク
    f_head = ImageFont.truetype(FONT_TSUKUSHI, 50)
    d.text((REEL_W/2 - 100, 1380), "🎧 発音再生中", font=f_head, fill=(140, 125, 115))

    # フッター
    f_brand = ImageFont.truetype(FONT_TOPPAN, 38)
    b = "@sekakoto_dict"
    bbox = d.textbbox((0, 0), b, font=f_brand)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, REEL_H - 100), b, font=f_brand, fill=(140, 125, 115))

    img.save(path, "JPEG", quality=92)


def draw_cta(path: Path):
    img = Image.new("RGB", (REEL_W, REEL_H), BG_COLOR)
    d = ImageDraw.Draw(img)
    d.rectangle([(0, 0), (REEL_W, 700)], fill=(55, 45, 40))
    f1 = ImageFont.truetype(FONT_TOPPAN, 130)
    msg = "保存しておこう"
    bbox = d.textbbox((0, 0), msg, font=f1)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 220), msg, font=f1, fill=(255, 253, 248))
    d.rectangle([(REEL_W/2-110, 410), (REEL_W/2+110, 420)], fill=ACCENT)
    f2 = ImageFont.truetype(FONT_TSUKUSHI, 58)
    s = "発音を繰り返し練習しよう"
    bbox = d.textbbox((0, 0), s, font=f2)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 470), s, font=f2, fill=(220, 210, 195))
    f3 = ImageFont.truetype(FONT_TSUKUSHI, 58)
    for i, line in enumerate(["世界8言語のフレーズ辞典", "毎日自動更新", "音声付きリールも配信中🎧"]):
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
    ac = "@sekakoto_dict"
    bbox = d.textbbox((0, 0), ac, font=f5)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 1480), ac, font=f5, fill=TEXT_PRIMARY)
    f6 = ImageFont.truetype(FONT_TOPPAN, 42)
    url = "sekai-kotoba.com"
    bbox = d.textbbox((0, 0), url, font=f6)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 1600), url, font=f6, fill=(140, 125, 115))
    img.save(path, "JPEG", quality=92)


def generate(theme: str) -> Path:
    from moviepy import AudioFileClip, CompositeAudioClip, ImageClip, concatenate_videoclips

    phrase, sections = parse_article(theme)
    if len(sections) < 4:
        sys.exit(f"言語データ不足: {len(sections)}言語しか取れません")

    REELS_DIR.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # Hook
        hook_img = tmp_dir / "hook.jpg"
        # テーマ名のハッシュでフックパターンをローテーション
        pattern_idx = hash(theme) % len(HOOK_PATTERNS)
        draw_hook(phrase, hook_img, pattern_idx=pattern_idx)

        # 各言語スライド + 音声
        total = len(sections)
        slide_clips = []
        audio_clips = []
        clip_start = HOOK_DURATION
        for i, sec in enumerate(sections, 1):
            img_path = tmp_dir / f"lang_{i:02d}.jpg"
            draw_language_slide(phrase, sec, i, total, img_path)
            slide_clips.append((img_path, LANG_DURATION))

            # TTS
            audio_path = tmp_dir / f"audio_{i:02d}.mp3"
            try:
                gen_tts(sec["native"], LANG_CONFIG[sec["lang"]]["tts"], audio_path)
                audio = AudioFileClip(str(audio_path))
                # スライド開始1秒後に再生開始
                audio_clips.append(audio.with_start(clip_start + 1.0))
            except Exception as e:
                print(f"  音声生成失敗 {sec['lang']}: {e}", file=sys.stderr)
            clip_start += LANG_DURATION

        # CTA
        cta_img = tmp_dir / "cta.jpg"
        draw_cta(cta_img)

        # 動画組み立て
        all_clips = [ImageClip(str(hook_img)).with_duration(HOOK_DURATION)]
        for img_path, dur in slide_clips:
            all_clips.append(ImageClip(str(img_path)).with_duration(dur))
        all_clips.append(ImageClip(str(cta_img)).with_duration(CTA_DURATION))

        video = concatenate_videoclips(all_clips, method="chain")

        if audio_clips:
            audio = CompositeAudioClip(audio_clips)
            video = video.with_audio(audio)

        out = REELS_DIR / f"{theme}.mp4"
        raw = REELS_DIR / f"{theme}.raw.mp4"
        video.write_videofile(
            str(raw),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            logger=None,
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
