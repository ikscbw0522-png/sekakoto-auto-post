#!/usr/bin/env python3
"""カルーセル画像 + フック + ズーム効果でリール動画(9:16 MP4)を生成。

構成:
  [0.0-2.0s] フックスライド「"X"って8言語で言える？」
  [2.0-10.0s] 言語スライド8枚 × 1.0秒（ズームイン効果）
  [10.0-13.0s] CTAスライド「保存して旅先で📱」
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
REELS_DIR = BASE / "reels"

REEL_W, REEL_H = 1080, 1920
BG_COLOR = (244, 239, 230)
TEXT_PRIMARY = (55, 45, 40)
ACCENT = (215, 165, 90)

FONT_TOPPAN = "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/0ab217c39c45c7c6acaddfa199fd32c55a7b4a19.asset/AssetData/ToppanBunkyuGothicPr6N.ttc"
FONT_TSUKUSHI = "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/10b097deccb3c6126d986e24b1980031ff7399da.asset/AssetData/TsukushiBMaruGothic.ttc"

LANGS_ORDER = ["韓国語", "中国語", "タイ語", "ベトナム語", "インドネシア語", "ヒンディー語", "アラビア語", "トルコ語"]

HOOK_DURATION = 2.5
SLIDE_DURATION = 1.5
CTA_DURATION = 3.5


def get_phrase(theme: str) -> str:
    md = ARTICLES / f"{theme}_外国語.md"
    if md.exists():
        m = re.search(r"^#\s*「(.+?)」", md.read_text(encoding="utf-8"), re.MULTILINE)
        if m:
            return m.group(1)
    return theme


def make_hook(phrase: str, path: Path):
    img = Image.new("RGB", (REEL_W, REEL_H), (55, 45, 40))
    d = ImageDraw.Draw(img)

    # 上部：問いかけ
    f1 = ImageFont.truetype(FONT_TOPPAN, 82)
    q = "このフレーズ…"
    bbox = d.textbbox((0, 0), q, font=f1)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 380), q, font=f1, fill=(220, 210, 195))

    # メイン：テーマ名大きく
    f2 = ImageFont.truetype(FONT_TOPPAN, 200)
    phrase_text = f"「{phrase}」"
    # 幅に合わせてサイズ調整
    for sz in range(220, 80, -10):
        f2 = ImageFont.truetype(FONT_TOPPAN, sz)
        bbox = d.textbbox((0, 0), phrase_text, font=f2)
        if bbox[2]-bbox[0] <= REEL_W - 120:
            break
    bbox = d.textbbox((0, 0), phrase_text, font=f2)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 540), phrase_text, font=f2, fill=(255, 253, 248))

    # 下部：煽り
    f3 = ImageFont.truetype(FONT_TOPPAN, 90)
    k = "8言語で言える？"
    bbox = d.textbbox((0, 0), k, font=f3)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 820), k, font=f3, fill=ACCENT)

    # 下部装飾：黄色い下線
    d.rectangle([(REEL_W/2-150, 970), (REEL_W/2+150, 978)], fill=ACCENT)

    # スワイプ誘導
    f4 = ImageFont.truetype(FONT_TSUKUSHI, 60)
    s = "スワイプで正解↓"
    bbox = d.textbbox((0, 0), s, font=f4)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 1050), s, font=f4, fill=(220, 210, 195))

    # @brand
    f5 = ImageFont.truetype(FONT_TOPPAN, 48)
    b = "@sekakoto_dict"
    bbox = d.textbbox((0, 0), b, font=f5)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, REEL_H - 160), b, font=f5, fill=(220, 210, 195))

    img.save(path, "JPEG", quality=92)


def make_cta(path: Path):
    img = Image.new("RGB", (REEL_W, REEL_H), BG_COLOR)
    d = ImageDraw.Draw(img)

    # 上部帯
    d.rectangle([(0, 0), (REEL_W, 700)], fill=(55, 45, 40))

    f1 = ImageFont.truetype(FONT_TOPPAN, 130)
    msg = "保存しておこう"
    bbox = d.textbbox((0, 0), msg, font=f1)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 220), msg, font=f1, fill=(255, 253, 248))

    d.rectangle([(REEL_W/2-110, 410), (REEL_W/2+110, 420)], fill=ACCENT)

    f2 = ImageFont.truetype(FONT_TSUKUSHI, 58)
    s = "旅行で使えるフレーズ"
    bbox = d.textbbox((0, 0), s, font=f2)
    d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 470), s, font=f2, fill=(220, 210, 195))

    # 中央メッセージ
    f3 = ImageFont.truetype(FONT_TSUKUSHI, 58)
    for i, line in enumerate(["世界8言語のフレーズ", "毎日朝夜 自動更新中", "旅行・ビジネスで使える"]):
        bbox = d.textbbox((0, 0), line, font=f3)
        d.text(((REEL_W - (bbox[2]-bbox[0])) / 2, 830 + i * 110), line, font=f3, fill=TEXT_PRIMARY)

    # フォローボタン風
    f4 = ImageFont.truetype(FONT_TOPPAN, 70)
    fb = "フォローしてね"
    bbox = d.textbbox((0, 0), fb, font=f4)
    w = bbox[2] - bbox[0]
    pad = 40
    d.rounded_rectangle(
        [((REEL_W-w)/2 - pad, 1280), ((REEL_W+w)/2 + pad, 1400)],
        radius=60, fill=ACCENT,
    )
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


def pad_slide(src: Path, dst: Path):
    img = Image.open(src).convert("RGB")
    canvas = Image.new("RGB", (REEL_W, REEL_H), BG_COLOR)
    y = (REEL_H - img.height) // 2
    canvas.paste(img, (0, y))
    canvas.save(dst, "JPEG", quality=92)


def zoom_clip(path: str, duration: float, zoom_from=1.0, zoom_to=1.12):
    from moviepy import ImageClip

    def resize_func(t):
        progress = t / duration
        return zoom_from + (zoom_to - zoom_from) * progress

    clip = ImageClip(path).with_duration(duration)
    # Ken Burns風: ゆっくりズームイン
    clip = clip.resized(resize_func).with_position(("center", "center"))
    return clip


def generate_reel(theme: str) -> Path:
    from moviepy import CompositeVideoClip, ImageClip, concatenate_videoclips

    src_dir = CAROUSELS_DIR / theme
    images = sorted(src_dir.glob("*.jpg"))
    if len(images) != 10:
        sys.exit(f"画像数10枚必要: {len(images)}")

    REELS_DIR.mkdir(exist_ok=True)
    phrase = get_phrase(theme)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # フック
        hook = tmp_dir / "hook.jpg"
        make_hook(phrase, hook)

        # 言語スライド（index 1..8）→ パディング
        lang_padded = []
        for i in range(1, 9):
            dst = tmp_dir / f"lang_{i:02d}.jpg"
            pad_slide(images[i], dst)
            lang_padded.append(dst)

        # CTA
        cta = tmp_dir / "cta.jpg"
        make_cta(cta)

        clips = []
        clips.append(ImageClip(str(hook)).with_duration(HOOK_DURATION))
        for p in lang_padded:
            clips.append(ImageClip(str(p)).with_duration(SLIDE_DURATION))
        clips.append(ImageClip(str(cta)).with_duration(CTA_DURATION))

        video = concatenate_videoclips(clips, method="chain")
        out_path = REELS_DIR / f"{theme}.mp4"
        video.write_videofile(
            str(out_path), fps=30, codec="libx264", audio=False, preset="medium", logger=None,
        )
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", required=True)
    args = parser.parse_args()
    out = generate_reel(args.theme)
    size_mb = out.stat().st_size / 1024 / 1024
    print(f"✅ {out.name} ({size_mb:.1f}MB)")


if __name__ == "__main__":
    main()
