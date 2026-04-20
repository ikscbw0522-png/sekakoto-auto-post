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
REEL_LOG = BASE / "reel_posted.log"

# フォーマット識別タグ（reel_posted.log の末尾 []）
FORMAT_TAGS = ["hyperframes", "voice", "convo"]


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


def load_format_map():
    """reel_posted.log から media_id → format (hyperframes/voice/convo/normal) のマップを構築。"""
    import re
    mapping = {}
    if not REEL_LOG.exists():
        return mapping
    # 例: 2026-04-20 13:55 おはよう (18086233694525406) [hyperframes]
    pat = re.compile(r"\((\d+)\)(?:\s+\[([^\]]+)\])?")
    for line in REEL_LOG.read_text(encoding="utf-8").splitlines():
        m = pat.search(line)
        if m:
            mid = m.group(1)
            tag = m.group(2) if m.group(2) in FORMAT_TAGS else "normal"
            mapping[mid] = tag
    return mapping


def by_format_stats(posts_with_insights):
    """フォーマット別に集計した統計を返す。"""
    from collections import defaultdict
    stats = defaultdict(lambda: {"count": 0, "reach": 0, "saved": 0, "shares": 0,
                                  "interactions": 0, "themes": []})
    for p in posts_with_insights:
        fmt = p.get("format", "unknown")
        ins = p["insights"]
        theme = extract_theme(p.get("caption", ""))
        stats[fmt]["count"] += 1
        stats[fmt]["reach"] += ins.get("reach", 0)
        stats[fmt]["saved"] += ins.get("saved", 0)
        stats[fmt]["shares"] += ins.get("shares", 0)
        stats[fmt]["interactions"] += ins.get("total_interactions", 0)
        stats[fmt]["themes"].append((theme, ins.get("reach", 0), ins.get("saved", 0)))
    return dict(stats)


def generate_report(posts_with_insights):
    """分析レポートを生成。"""
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append(f"📊 Instagram Insights レポート ({now})")
    lines.append(f"{'='*40}")
    lines.append(f"総投稿数: {len(posts_with_insights)}")

    # === フォーマット別サマリー ===
    fmt_stats = by_format_stats(posts_with_insights)
    if fmt_stats:
        lines.append("")
        lines.append("🎬 フォーマット別サマリー:")
        # 順番: hyperframes > voice > convo > normal > unknown
        order = ["hyperframes", "voice", "convo", "normal", "unknown"]
        for fmt in order:
            if fmt not in fmt_stats:
                continue
            s = fmt_stats[fmt]
            avg_reach = s["reach"] / s["count"] if s["count"] else 0
            save_rate = s["saved"] / max(1, s["reach"]) * 100
            lines.append(f"  [{fmt:11s}] n={s['count']:2d} / reach合計={s['reach']:4d} / "
                         f"平均reach={avg_reach:5.1f} / 保存={s['saved']} ({save_rate:.1f}%) / "
                         f"シェア={s['shares']}")
        # 各フォーマットの代表投稿（reach TOP2）
        lines.append("")
        lines.append("🏁 フォーマット別 reach TOP2:")
        for fmt in order:
            if fmt not in fmt_stats:
                continue
            themes = sorted(fmt_stats[fmt]["themes"], key=lambda t: t[1], reverse=True)[:2]
            if not themes:
                continue
            lines.append(f"  [{fmt}]")
            for theme, reach, saved in themes:
                lines.append(f"      「{theme}」 reach={reach} saved={saved}")

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


