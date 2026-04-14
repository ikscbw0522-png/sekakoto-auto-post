#!/usr/bin/env python3
"""プロフィール用ロゴ画像生成（吹き出し×国旗カラー）"""
from PIL import Image, ImageDraw, ImageFont
import math

FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
SIZE = 1000

# 10言語の代表カラー（国旗の主要色）
LANG_COLORS = [
    (206, 17, 38),    # 韓国（赤）
    (237, 27, 36),    # 中国（赤）
    (237, 27, 36),    # タイ（赤）
    (218, 37, 29),    # ベトナム（赤）
    (237, 27, 36),    # インドネシア（赤）
    (0, 56, 168),     # タガログ（青）
    (1, 66, 106),     # マレー（紺）
    (255, 153, 51),   # ヒンディー（サフラン）
    (0, 109, 53),     # アラビア（緑）
    (227, 10, 23),    # トルコ（赤）
]


def make_logo(out_path: str):
    # 背景（グラデーション紺）
    img = Image.new("RGB", (SIZE, SIZE), (30, 50, 110))
    draw = ImageDraw.Draw(img)

    # 軽いグラデ
    for y in range(SIZE):
        shade = int(y * 0.08)
        draw.line([(0, y), (SIZE, y)], fill=(30 + shade, 50 + shade, 110 + shade))

    # 吹き出しの位置
    bubble_x = 150
    bubble_y = 200
    bubble_w = SIZE - 300
    bubble_h = 500
    radius = 60

    # 吹き出し本体（白）
    draw.rounded_rectangle(
        [(bubble_x, bubble_y), (bubble_x + bubble_w, bubble_y + bubble_h)],
        radius=radius,
        fill=(255, 255, 255),
    )
    # 吹き出しのしっぽ（三角）
    tail = [
        (SIZE // 2 - 50, bubble_y + bubble_h - 10),
        (SIZE // 2 + 50, bubble_y + bubble_h - 10),
        (SIZE // 2, bubble_y + bubble_h + 80),
    ]
    draw.polygon(tail, fill=(255, 255, 255))

    # 吹き出し内に「10言語」テキスト
    font_main = ImageFont.truetype(FONT_PATH, 220)
    text = "10言語"
    bbox = draw.textbbox((0, 0), text, font=font_main)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(
        ((SIZE - w) / 2, bubble_y + 130),
        text,
        font=font_main,
        fill=(30, 50, 110),
    )

    # 小さなサブテキスト
    font_sub = ImageFont.truetype(FONT_PATH, 60)
    sub = "世界のことば"
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    w = bbox[2] - bbox[0]
    draw.text(
        ((SIZE - w) / 2, bubble_y + 370),
        sub,
        font=font_sub,
        fill=(100, 120, 160),
    )

    # 吹き出しの周りに10色の小円（言語を表現）
    center_x, center_y = SIZE // 2, SIZE // 2
    dot_radius = 35
    ring_radius = 430
    for i, color in enumerate(LANG_COLORS):
        angle = math.radians(-90 + i * 36)  # 360 / 10 = 36度ずつ
        cx = center_x + ring_radius * math.cos(angle)
        cy = center_y + ring_radius * math.sin(angle)
        # 紺背景に被る位置はスキップ（吹き出し付近）
        if bubble_y - 30 < cy < bubble_y + bubble_h + 90:
            if bubble_x - 30 < cx < bubble_x + bubble_w + 30:
                continue
        draw.ellipse(
            [(cx - dot_radius, cy - dot_radius), (cx + dot_radius, cy + dot_radius)],
            fill=color,
            outline=(255, 255, 255),
            width=4,
        )

    img.save(out_path, "JPEG", quality=95)


if __name__ == "__main__":
    make_logo("logo.jpg")
    print("Generated: logo.jpg")
