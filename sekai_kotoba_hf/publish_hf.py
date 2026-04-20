#!/usr/bin/env python3
"""Hyperframes動画 → IG再エンコード → WPアップロード → IG投稿 の一気通貫スクリプト。

Usage:
    python3 publish_hf.py --mp4 ohayou_8lang_v4c.mp4 --theme おはよう --caption-file ../captions/おはよう_hf.txt
    python3 publish_hf.py --mp4 output/いくらですか.mp4 --theme いくらですか

前提:
    - ../.env に WP_URL, WP_USER, WP_APP_PASSWORD, IG_USER_ID, IG_ACCESS_TOKEN
    - reencode_for_ig.py が同ディレクトリ
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
ROOT = HERE.parent
ENV_PATH = ROOT / ".env"
CAPTIONS_DIR = ROOT / "captions"
URL_JSON = HERE / "hyperframes_reel_urls.json"


def load_env():
    """環境変数を優先、.envがあれば補完（GitHub Actions でも動くように）。"""
    import os
    env = dict(os.environ)  # 環境変数を優先
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
    return env


def reencode(src: Path, dst: Path) -> None:
    """IG仕様に再エンコード。"""
    from reencode_for_ig import reencode_for_ig
    reencode_for_ig(src, dst)


def ascii_name(theme: str, ext: str = ".mp4") -> str:
    """WP/HTTPヘッダーで扱えるASCII名を生成（theme名は日本語のためタイムスタンプ＋ハッシュ）。"""
    import hashlib
    h = hashlib.md5(theme.encode()).hexdigest()[:8]
    return f"hf_{int(time.time())}_{h}{ext}"


def upload_to_wp(path: Path, ascii_fn: str, env: dict) -> str:
    url = f"{env['WP_URL']}/wp-json/wp/v2/media"
    auth_b64 = base64.b64encode(f"{env['WP_USER']}:{env['WP_APP_PASSWORD']}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Disposition": f'attachment; filename="{ascii_fn}"',
        "Content-Type": "video/mp4",
    }
    print(f"  → POST {url}")
    print(f"  → filename={ascii_fn}, size={path.stat().st_size/1024/1024:.1f}MB")
    with open(path, "rb") as f:
        r = requests.post(url, headers=headers, data=f.read(), timeout=300)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"WP upload failed {r.status_code}: {r.text[:300]}")
    return r.json()["source_url"]


def create_reel_container(video_url: str, caption: str, env: dict, thumb_offset_ms: int = 2000) -> str:
    """Reelsコンテナ作成。thumb_offset_msでサムネイル用フレーム位置を指定（フック完成後の2秒目）。"""
    url = f"https://graph.instagram.com/v21.0/{env['IG_USER_ID']}/media"
    params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "thumb_offset": str(thumb_offset_ms),  # ms単位、フック完成フレームをサムネに
        "access_token": env["IG_ACCESS_TOKEN"],
    }
    r = requests.post(url, params=params, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"IG container creation failed {r.status_code}: {r.text[:300]}")
    return r.json()["id"]


def wait_for_processing(container_id: str, env: dict, timeout: int = 300) -> bool:
    url = f"https://graph.instagram.com/v21.0/{container_id}"
    params = {"fields": "status_code", "access_token": env["IG_ACCESS_TOKEN"]}
    start = time.time()
    error_streak = 0
    ERROR_THRESHOLD = 5
    while time.time() - start < timeout:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            status = r.json().get("status_code", "")
            elapsed = int(time.time() - start)
            print(f"  [{elapsed}s] status={status}")
            if status == "FINISHED":
                return True
            if status == "ERROR":
                error_streak += 1
                if error_streak >= ERROR_THRESHOLD:
                    print(f"  連続{ERROR_THRESHOLD}回ERROR: {r.text[:200]}")
                    return False
            else:
                error_streak = 0
        time.sleep(5)
    return False


def publish_reel(container_id: str, env: dict) -> str:
    url = f"https://graph.instagram.com/v21.0/{env['IG_USER_ID']}/media_publish"
    params = {"creation_id": container_id, "access_token": env["IG_ACCESS_TOKEN"]}
    r = requests.post(url, params=params, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"IG publish failed {r.status_code}: {r.text[:300]}")
    return r.json()["id"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mp4", type=Path, required=True, help="Hyperframes raw MP4")
    p.add_argument("--theme", required=True, help="テーマ名")
    p.add_argument("--caption-file", type=Path, help="キャプションtxt（省略時 captions/{theme}_hf.txt or {theme}.txt）")
    p.add_argument("--skip-upload", action="store_true", help="既存URL使用（hyperframes_reel_urls.json に --themeがある前提）")
    p.add_argument("--skip-reencode", action="store_true", help="IG再エンコード済のMP4を直接アップロード（render_theme.py の --no-reencodeなし出力など）")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    env = load_env()

    mp4 = args.mp4 if args.mp4.is_absolute() else (HERE / args.mp4)
    if not mp4.exists():
        # try as relative to cwd
        mp4 = Path(args.mp4).resolve()
    if not mp4.exists():
        sys.exit(f"MP4なし: {args.mp4}")

    # キャプション読み込み
    if args.caption_file:
        cap_path = args.caption_file
    else:
        for cand in [CAPTIONS_DIR / f"{args.theme}_hf.txt", CAPTIONS_DIR / f"{args.theme}.txt"]:
            if cand.exists():
                cap_path = cand
                break
        else:
            sys.exit(f"キャプション見つからない: captions/{args.theme}_hf.txt or {args.theme}.txt")
    caption = cap_path.read_text(encoding="utf-8").strip()
    print(f"📝 caption: {cap_path.name} ({len(caption)}文字)")

    # URL解決（skip-upload または 新規アップロード）
    urls = json.loads(URL_JSON.read_text(encoding="utf-8")) if URL_JSON.exists() else {}
    if args.skip_upload:
        if args.theme not in urls:
            sys.exit(f"{URL_JSON.name} に {args.theme} のURLなし")
        video_url = urls[args.theme]
        print(f"🔗 existing URL: {video_url}")
    else:
        # IG再エンコード（skip-reencode時はそのまま使う）
        if args.skip_reencode:
            print(f"🎞️  IG再エンコードスキップ: {mp4.name} を直接アップロード")
            ig_mp4 = mp4
        else:
            ig_mp4 = mp4.with_stem(mp4.stem + "_ig")
            if not ig_mp4.exists():
                print(f"🎞️  IG再エンコード: {mp4.name} → {ig_mp4.name}")
                reencode(mp4, ig_mp4)
                print(f"  ✅ {ig_mp4.stat().st_size/1024/1024:.1f}MB")
            else:
                print(f"🎞️  IG再エンコード済: {ig_mp4.name}")

        # WPアップロード
        print("⬆️  WPアップロード中...")
        fn = ascii_name(args.theme)
        video_url = upload_to_wp(ig_mp4, fn, env)
        print(f"  ✅ {video_url}")

        # URLを保存
        urls[args.theme] = video_url
        URL_JSON.write_text(json.dumps(urls, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  🗂️  {URL_JSON.name} 更新")

    if args.dry_run:
        print(f"\n[dry-run] video_url={video_url}")
        print(f"\nキャプションプレビュー:\n{caption[:500]}...")
        return

    # IG投稿
    print("\n📱 [1/3] Reelコンテナ作成中...")
    cid = create_reel_container(video_url, caption, env)
    print(f"  container: {cid}")

    print("\n📱 [2/3] エンコード待機中...")
    if not wait_for_processing(cid, env):
        sys.exit("❌ IGエンコード失敗またはタイムアウト")

    print("\n📱 [3/3] 公開中...")
    media_id = publish_reel(cid, env)
    print(f"  投稿ID: {media_id}")

    # ログ
    log_path = ROOT / "reel_posted.log"
    log_line = f"{time.strftime('%Y-%m-%d %H:%M')} {args.theme} ({media_id}) [hyperframes]\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_line)

    print(f"\n✅ Hyperframes Reel投稿完了！ (log: {log_path.name})")


if __name__ == "__main__":
    main()
