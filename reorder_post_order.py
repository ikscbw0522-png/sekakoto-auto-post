#!/usr/bin/env python3
"""post_order.txt を IG insights に基づいて再並び替え。

結論（2026-04-20 insights）:
- TOP5: いくらですか(186), ありがとう(147), おやすみ(134), 乾杯(107), おはよう(101)
- WORST5: すみません(12), はじめまして(17), こんにちは(38), さようなら(53), こんばんは(54)

仮説：
- 旅行で「具体的に困る」実用フレーズが強い
- 日常すぎる挨拶は弱い

戦略：
- Tier 1（お金・決済・場所）を最上位へ
- Tier 2（緊急・トラブル）を次に
- Tier 3（食事・買い物）
- Tier 4（旅行必須サービス：予約・交通）
- Tier 5（恋愛・感情）
- Tier 6（感謝・祝福）
- Tier 7（日常挨拶）← WORST系は後ろに
- Tier 8（自己紹介・ビジネス）
"""
from pathlib import Path
from collections import OrderedDict

BASE = Path(__file__).parent
ORIGINAL = BASE / "post_order.txt"
BACKUP = BASE / "post_order_v1_backup.txt"
NEW = BASE / "post_order.txt"

# カテゴリ定義（キーワード → tier優先度）
# 低い数字ほど優先（上位に来る）
TIER_RULES = [
    # Tier 1: お金・決済・値段（最強実績：いくらですか 186）
    (10, ["いくら", "予算", "お会計", "現金", "クレジット", "レシート", "両替", "安く", "免税", "返品", "セール"]),
    # Tier 2: 緊急・トラブル（旅行者が絶対保存したい）
    (20, ["助けて", "病院", "救急", "警察", "火事", "危な", "盗まれ", "なくし", "パスポート", "財布", "迷い", "薬局", "アレルギー", "大使館", "痛い", "気分が悪い", "やめて"]),
    # Tier 3: 交通・場所
    (30, ["トイレ", "どこ", "駅", "空港", "ホテル", "タクシー", "電車", "切符", "地図", "ここは", "どのくらい", "まっすぐ", "右に", "左に", "近くに", "コンビニ", "WiFi", "観光地"]),
    # Tier 4: 注文・買い物・サービス
    (40, ["ください", "注文", "メニュー", "おすすめ", "持ち帰り", "試着", "サイズ", "他の色", "見ているだけ", "プレゼント包装", "袋", "これと同じ", "どこで買える", "いつ届く", "荷物", "予約", "チェックイン", "チェックアウト", "禁煙"]),
    # Tier 5: 食事・飲食（強テーマ：おいしい2位）
    (50, ["おいしい", "美味", "まずい", "お腹", "乾杯", "水を", "ビール", "いただき", "ごちそう", "辛い", "甘い", "辛くしない", "少なめ", "おかわり", "ベジタリアン"]),
    # Tier 6: コミュニケーション（旅先での会話補助）
    (60, ["日本から", "日本語", "英語話", "ゆっくり", "もう一度", "わかりません", "了解", "問題ありません", "確認", "検討", "ようこそ"]),
    # Tier 7: 感謝・感情（ありがとう reach 147）
    (70, ["ありがとう", "感謝", "助かり", "お気遣い", "光栄", "お世話", "恐れ入", "とんでもない", "どういたし"]),
    # Tier 8: 恋愛・親密（拡散性高）
    (80, ["愛してる", "大好き", "好きです", "会いたい", "また会い", "付き合", "結婚", "運命", "一目惚れ", "ずっと", "信じてる", "あなたが"]),
    # Tier 9: お祝い・励まし
    (85, ["おめでとう", "誕生日", "頑張", "気をつけて", "大丈夫", "心配しないで", "気にしないで"]),
    # Tier 10: 感情表現
    (90, ["嬉しい", "楽しい", "寂しい", "悲しい", "怒って", "疲れた", "幸せ", "びっくり", "最高", "かわいい", "かっこいい", "素敵"]),
    # Tier 11: 自己紹介・仕事（ビジネス旅行向け）
    (100, ["名前", "名刺", "連絡先", "LINE", "友達", "一緒に遊", "一緒に写真", "写真を撮", "初めて", "住んでいる", "会社員", "学生", "趣味", "仕事", "家族", "何人", "何歳", "来ました", "会議", "契約", "担当", "資料", "ご連絡", "ご提案", "締め切り", "お忙しい", "おかげさま"]),
    # Tier 12: 日常挨拶（弱い：WORST5のこんにちは・こんばんは・さようなら・はじめまして・すみません 含む）
    (120, ["おはよう", "おやすみ", "こんにちは", "こんばんは", "さようなら", "はじめまして", "すみません", "お疲れ様", "お元気", "おかえり", "ただいま", "いってきます", "いってらっしゃい", "久しぶり", "また会いましょう", "よろしく", "お邪魔", "お先に", "お手数", "かしこまり", "少々お待ち", "申し訳", "お会いできて", "ごめん", "ごめんね"]),
    # Tier 13: その他（未分類）
    (200, []),
]


def categorize(theme: str) -> int:
    """テーマを tier に振り分け。"""
    # 完全一致優先（ごめんなさい vs ごめんね 等）
    for tier, keywords in TIER_RULES:
        for kw in keywords:
            if kw in theme:
                return tier
    return 200  # その他


def main():
    themes = [line.strip() for line in ORIGINAL.read_text(encoding="utf-8").splitlines() if line.strip()]

    # バックアップ
    if not BACKUP.exists():
        BACKUP.write_text("\n".join(themes) + "\n", encoding="utf-8")
        print(f"📦 backup: {BACKUP.name}")

    # カテゴリ分け
    tiered = [(categorize(t), i, t) for i, t in enumerate(themes)]
    # tier昇順、同tier内は元の順序（安定）
    tiered.sort(key=lambda x: (x[0], x[1]))

    new_order = [t for _, _, t in tiered]

    # 重複削除（同じテーマが複数あっても1つだけ残す）
    seen = OrderedDict()
    for t in new_order:
        seen[t] = True
    new_order = list(seen.keys())

    # 統計
    from collections import Counter
    tier_counts = Counter(categorize(t) for t in new_order)
    print(f"📊 tier distribution:")
    for tier in sorted(tier_counts):
        label_map = {
            10: "お金・決済",
            20: "緊急・トラブル",
            30: "交通・場所",
            40: "注文・買物",
            50: "食事",
            60: "会話補助",
            70: "感謝・感情",
            80: "恋愛",
            85: "お祝い・励まし",
            90: "感情表現",
            100: "自己紹介・仕事",
            120: "日常挨拶",
            200: "未分類",
        }
        print(f"  tier {tier:3d} ({label_map.get(tier, '?'):12s}): {tier_counts[tier]}本")

    # 未分類を表示
    unclassified = [t for t in new_order if categorize(t) == 200]
    if unclassified:
        print(f"⚠️  未分類: {unclassified}")

    NEW.write_text("\n".join(new_order) + "\n", encoding="utf-8")
    print(f"✅ 新post_order.txt ({len(new_order)}本)")
    print(f"Top 10: {new_order[:10]}")


if __name__ == "__main__":
    main()
