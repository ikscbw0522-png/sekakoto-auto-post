#!/usr/bin/env python3
"""Hyperframes レンダ出力を Instagram Reels 仕様に再エンコード。

既存 generate_voice_reel.py の _reencode_for_ig() を流用。

Usage:
    python3 reencode_for_ig.py <input.mp4> [--out <output.mp4>]
    python3 reencode_for_ig.py ohayou_8lang_v4.mp4
    python3 reencode_for_ig.py ohayou_8lang_v4.mp4 --out ohayou_8lang_v4_ig.mp4
"""
import argparse
import subprocess
import sys
from pathlib import Path


def reencode_for_ig(src: Path, dst: Path) -> None:
    """IG Reels 仕様: H.264 High / yuv420p / 30fps / AAC 48kHz 192k / faststart."""
    # Prefer ~/.local/bin/ffmpeg (static_ffmpeg v8) then imageio_ffmpeg fallback
    ff = None
    for cand in [Path.home() / ".local/bin/ffmpeg", Path("/usr/local/bin/ffmpeg")]:
        if cand.exists():
            ff = str(cand)
            break
    if ff is None:
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
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path, help="Hyperframes 出力 MP4")
    p.add_argument("--out", type=Path, help="出力パス（省略時は入力+_ig.mp4）")
    args = p.parse_args()

    src = args.input
    if not src.exists():
        sys.exit(f"入力なし: {src}")
    dst = args.out or src.with_stem(src.stem + "_ig")

    print(f"Re-encoding for IG: {src.name} → {dst.name}")
    reencode_for_ig(src, dst)
    size_mb = dst.stat().st_size / 1024 / 1024
    print(f"✅ {dst.name} ({size_mb:.1f}MB)")


if __name__ == "__main__":
    main()
