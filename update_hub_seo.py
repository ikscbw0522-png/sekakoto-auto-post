#!/usr/bin/env python3
"""ハブ記事7本のSEOタイトル・meta descriptionを一括更新（CTR改善）。

- SEOタイトル：短く・数字あり・ベネフィット明示（30文字目標）
- Meta description：100-120字、行動誘発型、具体数字含む
"""
import os
import sys
import time
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

WP_URL = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
AUTH = HTTPBasicAuth(WP_USER, WP_APP_PASSWORD)

# 改善案：ハブ記事7本のSEOメタ（2026-04-20 CTR対策）
HUB_SEO = {
    3299: {
        "title": "🌍海外旅行で使えるフレーズ10言語｜6シーン別・保存版",
        "description": "挨拶・ホテル・食事・買い物・交通・トラブルの6シーンで必須のフレーズを10言語で。発音付き・スクショで持ち歩ける保存版。出発前に必読。",
        "focus_kw": "海外旅行,外国語,フレーズ",
    },
    3318: {
        "title": "「ありがとう」を10言語で｜感謝・謝罪フレーズ完全版",
        "description": "「ありがとう」「ごめんなさい」を10言語で即使える。基本から丁寧まで、謝罪・感謝のシーン別完全ガイド。発音付き・保存してそのまま使える。",
        "focus_kw": "感謝,謝罪,外国語",
    },
    3321: {
        "title": "「愛してる」を10言語で｜告白・プロポーズ5シーン",
        "description": "「愛してる」「好きです」「会いたい」を10言語で。告白・プロポーズ・褒め言葉まで5シーン別フレーズ集。発音付きで海外の特別な人に気持ちを伝えよう。",
        "focus_kw": "愛してる,外国語,愛",
    },
    3324: {
        "title": "ビジネスで使える外国語10言語｜5シーン別・出張即戦力",
        "description": "挨拶・会議・謝罪・お礼・別れの5シーンで即使えるビジネスフレーズを10言語で。海外出張・国際会議で信頼を得るための発音付き完全ガイド。",
        "focus_kw": "ビジネス,外国語,フレーズ",
    },
    3326: {
        "title": "喜怒哀楽を10言語で｜外国語の感情表現フレーズ集",
        "description": "嬉しい・悲しい・楽しい・怒りなど感情表現を10言語でまとめた完全ガイド。発音付きで、海外の友達と深い会話ができるようになる実用フレーズ集。",
        "focus_kw": "感情,外国語,フレーズ",
    },
    3328: {
        "title": "食事で使える外国語10言語｜レストラン〜屋台まで",
        "description": "注文・味の感想・会計など食事シーンで使える外国語フレーズを10言語で。レストランから屋台まで、海外グルメを満喫するための発音付き完全ガイド。",
        "focus_kw": "食事,外国語,フレーズ",
    },
    3330: {
        "title": "自己紹介を10言語で｜初対面で盛り上がるフレーズ集",
        "description": "名前・出身・趣味・職業を10言語で自己紹介。初対面でぐっと距離が縮まるフレーズ集。発音付きで海外で新しい友達を作りたい人に最適。",
        "focus_kw": "自己紹介,外国語,フレーズ",
    },
}


def update_post_seo(post_id, seo):
    """WP REST API でメタデータを更新。"""
    resp = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
        json={
            "meta": {
                "rank_math_title": seo["title"],
                "rank_math_description": seo["description"],
                "rank_math_focus_keyword": seo["focus_kw"],
            }
        },
        auth=AUTH,
        timeout=30,
    )
    return resp


def main():
    print("🔧 ハブ記事7本のSEO一括更新 (CTR改善)\n")
    successes = 0
    for pid, seo in HUB_SEO.items():
        print(f"━━━ ID{pid} ━━━")
        print(f"  title : {seo['title']} ({len(seo['title'])}文字)")
        print(f"  desc  : {seo['description'][:60]}... ({len(seo['description'])}文字)")
        try:
            r = update_post_seo(pid, seo)
            if r.status_code == 200:
                # 反映確認
                data = r.json()
                m = data.get("meta", {})
                title_set = m.get("rank_math_title", "")
                if title_set == seo["title"]:
                    print(f"  ✅ 更新成功")
                    successes += 1
                else:
                    print(f"  ⚠️  200返ったが反映確認NG: got '{title_set[:40]}'")
            else:
                print(f"  ❌ {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  ❌ {e}")
        time.sleep(1)  # rate limit
        print()

    print(f"━━━ 完了: {successes}/{len(HUB_SEO)}本成功 ━━━")


if __name__ == "__main__":
    main()
