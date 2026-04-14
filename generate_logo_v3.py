#!/usr/bin/env python3
"""ロゴB改良版（複数フォント比較）"""
from PIL import Image, ImageDraw, ImageFont
import math

FONTS = {
    "yumincho": "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/e9a9a2d18358033875835a6228cb70ce84b7e47c.asset/AssetData/YuMincho.ttc",
    "klee": "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/f110a45f1759f86c645cfd2f47baba57aa50056e.asset/AssetData/Klee.ttc",
    "toppan": "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/0ab217c39c45c7c6acaddfa199fd32c55a7b4a19.asset/AssetData/ToppanBunkyuGothicPr6N.ttc",
    "tsukushi": "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/10b097deccb3c6126d986e24b1980031ff7399da.asset/AssetData/TsukushiBMaruGothic.ttc",
}

SIZE = 1000


def make_logo_b(font_key: str, out_path: str):
    font_path = FONTS[font_key]
    img = Image.new("RGB", (SIZE, SIZE), (245, 248, 252))
    draw = ImageDraw.Draw(img)

    # 地球（グラデ青）
    cx, cy = SIZE // 2, 420
    r = 260
    for i in range(r, 0, -2):
        shade = int((r - i) * 0.35)
        color = (
            max(30, 70 - shade // 3),
            max(100, 140 - shade // 3),
            max(170, 210 - shade // 3),
        )
        draw.ellipse([(cx - i, cy - i), (cx + i, cy + i)], fill=color)

    # 地球の経線（中央1本＋左右）
    for offset in [0, 120, -120]:
        draw.arc(
            [(cx + offset - 150, cy - r), (cx + offset + 150, cy + r)],
            start=0,
            end=360,
            fill=(255, 255, 255, 150),
            width=3,
        )

    # 緯線
    for y_offset in [-120, 0, 120]:
        ty = cy + y_offset
        if abs(y_offset) < r:
            tw = int(math.sqrt(r ** 2 - y_offset ** 2))
            draw.line([(cx - tw, ty), (cx + tw, ty)], fill=(255, 255, 255, 130), width=3)

    # 右上の吹き出し（黄色）
    bx, by = cx + 130, cy - 240
    draw.ellipse([(bx, by), (bx + 180, by + 150)], fill=(255, 200, 100))
    draw.polygon(
        [(bx + 30, by + 120), (bx + 60, by + 185), (bx + 85, by + 135)],
        fill=(255, 200, 100),
    )

    # メインタイトル
    font_main = ImageFont.truetype(font_path, 115)
    text = "世界のことば"
    bbox = draw.textbbox((0, 0), text, font=font_main)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 755), text, font=font_main, fill=(25, 35, 70))

    # サブ
    font_sub = ImageFont.truetype(font_path, 52)
    sub = "10言語フレーズ辞典"
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    w = bbox[2] - bbox[0]
    draw.text(((SIZE - w) / 2, 900), sub, font=font_sub, fill=(100, 110, 140))

    img.save(out_path, "JPEG", quality=95)


if __name__ == "__main__":
    for key in FONTS:
        make_logo_b(key, f"logo_b_{key}.jpg")
        print(f"Generated: logo_b_{key}.jpg")
