#!/usr/bin/env python3
"""Instagram Insights分析レポート生成。

全投稿のリーチ・保存・シェア・インタラクションを取得し、
テーマ別・日付別のパフォーマンスを分析してレポート出力。

使用例:
    python3 ig_insights_report.py
    python3 ig_insights_report.py --discord WEBHOOK_URL
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

BASE = Path(__file__).parent
ENV_PATH = BASE / ".env"


def load_env():
    env = {k: os.environ[k] for k in ["IG_USER_ID", "IG_ACCESS_TOKEN"] if k in os.environ}
    if not all(k in env for k in ["IG_USER_ID", "IG_ACCESS_TOKEN"]) and ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
    return env


def get_all_media(env):
    """全投稿を取得。"""
    posts = []
    url = f"https://graph.instagram.com/v21.0/{env['IG_USER_ID']}/media"
    params = {
        "fields": "id,media_type,caption,timestamp,like_count,comments_count,permalink",
        "limit": 50,
        "access_token": env["IG_ACCESS_TOKEN"],
    }
    while url:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            print(f"Error fetching media: {r.status_code}", file=sys.stderr)
            break
        data = r.json()
        posts.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}  # next URL already has params
        time.sleep(0.3)
    return posts


def get_insights(media_id, env):
    """投稿のInsightsを取得。"""
    metrics = "reach,saved,shares,total_interactions"
    r = requests.get(
        f"https://graph.instagram.com/v21.0/{media_id}/insights",
        params={"metric": metrics, "access_token": env["IG_ACCESS_TOKEN"]},
        timeout=30,
    )
    if r.status_code != 200:
        return {}
    result = {}
    for m in r.json().get("data", []):
        result[m["name"]] = m["values"][0]["value"]
    return result


def extract_theme(caption):
    """キャプションからテーマを抽出（「〇〇」は8言語で…）"""
    if not caption:
        return "不明"
    import re
    m = re.search(r"「(.+?)」", caption)
    return m.group(1) if m else caption[:20].replace("\n", " ")


def generate_report(posts_with_insights):
    """分析レポートを生成。"""
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append(f"📊 Instagram Insights レポート ({now})")
    lines.append(f"{'='*40}")
    lines.append(f"総投稿数: {len(posts_with_insights)}")

    total_reach = sum(p["insights"].get("reach", 0) for p in posts_with_insights)
    total_saved = sum(p["insights"].get("saved", 0) for p in posts_with_insights)
    total_shares = sum(p["insights"].get("shares", 0) for p in posts_with_insights)
    total_interactions = sum(p["insights"].get("total_interactions", 0) for p in posts_with_insights)

    lines.append(f"総リーチ: {total_reach}")
    lines.append(f"総保存: {total_saved}")
    lines.append(f"総シェア: {total_shares}")
    lines.append(f"総インタラクション: {total_interactions}")
    lines.append("")

    # テーマ別ランキング（リーチ順）
    sorted_posts = sorted(posts_with_insights, key=lambda p: p["insights"].get("reach", 0), reverse=True)

    lines.append("🏆 リーチ TOP5:")
    for i, p in enumerate(sorted_posts[:5], 1):
        theme = extract_theme(p.get("caption", ""))
        ins = p["insights"]
        ts = p.get("timestamp", "")[:10]
        lines.append(f"  {i}. 「{theme}」 reach={ins.get('reach',0)} saved={ins.get('saved',0)} shares={ins.get('shares',0)} ({ts})")

    lines.append("")
    lines.append("📉 リーチ WORST5:")
    for i, p in enumerate(sorted_posts[-5:], 1):
        theme = extract_theme(p.get("caption", ""))
        ins = p["insights"]
        ts = p.get("timestamp", "")[:10]
        lines.append(f"  {i}. 「{theme}」 reach={ins.get('reach',0)} saved={ins.get('saved',0)} ({ts})")

    # 保存率（saved/reach）
    lines.append("")
    lines.append("💾 保存率 TOP5（保存/リーチ）:")
    for_save = [p for p in posts_with_insights if p["insights"].get("reach", 0) > 0]
    for_save.sort(key=lambda p: p["insights"].get("saved", 0) / max(1, p["insights"].get("reach", 1)), reverse=True)
    for i, p in enumerate(for_save[:5], 1):
        theme = extract_theme(p.get("caption", ""))
        ins = p["insights"]
        rate = ins.get("saved", 0) / max(1, ins.get("reach", 1)) * 100
        lines.append(f"  {i}. 「{theme}」 {rate:.1f}% (saved={ins.get('saved',0)}/reach={ins.get('reach',0)})")

    # 改善提案
    lines.append("")
    lines.append("💡 改善提案:")
    if total_reach < 100:
        lines.append("  - リーチが少ない。ハッシュタグの見直しと投稿時間の最適化を推奨")
        lines.append("  - 同ジャンルアカウントへのコメント交流を毎日10件以上")
    if total_saved == 0:
        lines.append("  - 保存が0。CTAで「保存して旅行前にチェック」を強化")
        lines.append("  - Reel内に「保存しておこう」のテキストを追加")
    if total_shares == 0:
        lines.append("  - シェアが0。友達に送りたくなるクイズ形式のフックを検討")
    top_theme = extract_theme(sorted_posts[0].get("caption", "")) if sorted_posts else "不明"
    lines.append(f"  - 最もリーチの高いテーマ「{top_theme}」に類似したテーマの投稿頻度を上げる")

    return "\n".join(lines)


def send_discord(webhook_url, message):
    """Discordにレポートを送信。"""
    # Discord max 2000 chars per message
    chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
    for chunk in chunks:
        r = requests.post(webhook_url, json={"content": f"```\n{chunk}\n```"}, timeout=30)
        if r.status_code not in (200, 204):
            print(f"Discord送信エラー: {r.status_code}", file=sys.stderr)
        time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--discord", help="Discord Webhook URL")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    args = parser.parse_args()

    env = load_env()
    print("投稿データ取得中...")
    posts = get_all_media(env)
    print(f"  {len(posts)}件取得")

    print("Insights取得中...")
    posts_with_insights = []
    for i, p in enumerate(posts, 1):
        ins = get_insights(p["id"], env)
        p["insights"] = ins
        posts_with_insights.append(p)
        if i % 10 == 0:
            print(f"  {i}/{len(posts)}")
        time.sleep(0.3)

    if args.json:
        print(json.dumps(posts_with_insights, ensure_ascii=False, indent=2))
        return

    report = generate_report(posts_with_insights)
    print("\n" + report)

    # レポートをファイルに保存
    report_path = BASE / "insights_report.txt"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n📄 レポート保存: {report_path}")

    if args.discord:
        print("Discord送信中...")
        send_discord(args.discord, report)
        print("✅ Discord送信完了")


if __name__ == "__main__":
    main()
