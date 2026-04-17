#!/usr/bin/env python3
"""既存アバター画像から口開き版を自動生成。

mediapipe Face Mesh で口のランドマークを検出し、
口の内側に暗い領域（開いた口）と歯のハイライトを合成する。

使用例:
    python3 generate_mouth_open.py --src avatars/韓国語.jpeg
    → avatars/韓国語_open.jpeg を生成
"""
import argparse
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np


# mediapipe Face Mesh の口周りランドマーク番号
LIPS_OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291,
              409, 270, 269, 267, 0, 37, 39, 40, 185]
LIPS_UPPER_INNER = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308]
LIPS_LOWER_INNER = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308]


def generate_mouth_open(src: Path, dst: Path, open_amount: float = 1.0):
    """口開き版を生成。上唇と下唇の間に歯の白いバンドを挿入し、下唇を少し下にずらす。

    open_amount: 口の開き具合（1.0 = 通常、1.5〜2.0 で大きめ）
    """
    img = cv2.imread(str(src))
    if img is None:
        sys.exit(f"画像読み込み失敗: {src}")
    h, w = img.shape[:2]

    mp_face = mp.solutions.face_mesh
    with mp_face.FaceMesh(static_image_mode=True, max_num_faces=1,
                           refine_landmarks=True, min_detection_confidence=0.3) as fm:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result = fm.process(rgb)
        if not result.multi_face_landmarks:
            sys.exit("顔が検出できませんでした")
        landmarks = result.multi_face_landmarks[0].landmark

    def pt(i):
        return np.array([landmarks[i].x * w, landmarks[i].y * h])

    # 口のランドマーク
    mouth_left = pt(61)
    mouth_right = pt(291)
    mouth_center = (mouth_left + mouth_right) / 2
    mouth_width = np.linalg.norm(mouth_right - mouth_left)
    upper_inner_bottom = pt(13)   # 上唇下端の中央
    lower_inner_top = pt(14)      # 下唇上端の中央

    # 下唇〜顎下領域を下にシフト（mediapipeの468点メッシュの顔下部を移動）
    # シンプル実装: 下唇と顎のバウンディングボックスを下にずらす
    shift_y = int(mouth_width * 0.06 * open_amount)

    # 上唇の底面Y座標
    upper_bottom_y = int(upper_inner_bottom[1])
    # 下顎の領域を特定するため、下唇のX範囲を取得
    x_min = int(mouth_left[0] - mouth_width * 0.15)
    x_max = int(mouth_right[0] + mouth_width * 0.15)
    x_min = max(0, x_min)
    x_max = min(w, x_max)

    # 下唇領域（y = upper_bottom_y + 2 から下唇までの範囲）を下にコピー＆シフト
    # これで歯の上に下唇が移動する形になる
    lower_region_top = upper_bottom_y + 2
    lower_region_bot = min(h, int(lower_inner_top[1]) + int(mouth_width * 0.25))

    if lower_region_bot > lower_region_top + 5:
        result = img.copy()
        # 下唇領域を下にshift_yだけずらす
        src_region = img[lower_region_top:lower_region_bot, x_min:x_max].copy()
        # ずらした先に貼り付け
        new_top = lower_region_top + shift_y
        new_bot = min(h, new_top + src_region.shape[0])
        paste_h = new_bot - new_top
        if paste_h > 0:
            # マスクで境界をソフトに
            mask = np.zeros((src_region.shape[0], src_region.shape[1]), dtype=np.uint8)
            cv2.ellipse(mask,
                        (src_region.shape[1]//2, src_region.shape[0]//2),
                        (int(src_region.shape[1]*0.45), int(src_region.shape[0]*0.55)),
                        0, 0, 360, 255, -1)
            mask = cv2.GaussianBlur(mask, (21, 21), 8)
            mask_3 = cv2.merge([mask, mask, mask]) / 255.0

            # 元の結果の該当領域に src_region を合成
            target = result[new_top:new_bot, x_min:x_max].astype(np.float32)
            overlay = src_region[:paste_h].astype(np.float32)
            target = target * (1 - mask_3[:paste_h]) + overlay * mask_3[:paste_h]
            result[new_top:new_bot, x_min:x_max] = target.astype(np.uint8)
        img = result

    # 歯の白いバンド: 上唇の直下〜下唇シフト分
    teeth_top = upper_bottom_y + 1
    teeth_bot = teeth_top + max(4, int(mouth_width * 0.08 * open_amount))
    teeth_cx = int(mouth_center[0])
    teeth_half_w = int(mouth_width * 0.28)

    teeth_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.ellipse(teeth_mask,
                (teeth_cx, (teeth_top + teeth_bot) // 2),
                (teeth_half_w, (teeth_bot - teeth_top) // 2),
                0, 0, 360, 255, -1)
    teeth_mask = cv2.GaussianBlur(teeth_mask, (5, 5), 1.5)

    # 歯の色: ほぼ白でややクリーム
    teeth_color = np.full_like(img, (230, 230, 235))  # BGR: 白系
    teeth_mask_3 = cv2.merge([teeth_mask, teeth_mask, teeth_mask]) / 255.0

    img_f = img.astype(np.float32)
    blended = img_f * (1 - teeth_mask_3 * 0.85) + teeth_color.astype(np.float32) * teeth_mask_3 * 0.85
    blended = blended.astype(np.uint8)

    # 歯の上に薄く影（上唇の影で歯の上端を自然に暗く）
    shadow_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.ellipse(shadow_mask,
                (teeth_cx, teeth_top),
                (teeth_half_w, max(2, (teeth_bot - teeth_top) // 3)),
                0, 180, 360, 255, -1)
    shadow_mask = cv2.GaussianBlur(shadow_mask, (5, 5), 2)
    shadow_mask_3 = cv2.merge([shadow_mask, shadow_mask, shadow_mask]) / 255.0
    shadow_color = np.full_like(img, (90, 80, 95))  # 薄暗いグレー
    blended = blended.astype(np.float32) * (1 - shadow_mask_3 * 0.4) + shadow_color.astype(np.float32) * shadow_mask_3 * 0.4
    blended = blended.astype(np.uint8)

    cv2.imwrite(str(dst), blended, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"✅ {dst.name} 生成完了")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="ソース画像パス（例: avatars/韓国語.jpeg）")
    parser.add_argument("--open", type=float, default=1.0, help="口の開き具合（1.0〜2.0）")
    args = parser.parse_args()

    src = Path(args.src)
    dst = src.with_name(f"{src.stem}_open{src.suffix}")
    generate_mouth_open(src, dst, open_amount=args.open)


if __name__ == "__main__":
    main()