def compare_hyperframes_report(posts_with_insights):
    """Hyperframes vs voice/convo/normal の詳細比較レポート（投稿24h経過分のみ）。"""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    # 24h以上経過した投稿だけを対象に
    import re as _re
    mature = []
    for p in posts_with_insights:
        ts = p.get("timestamp", "")
        if not ts:
            continue
        # IGは "2026-04-15T14:58:12+0000" 形式を返す。Python 3.9 fromisoformat は +00:00 が必要
        ts_norm = _re.sub(r"([+-])(\d{2})(\d{2})$", r"\1\2:\3", ts.replace("Z", "+00:00"))
        try:
            post_dt = datetime.fromisoformat(ts_norm)
            if post_dt < cutoff:
                mature.append(p)
        except ValueError:
            continue

    lines = []
    lines.append("")
    lines.append("=" * 50)
    lines.append("🏁 Hyperframes A/B比較レポート（投稿24h経過分のみ）")
    lines.append("=" * 50)
    lines.append(f"対象期間: 24h以上前の投稿のみ（n={len(mature)}）")

    fmt_stats = by_format_stats(mature)
    if not fmt_stats:
        lines.append("⚠️ 比較対象データなし")
        return "\n".join(lines)

    # 各フォーマットの平均
    lines.append("")
    lines.append(f"{'フォーマット':15s} {'n':>3} {'平均reach':>12} {'平均保存':>10} {'保存率':>8} {'平均シェア':>10}")
    lines.append("-" * 70)
    fmt_avg = {}
    for fmt in ["hyperframes", "voice", "convo", "normal"]:
        if fmt not in fmt_stats:
            continue
        s = fmt_stats[fmt]
        n = s["count"]
        avg_reach = s["reach"] / n if n else 0
        avg_saved = s["saved"] / n if n else 0
        save_rate = s["saved"] / max(1, s["reach"]) * 100
        avg_shares = s["shares"] / n if n else 0
        fmt_avg[fmt] = {"n": n, "reach": avg_reach, "saved": avg_saved, "save_rate": save_rate, "shares": avg_shares}
        lines.append(f"{fmt:15s} {n:>3} {avg_reach:>12.1f} {avg_saved:>10.2f} {save_rate:>7.2f}% {avg_shares:>10.2f}")

    # 判定
    lines.append("")
    lines.append("【判定】")
    if "hyperframes" not in fmt_avg:
        lines.append("⚠️ Hyperframesデータなし（24h以上経過の投稿が0本）")
    else:
        hf = fmt_avg["hyperframes"]
        # 比較対象として voice/convo/normal のうち最大の平均reach
        baseline_names = [k for k in ["voice", "convo", "normal"] if k in fmt_avg]
        if not baseline_names:
            lines.append("⚠️ 比較対象（voice/convo/normal）データなし")
        else:
            best_baseline = max(baseline_names, key=lambda k: fmt_avg[k]["reach"])
            bl = fmt_avg[best_baseline]
            reach_ratio = hf["reach"] / max(1, bl["reach"])
            lines.append(f"  Hyperframes平均reach: {hf['reach']:.1f} (n={hf['n']})")
            lines.append(f"  比較基準 [{best_baseline}] 平均reach: {bl['reach']:.1f} (n={bl['n']})")
            lines.append(f"  比率: {reach_ratio:.2f}x")
            if hf["n"] < 3:
                lines.append("  ⚠️ サンプル少なすぎ（Hyperframes n<3）— 判断保留推奨")
            elif reach_ratio >= 1.0:
                lines.append(f"  ✅ Hyperframes優勢 → P4（195本一括）推奨")
            elif reach_ratio >= 0.8:
                lines.append(f"  🟡 ほぼ同等 → 保存率・シェアも確認、差があれば採用")
            else:
                lines.append(f"  ❌ Hyperframes劣勢 → フック/CTA再調整 or ロールバック検討")

            # 保存率も比較
            if hf["save_rate"] > 0 and bl["save_rate"] > 0:
                save_ratio = hf["save_rate"] / bl["save_rate"]
                lines.append(f"  保存率比: {save_ratio:.2f}x (Hyperframes {hf['save_rate']:.1f}% vs {bl['save_rate']:.1f}%)")
            elif hf["save_rate"] > 0:
                lines.append(f"  Hyperframesのみ保存発生: {hf['save_rate']:.1f}%")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--discord", help="Discord Webhook URL")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    parser.add_argument("--compare-hyperframes", action="store_true",
                        help="Hyperframes vs voice/convo の詳細比較レポートを追加出力")
    args = parser.parse_args()

    env = load_env()
    print("投稿データ取得中...")
    posts = get_all_media(env)
    print(f"  {len(posts)}件取得")

    print("Insights取得中...")
    fmt_map = load_format_map()  # media_id → hyperframes/voice/convo/normal
    posts_with_insights = []
    for i, p in enumerate(posts, 1):
        ins = get_insights(p["id"], env)
        p["insights"] = ins
        p["format"] = fmt_map.get(p["id"], "unknown")
        posts_with_insights.append(p)
        if i % 10 == 0:
            print(f"  {i}/{len(posts)}")
        time.sleep(0.3)

    if args.json:
        print(json.dumps(posts_with_insights, ensure_ascii=False, indent=2))
        return

    report = generate_report(posts_with_insights)
    print("\n" + report)

    # Hyperframes比較レポート（--compare-hyperframes指定時）
    if args.compare_hyperframes:
        compare = compare_hyperframes_report(posts_with_insights)
        print(compare)
        report = report + "\n" + compare

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
