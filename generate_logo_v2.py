#!/usr/bin/env python3
"""ロゴ3パターン生成"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
SIZE = 1000


def logo_a():
    """ミニマル文字ロゴ"""
    # クリーム色背景
    img = Image.new("RGB", (SIZE, SIZE), (248, 245, 238))
    draw = ImageDraw.Draw(img)

    # 濃紺の大きな「せかこと」
    font = ImageFont.truetype(FONT_PATH, 280)
    text = "せかこと"
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (SIZE - w) / 2
    y = (SIZE - h) / 2 - 40
    draw.text((x, y), text, font=font, fill=(25, 35, 70))

    # 下に細いアクセント線
    line_y = y + h + 60
    line_w = 300
    draw.rectangle(
        [((SIZE - line_w) / 2, line_y), ((SIZE + line_w) / 2, line_y + 8)],
        fill=(220, 100, 70),
    )

    # その下に小さく "10 LANGUAGES DICTIONARY"
    font_sub = ImageFont.truetype(FONT_PATH, 42)
    sub = "10 LANGUAGES DICTIONARY"
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    w = bbox[2] - bbox[0]
    draw.text(
        ((SIZE - w) / 2, line_y + 40),
        sub,
        font=font_sub,
        fill=(100, 100, 120),
    )

    img.save("logo_a.jpg", "JPEG", quality=95)


def logo_b():
    """地球＋吹き出し"""
    # グラデ背景
    img = Image.new("RGB", (SIZE, SIZE), (245, 248, 252))
    draw = ImageDraw.Draw(img)

    # 大きな円（地球）
    cx, cy = SIZE // 2, SIZE // 2 - 40
    r = 280
    # グラデ円（青系）
    for i in range(r, 0, -2):
        shade = int(i * 0.5)
        color = (
            max(20, 40 + shade - 50),
            max(80, 100 + shade - 50),
            max(140, 180 + shade - 50),
        )
        draw.ellipse([(cx - i, cy - i), (cx + i, cy + i)], fill=color)

    # 地球の経線（縦の楕円）
    for offset in [-200, -100, 0, 100, 200]:
        draw.arc(
            [(cx - abs(offset) - 50, cy - r), (cx + abs(offset) + 50, cy + r)],
            start=0,
            end=360,
            fill=(255, 255, 255, 80),
            width=3,
        )

    # 緯線（横の楕円）
    for y_offset in [-150, 0, 150]:
        ty = cy + y_offset
        tw = int(math.sqrt(r ** 2 - y_offset ** 2))
        draw.line(
            [(cx - tw, ty), (cx + tw, ty)],
            fill=(255, 255, 255, 100),
            width=3,
        )

    # 右上に吹き出し
    bubble_x = cx + 140
    bubble_y = cy - 260
    draw.ellipse(
        [(bubble_x, bubble_y), (bubble_x + 180, bubble_y + 150)],
        fill=(255, 200, 100),
    )
    # 吹き出しのしっぽ
    draw.polygon(
        [
            (bubble_x + 30, bubble_y + 120),
            (bubble_x + 60, bubble_y + 180),
            (bubble_x + 80, bubble_y + 130),
        ],
        fill=(255, 200, 100),
    )

    # 下にサイト名
    font = ImageFont.truetype(FONT_PATH, 100)
    text = "世界のことば"
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(
        ((SIZE - w) / 2, SIZE - 220),
        text,
        font=font,
        fill=(25, 35, 70),
    )

    font_sub = ImageFont.truetype(FONT_PATH, 55)
    sub = "10言語フレーズ辞典"
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    w = bbox[2] - bbox[0]
    draw.text(
        ((SIZE - w) / 2, SIZE - 100),
        sub,
        font=font_sub,
        fill=(100, 100, 120),
    )

    img.save("logo_b.jpg", "JPEG", quality=95)


def logo_c():
    """極太タイポ"""
    # ウォームオレンジ背景
    img = Image.new("RGB", (SIZE, SIZE), (235, 90, 50))
    draw = ImageDraw.Draw(img)

    # 大きな白い「世界」
    font = ImageFont.truetype(FONT_PATH, 420)
    text = "世界"
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(
        ((SIZE - w) / 2, (SIZE - h) / 2 - 60),
        text,
        font=font,
        fill=(255, 255, 255),
    )

    # 小さく英語
    font_sub = ImageFont.truetype(FONT_PATH, 60)
    sub = "SEKAI NO KOTOBA"
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    w = bbox[2] - bbox[0]
    draw.text(
        ((SIZE - w) / 2, SIZE - 200),
        sub,
        font=font_sub,
        fill=(255, 255, 255),
    )

    # 下部にドット10個（控えめ）
    for i in range(10):
        x = 200 + i * 65
        draw.ellipse(
            [(x, SIZE - 80), (x + 30, SIZE - 50)],
            fill=(255, 255, 255),
        )

    img.save("logo_c.jpg", "JPEG", quality=95)


if __name__ == "__main__":
    logo_a()
    logo_b()
    logo_c()
    print("Generated: logo_a.jpg, logo_b.jpg, logo_c.jpg")
