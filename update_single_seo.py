#!/usr/bin/env python3
"""シングル記事198本のSEOタイトル・meta descriptionを一括更新（CTR改善）。

現状: 36-47字の長すぎるタイトル（SERPで省略）＋言語名羅列のdesc。
改善: カテゴリ別テンプレで短く（24-32字）＋行動誘発型desc（70-100字）。
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

# ハブ記事は別対応済みなのでスキップ
HUB_IDS = {3299, 3318, 3321, 3324, 3326, 3328, 3330}

# カテゴリ分類ルール（優先度順：より具体的なカテゴリを先に）
TIER_RULES = [
    # 緊急 > 最優先
    (20, "緊急・トラブル", ["助けて", "病院", "救急", "警察", "火事", "危な", "盗まれ", "なくし", "パスポート", "財布", "迷い", "薬局", "アレルギー", "大使館", "痛い", "気分が悪い", "やめて"]),
    (10, "お金・決済", ["いくら", "予算", "お会計", "現金", "クレジット", "レシート", "両替", "安く", "免税", "返品", "セール"]),
    # 食事を買物より先に（「辛くしないでください」を食事扱いに）
    (50, "食事", ["おいしい", "美味", "まずい", "お腹", "乾杯", "水を", "ビール", "いただき", "ごちそう", "辛い", "甘い", "辛くしない", "少なめ", "おかわり", "ベジタリアン"]),
    (80, "恋愛", ["愛してる", "大好き", "好きです", "会いたい", "また会い", "付き合", "結婚", "運命", "一目惚れ", "ずっと", "信じてる", "あなたが"]),
    (85, "お祝い・励まし", ["おめでとう", "誕生日", "頑張", "気をつけて", "大丈夫", "心配しないで", "気にしないで"]),
    (30, "交通・場所", ["トイレ", "駅", "空港", "ホテル", "タクシー", "電車", "切符", "地図", "ここは", "どのくらい", "まっすぐ", "右に", "左に", "近くに", "コンビニ", "WiFi", "観光地"]),
    # 会話補助：英語・日本語・ゆっくり系
    (60, "会話補助", ["日本から", "日本語", "英語話", "英語は話", "ゆっくり", "もう一度", "わかりません", "了解", "問題ありません", "確認", "検討", "ようこそ"]),
    # 仕事・自己紹介：「連絡先」「資料」等を買物より先に
    (100, "自己紹介・仕事", ["名前", "名刺", "連絡先", "LINE", "友達", "一緒に遊", "一緒に写真", "写真を撮", "初めて", "住んでいる", "会社員", "学生", "趣味", "仕事", "家族", "何人", "何歳", "来ました", "会議", "契約", "担当", "資料", "ご連絡", "ご提案", "締め切り", "お忙しい", "おかげさま"]),
    (90, "感情表現", ["嬉しい", "楽しい", "寂しい", "悲しい", "怒って", "疲れた", "幸せ", "びっくり", "最高", "かわいい", "かっこいい", "素敵"]),
    (70, "感謝・感情", ["ありがとう", "感謝", "助かり", "お気遣い", "光栄", "お世話", "恐れ入", "とんでもない", "どういたし"]),
    # 買物・注文：一般的な「ください」等はここで（他のより具体的なカテゴリが先にマッチ）
    (40, "注文・買物", ["注文", "メニュー", "おすすめ", "持ち帰り", "試着", "サイズ", "他の色", "見ているだけ", "プレゼント包装", "袋", "これと同じ", "どこで買える", "いつ届く", "荷物", "予約", "チェックイン", "チェックアウト", "禁煙", "ください"]),
    # 汎用「どこ」は最後
    (30, "交通・場所（汎用）", ["どこ"]),
    (120, "日常挨拶", ["おはよう", "おやすみ", "こんにちは", "こんばんは", "さようなら", "はじめまして", "すみません", "お疲れ様", "お元気", "おかえり", "ただいま", "いってきます", "いってらっしゃい", "久しぶり", "また会いましょう", "よろしく", "お邪魔", "お先に", "お手数", "かしこまり", "少々お待ち", "申し訳", "お会いできて", "ごめん", "ごめんね"]),
]

# カテゴリ別 SEO テンプレート
SEO_TEMPLATES = {
    10: {
        "title": "「{theme}」を10言語で｜海外の支払いで使えるフレーズ",
        "desc": "「{theme}」を10言語で即使える。海外ショッピング・レストラン・タクシーの支払い場面で通じる発音カタカナ付きフレーズ集。スクショで保存推奨。",
        "focus_kw": "{theme},外国語,支払い",
    },
    20: {
        "title": "「{theme}」を10言語で｜緊急時に身を守るフレーズ",
        "desc": "海外トラブル時「{theme}」を10言語で言える。病院・警察・盗難など緊急場面で命を守る発音付きフレーズ。旅行前にスマホ保存必須。",
        "focus_kw": "{theme},外国語,緊急",
    },
    30: {
        "title": "「{theme}」を10言語で｜海外で迷わない移動フレーズ",
        "desc": "「{theme}」を10言語で。タクシー・電車・道案内など海外の移動で困らない発音付きフレーズ集。スクショで旅先で即使える。",
        "focus_kw": "{theme},外国語,旅行",
    },
    40: {
        "title": "「{theme}」を10言語で｜買物・注文で使えるフレーズ",
        "desc": "海外の買物・注文で「{theme}」を10言語で即使える。レストラン・ショップで通じる発音付きフレーズ集。旅行前に保存推奨。",
        "focus_kw": "{theme},外国語,買物",
    },
    50: {
        "title": "「{theme}」を10言語で｜海外グルメで使えるフレーズ",
        "desc": "海外で「{theme}」を10言語で言える。レストラン・屋台・カフェなど食事シーンで通じる発音カタカナ付きフレーズ集。",
        "focus_kw": "{theme},外国語,食事",
    },
    60: {
        "title": "「{theme}」を10言語で｜会話に困った時に使える",
        "desc": "「{theme}」を10言語で。言葉が出ない時に使える発音付きフレーズ集。海外旅行・国際交流で必須の実用表現。",
        "focus_kw": "{theme},外国語,会話",
    },
    70: {
        "title": "「{theme}」を10言語で｜気持ちを伝える表現集",
        "desc": "「{theme}」を10言語で。感謝・感動など気持ちを現地の言葉で伝えるフレーズ集。発音カタカナ付きで海外で心が通じる。",
        "focus_kw": "{theme},外国語,感謝",
    },
    80: {
        "title": "「{theme}」を10言語で｜海外の恋・愛の言葉",
        "desc": "「{theme}」を10言語で。海外の特別な人に気持ちを伝えるフレーズ集。発音付きで世界中どこでも使える愛の言葉。",
        "focus_kw": "{theme},外国語,愛",
    },
    85: {
        "title": "「{theme}」を10言語で｜祝福・励ましフレーズ",
        "desc": "「{theme}」を10言語で。海外の友人・家族を祝う・励ますフレーズ集。発音カタカナ付きで心が伝わる実用表現。",
        "focus_kw": "{theme},外国語,励まし",
    },
    90: {
        "title": "「{theme}」を10言語で｜感情を伝える表現",
        "desc": "「{theme}」を10言語で。海外で感情を素直に伝えるフレーズ集。発音カタカナ付き・文化背景解説付きの実用ガイド。",
        "focus_kw": "{theme},外国語,感情",
    },
    100: {
        "title": "「{theme}」を10言語で｜自己紹介・ビジネス表現",
        "desc": "「{theme}」を10言語で。海外の自己紹介・ビジネスシーンで使えるフレーズ集。発音カタカナ付きで信頼を得る実用表現。",
        "focus_kw": "{theme},外国語,ビジネス",
    },
    120: {
        "title": "「{theme}」を10言語で｜挨拶の発音＆使い方",
        "desc": "「{theme}」を韓国語・中国語・タイ語など10言語で。発音カタカナ付き・文化背景も解説。海外旅行・国際交流で使える実用ガイド。",
        "focus_kw": "{theme},外国語,挨拶",
    },
    200: {  # その他
        "title": "「{theme}」を10言語で｜発音＆使い方ガイド",
        "desc": "「{theme}」を10言語で。発音カタカナ付き・使い方解説の実用フレーズ集。海外旅行・国際交流で使える。",
        "focus_kw": "{theme},外国語,フレーズ",
    },
}


def categorize(theme: str) -> int:
    for tier, name, keywords in TIER_RULES:
        for kw in keywords:
            if kw in theme:
                return tier
    return 200


def extract_theme_from_title(title_rendered: str) -> str:
    """「{theme}」は外国語で何て言う？... からテーマ抽出。"""
    import re
    m = re.search(r"「(.+?)」", title_rendered)
    return m.group(1) if m else title_rendered[:15]


def generate_seo(theme: str) -> dict:
    tier = categorize(theme)
    tpl = SEO_TEMPLATES[tier]
    return {
        "title": tpl["title"].format(theme=theme),
        "desc": tpl["desc"].format(theme=theme),
        "focus_kw": tpl["focus_kw"].format(theme=theme),
        "tier": tier,
    }


def fetch_all_singles():
    singles = []
    page = 1
    while True:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts?per_page=100&page={page}&_fields=id,title,slug",
            timeout=30,
        )
        if r.status_code != 200:
            break
        posts = r.json()
        if not posts:
            break
        singles.extend([p for p in posts if p["id"] not in HUB_IDS])
        page += 1
        if page > 5:
            break
    return singles


def update_post(post_id, seo):
    resp = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
        json={
            "meta": {
                "rank_math_title": seo["title"],
                "rank_math_description": seo["desc"],
                "rank_math_focus_keyword": seo["focus_kw"],
            }
        },
        auth=AUTH,
        timeout=30,
    )
    return resp


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="更新せず生成結果のみ表示")
    p.add_argument("--limit", type=int, help="先頭N件だけ処理（テスト用）")
    args = p.parse_args()

    print("📥 全シングル記事取得中...")
    singles = fetch_all_singles()
    print(f"  {len(singles)}本\n")

    if args.limit:
        singles = singles[:args.limit]

    ok = 0
    fail = 0
    from collections import Counter
    tier_count = Counter()

    for i, post in enumerate(singles, 1):
        theme = extract_theme_from_title(post["title"]["rendered"])
        seo = generate_seo(theme)
        tier_count[seo["tier"]] += 1

        if args.dry_run:
            if i <= 15 or i % 50 == 0:
                print(f"[{i:3d}] ID{post['id']} tier{seo['tier']:3d} {theme}")
                print(f"       title: {seo['title']} ({len(seo['title'])}字)")
                print(f"       desc : {seo['desc'][:60]}... ({len(seo['desc'])}字)")
            continue

        try:
            r = update_post(post["id"], seo)
            if r.status_code == 200:
                ok += 1
                if i % 20 == 0:
                    print(f"[{i:3d}/{len(singles)}] ✅ ID{post['id']} {theme}")
            else:
                fail += 1
                print(f"[{i:3d}] ❌ ID{post['id']} {theme}: {r.status_code}")
        except Exception as e:
            fail += 1
            print(f"[{i:3d}] ❌ ID{post['id']} {theme}: {e}")
        time.sleep(0.3)

    print(f"\n━━━ 完了: {ok}成功 / {fail}失敗 / {len(singles)}中 ━━━")
    print(f"カテゴリ分布:")
    for tier in sorted(tier_count):
        label = next((n for t, n, _ in TIER_RULES if t == tier), "未分類")
        print(f"  tier{tier:3d} ({label}): {tier_count[tier]}本")


if __name__ == "__main__":
    main()
