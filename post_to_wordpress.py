#!/usr/bin/env python3
"""
WordPress 一括投稿スクリプト
multilang_blog/記事サンプル/ 内の .md 記事を
WordPress REST API 経由で一括投稿する
"""

import os
import re
import glob
import base64
import json
import urllib.request
import urllib.error

# ============ 設定 ============
WP_SITE = "https://sekai-kotoba.com"
WP_USER = "ik.scbw0522@gmail.com"
WP_APP_PASSWORD = "2ABi uqcs JfQj qYMn 9lmH zSRc"
ARTICLES_DIR = os.path.join(os.path.dirname(__file__), "記事サンプル")

# フレーズ → スラッグ/カテゴリ のマッピング
SLUG_MAP = {
    "おはよう": ("ohayou-foreign-languages", "greeting"),
    "こんにちは": ("konnichiwa-foreign-languages", "greeting"),
    "こんばんは": ("konbanwa-foreign-languages", "greeting"),
    "さようなら": ("sayounara-foreign-languages", "greeting"),
    "おやすみ": ("oyasumi-foreign-languages", "greeting"),
    "はじめまして": ("hajimemashite-foreign-languages", "greeting"),
    "お元気ですか": ("ogenki-desuka-foreign-languages", "greeting"),
    "久しぶり": ("hisashiburi-foreign-languages", "greeting"),
    "いってきます": ("ittekimasu-foreign-languages", "greeting"),
    "ただいま": ("tadaima-foreign-languages", "greeting"),
    "おかえり": ("okaeri-foreign-languages", "greeting"),
    "よろしくお願いします": ("yoroshiku-foreign-languages", "greeting"),
    "ありがとう": ("arigatou-foreign-languages", "thanks"),
    "ごめんなさい": ("gomennasai-foreign-languages", "thanks"),
    "すみません": ("sumimasen-foreign-languages", "thanks"),
    "感謝しています": ("kansha-foreign-languages", "thanks"),
    "助かりました": ("tasukarimashita-foreign-languages", "thanks"),
    "申し訳ございません": ("moushiwake-foreign-languages", "thanks"),
    "お世話になりました": ("osewa-foreign-languages", "thanks"),
    "どういたしまして": ("douitashimashite-foreign-languages", "thanks"),
    "大丈夫です": ("daijoubu-foreign-languages", "thanks"),
    "おかげさまで": ("okagesamade-foreign-languages", "thanks"),
    "お疲れ様です": ("otsukaresama-foreign-languages", "greeting"),
    "いただきます": ("itadakimasu-foreign-languages", "greeting"),
    "ごちそうさま": ("gochisousama-foreign-languages", "greeting"),
    "お先に失礼します": ("osaki-shitsurei-foreign-languages", "greeting"),
    "お邪魔します": ("ojama-shimasu-foreign-languages", "greeting"),
    "ようこそ": ("youkoso-foreign-languages", "greeting"),
    "また会いましょう": ("mata-aimashou-foreign-languages", "greeting"),
    "気をつけて": ("kiwotsukete-foreign-languages", "greeting"),
    "ごめんね": ("gomenne-foreign-languages", "thanks"),
    "気にしないで": ("kinishinaide-foreign-languages", "thanks"),
    "許してください": ("yurushite-foreign-languages", "thanks"),
    "心から感謝します": ("kokorokara-kansha-foreign-languages", "thanks"),
    "恐れ入ります": ("osoreirimasu-foreign-languages", "thanks"),
    "本当にありがとう": ("hontouni-arigatou-foreign-languages", "thanks"),
    "いつもありがとう": ("itsumo-arigatou-foreign-languages", "thanks"),
    "とんでもないです": ("tondemonai-foreign-languages", "thanks"),
    "お気遣いありがとう": ("okizukai-arigatou-foreign-languages", "thanks"),
    "愛してる": ("aishiteru-foreign-languages", "emotion"),
    "好きです": ("sukidesu-foreign-languages", "emotion"),
    "嬉しい": ("ureshii-foreign-languages", "emotion"),
    "楽しい": ("tanoshii-foreign-languages", "emotion"),
    "悲しい": ("kanashii-foreign-languages", "emotion"),
    "寂しい": ("sabishii-foreign-languages", "emotion"),
    "怒っている": ("okotteru-foreign-languages", "emotion"),
    "疲れた": ("tsukareta-foreign-languages", "emotion"),
    "お腹すいた": ("onakasuita-foreign-languages", "emotion"),
    "幸せ": ("shiawase-foreign-languages", "emotion"),
    "心配しないで": ("shinpaishinaide-foreign-languages", "emotion"),
    "頑張って": ("ganbatte-foreign-languages", "emotion"),
    "信じてる": ("shinjiteru-foreign-languages", "emotion"),
    "会いたい": ("aitai-foreign-languages", "emotion"),
    "大好き": ("daisuki-foreign-languages", "emotion"),
    "おめでとう": ("omedetou-foreign-languages", "emotion"),
    "かわいい": ("kawaii-foreign-languages", "emotion"),
    "かっこいい": ("kakkoii-foreign-languages", "emotion"),
    "最高": ("saikou-foreign-languages", "emotion"),
    "びっくりした": ("bikkuri-foreign-languages", "emotion"),
    "私の名前は": ("watashi-no-namae-foreign-languages", "introduction"),
    "日本から来ました": ("nihon-kara-foreign-languages", "introduction"),
    "何歳です": ("nansai-foreign-languages", "introduction"),
    "学生です": ("gakusei-foreign-languages", "introduction"),
    "会社員です": ("kaishain-foreign-languages", "introduction"),
    "趣味は": ("shumi-foreign-languages", "introduction"),
    "が好きです": ("gasukidesu-foreign-languages", "introduction"),
    "日本語を話します": ("nihongo-hanashimasu-foreign-languages", "introduction"),
    "勉強しています": ("benkyo-foreign-languages", "introduction"),
    "家族は何人": ("kazoku-foreign-languages", "introduction"),
    "住んでいます": ("sundeimasu-foreign-languages", "introduction"),
    "仕事は": ("shigoto-foreign-languages", "introduction"),
    "初めて来ました": ("hajimete-foreign-languages", "introduction"),
    "得意です": ("tokui-foreign-languages", "introduction"),
    "ここはどこですか": ("kokowadoko-foreign-languages", "introduction"),
    "駅はどこ": ("eki-doko-foreign-languages", "travel"),
    "トイレはどこ": ("toilet-doko-foreign-languages", "travel"),
    "いくらですか": ("ikura-foreign-languages", "travel"),
    "これをください": ("kore-kudasai-foreign-languages", "travel"),
    "タクシー呼んで": ("taxi-yonde-foreign-languages", "travel"),
    "ホテルまで": ("hotel-made-foreign-languages", "travel"),
    "地図を見せて": ("chizu-misete-foreign-languages", "travel"),
    "写真を撮って": ("shashin-totte-foreign-languages", "travel"),
    "チェックイン": ("checkin-foreign-languages", "travel"),
    "チェックアウト": ("checkout-foreign-languages", "travel"),
    "WiFiはありますか": ("wifi-foreign-languages", "travel"),
    "予約しています": ("yoyaku-foreign-languages", "travel"),
    "何時ですか": ("nanji-foreign-languages", "travel"),
    "どのくらいかかる": ("donokurai-foreign-languages", "travel"),
    "右に曲がって": ("migi-foreign-languages", "travel"),
    "左に曲がって": ("hidari-foreign-languages", "travel"),
    "まっすぐ行って": ("massugu-foreign-languages", "travel"),
    "近くにコンビニ": ("konbini-foreign-languages", "travel"),
    "空港まで": ("kuukou-foreign-languages", "travel"),
    "切符はどこで": ("kippu-foreign-languages", "travel"),
    "この電車は止まる": ("densha-tomaru-foreign-languages", "travel"),
    "荷物を預かって": ("nimotsu-azukatte-foreign-languages", "travel"),
    "おすすめの観光地": ("osusume-kankou-foreign-languages", "travel"),
    "両替したい": ("ryougae-foreign-languages", "travel"),
    "おすすめは何": ("osusume-nani-foreign-languages", "travel"),
    "メニューを見せて": ("menu-misete-foreign-languages", "food"),
    "これは何": ("koreha-nani-foreign-languages", "food"),
    "おいしい": ("oishii-foreign-languages", "food"),
    "まずい": ("mazui-foreign-languages", "food"),
    "辛い": ("karai-foreign-languages", "food"),
    "甘い": ("amai-foreign-languages", "food"),
    "お会計": ("okaikei-foreign-languages", "food"),
    "水をください": ("mizu-kudasai-foreign-languages", "food"),
    "ビールをください": ("beer-kudasai-foreign-languages", "food"),
    "アレルギー": ("allergy-foreign-languages", "food"),
    "ベジタリアン": ("vegetarian-foreign-languages", "food"),
    "持ち帰り": ("mochikaeri-foreign-languages", "food"),
    "予約したい": ("yoyaku-shitai-foreign-languages", "food"),
    "何人です": ("nannin-foreign-languages", "food"),
    "禁煙席": ("kinenseki-foreign-languages", "food"),
    "おかわり": ("okawari-foreign-languages", "food"),
    "とても美味しかった": ("totemo-oishikatta-foreign-languages", "food"),
    "辛くしないで": ("karaku-shinaide-foreign-languages", "food"),
    "クレジットカード": ("credit-card-foreign-languages", "food"),
    "何がおすすめ": ("nani-osusume-foreign-languages", "food"),
    "これと同じ": ("kore-to-onaji-foreign-languages", "food"),
    "少なめ": ("sukuname-foreign-languages", "food"),
    "お腹いっぱい": ("onaka-ippai-foreign-languages", "food"),
    "乾杯": ("kanpai-foreign-languages", "food"),
    "これはいくら": ("koreha-ikura-foreign-languages", "food"),
    "安くして": ("yasuku-shite-foreign-languages", "shopping"),
    "試着": ("shichaku-foreign-languages", "shopping"),
    "他の色": ("hoka-no-iro-foreign-languages", "shopping"),
    "サイズ合わない": ("size-awanai-foreign-languages", "shopping"),
    "大きいサイズ": ("ookii-size-foreign-languages", "shopping"),
    "小さいサイズ": ("chiisai-size-foreign-languages", "shopping"),
    "見ているだけ": ("miteru-dake-foreign-languages", "shopping"),
    "袋をください": ("fukuro-kudasai-foreign-languages", "shopping"),
    "レシート": ("receipt-foreign-languages", "shopping"),
    "返品": ("henpin-foreign-languages", "shopping"),
    "免税": ("menzei-foreign-languages", "shopping"),
    "おすすめどれ": ("osusume-dore-foreign-languages", "shopping"),
    "プレゼント包装": ("present-housou-foreign-languages", "shopping"),
    "新しいもの": ("atarashii-mono-foreign-languages", "shopping"),
    "セール中": ("sale-chuu-foreign-languages", "shopping"),
    "現金のみ": ("genkin-nomi-foreign-languages", "shopping"),
    "お釣り": ("otsuri-foreign-languages", "shopping"),
    "どこで買える": ("dokode-kaeru-foreign-languages", "shopping"),
    "お会いできて光栄": ("oaidekite-kouei-foreign-languages", "business"),
    "名刺をどうぞ": ("meishi-douzo-foreign-languages", "business"),
    "会議を始めよう": ("kaigi-hajime-foreign-languages", "business"),
    "確認させて": ("kakunin-sasete-foreign-languages", "business"),
    "締め切り": ("shimekiri-foreign-languages", "business"),
    "検討させて": ("kentou-sasete-foreign-languages", "business"),
    "ご連絡お待ち": ("gorenraku-omachi-foreign-languages", "business"),
    "お忙しいところ": ("oisogashii-foreign-languages", "business"),
    "担当者": ("tantousha-foreign-languages", "business"),
    "資料を送ります": ("shiryou-okurimasu-foreign-languages", "business"),
    "よろしくお願いいたします": ("yoroshiku-itashimasu-foreign-languages", "business"),
    "お手数": ("otesuu-foreign-languages", "business"),
    "了解しました": ("ryoukai-foreign-languages", "business"),
    "少々お待ち": ("shoushou-omachi-foreign-languages", "business"),
    "かしこまりました": ("kashikomarimashita-foreign-languages", "business"),
    "ご提案": ("goteian-foreign-languages", "business"),
    "予算": ("yosan-foreign-languages", "business"),
    "契約書": ("keiyakusho-foreign-languages", "business"),
    "いつ届く": ("itsu-todoku-foreign-languages", "business"),
    "問題ありません": ("mondai-arimasen-foreign-languages", "business"),
    "付き合って": ("tsukiatte-foreign-languages", "love"),
    "一目惚れ": ("hitomebore-foreign-languages", "love"),
    "デート": ("date-foreign-languages", "love"),
    "連絡先": ("renrakusaki-foreign-languages", "love"),
    "また会いたい": ("mata-aitai-foreign-languages", "love"),
    "ずっと一緒": ("zutto-issho-foreign-languages", "love"),
    "友達になろう": ("tomodachi-ninarou-foreign-languages", "love"),
    "一緒に遊ぼう": ("issho-ni-asobou-foreign-languages", "love"),
    "あなたが一番": ("anataga-ichiban-foreign-languages", "love"),
    "運命の人": ("unmei-no-hito-foreign-languages", "love"),
    "結婚してください": ("kekkon-foreign-languages", "love"),
    "誕生日おめでとう": ("tanjoubi-omedetou-foreign-languages", "love"),
    "素敵ですね": ("suteki-foreign-languages", "love"),
    "一緒に写真": ("issho-ni-shashin-foreign-languages", "love"),
    "LINE交換": ("line-koukan-foreign-languages", "love"),
    "助けて": ("tasukete-foreign-languages", "emergency"),
    "警察": ("keisatsu-foreign-languages", "emergency"),
    "救急車": ("kyuukyuusha-foreign-languages", "emergency"),
    "病院はどこ": ("byouin-doko-foreign-languages", "emergency"),
    "気分が悪い": ("kibun-warui-foreign-languages", "emergency"),
    "財布なくした": ("saifu-nakushita-foreign-languages", "emergency"),
    "パスポートなくした": ("passport-nakushita-foreign-languages", "emergency"),
    "道に迷いました": ("michi-mayoi-foreign-languages", "emergency"),
    "日本語話せる人": ("nihongo-hanaseru-foreign-languages", "emergency"),
    "大使館": ("taishikan-foreign-languages", "emergency"),
    "盗まれました": ("nusumareta-foreign-languages", "emergency"),
    "痛いです": ("itai-foreign-languages", "emergency"),
    "薬局": ("yakkyoku-foreign-languages", "emergency"),
    "火事です": ("kaji-foreign-languages", "emergency"),
    "危ない": ("abunai-foreign-languages", "emergency"),
    "やめてください": ("yamete-foreign-languages", "emergency"),
    "わかりません": ("wakarimasen-foreign-languages", "emergency"),
    "もう一度": ("mouichido-foreign-languages", "emergency"),
    "ゆっくり話して": ("yukkuri-hanashite-foreign-languages", "emergency"),
    "英語話せる": ("eigo-hanaseru-foreign-languages", "emergency"),
    "予算はいくら": ("yosan-ikura-foreign-languages", "emergency"),
    "何が良い": ("nani-ga-ii-foreign-languages", "emergency"),
}


def md_to_html(md: str) -> str:
    """簡易 Markdown → HTML 変換（このサイトのテンプレートに特化）"""
    lines = md.split("\n")
    html = []
    in_table = False
    table_rows = []

    for line in lines:
        # テーブル
        if line.startswith("|"):
            if not in_table:
                in_table = True
                table_rows = []
            # 区切り行はスキップ
            if re.match(r"^\|[\s\-:|]+\|$", line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            tag = "th" if not table_rows else "td"
            row_html = "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"
            table_rows.append(row_html)
            continue
        else:
            if in_table:
                html.append("<table>" + "".join(table_rows) + "</table>")
                in_table = False
                table_rows = []

        # 見出し
        if line.startswith("# "):
            # タイトル行は本文から除外（タイトルは別で渡す）
            continue
        if line.startswith("## "):
            html.append(f"<h2>{line[3:].strip()}</h2>")
            continue
        if line.startswith("### "):
            html.append(f"<h3>{line[4:].strip()}</h3>")
            continue

        # 水平線
        if line.strip() == "---":
            continue

        # 引用
        if line.startswith("> "):
            html.append(f"<blockquote>{line[2:].strip()}</blockquote>")
            continue

        # 空行
        if line.strip() == "":
            html.append("")
            continue

        # インライン装飾 **bold**
        processed = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
        html.append(f"<p>{processed}</p>")

    if in_table:
        html.append("<table>" + "".join(table_rows) + "</table>")

    return "\n".join(html)


def extract_title_and_phrase(md: str, filename: str):
    """記事からタイトルとフレーズ名を抽出"""
    first_line = md.split("\n", 1)[0].lstrip("# ").strip()
    # ファイル名からフレーズ名を取得（「おはよう_外国語.md」→「おはよう」）
    base = os.path.basename(filename).replace("_外国語.md", "")
    return first_line, base


def post_exists(slug: str, auth_header: str) -> bool:
    """指定スラッグの記事がすでに存在するか確認"""
    url = f"{WP_SITE}/wp-json/wp/v2/posts?slug={slug}"
    req = urllib.request.Request(url, headers={"Authorization": auth_header})
    with urllib.request.urlopen(req) as res:
        return bool(json.loads(res.read()))


def get_category_id(cat_slug: str, auth_header: str) -> int:
    """カテゴリスラッグから ID を取得"""
    url = f"{WP_SITE}/wp-json/wp/v2/categories?slug={cat_slug}"
    req = urllib.request.Request(url, headers={"Authorization": auth_header})
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read())
        if data:
            return data[0]["id"]
    return 0


def post_article(title: str, content: str, slug: str, category_id: int, auth_header: str):
    """記事を投稿"""
    url = f"{WP_SITE}/wp-json/wp/v2/posts"
    payload = {
        "title": title,
        "content": content,
        "slug": slug,
        "status": "publish",
        "categories": [category_id] if category_id else [],
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read())
            return True, data.get("link", "")
    except urllib.error.HTTPError as e:
        return False, f"{e.code}: {e.read().decode()}"


def main():
    # Basic 認証ヘッダを作成
    token = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
    auth_header = f"Basic {token}"

    # カテゴリ ID を事前に取得
    cat_cache = {}

    files = sorted(glob.glob(os.path.join(ARTICLES_DIR, "*.md")))
    print(f"投稿対象: {len(files)} 記事\n")

    for i, path in enumerate(files, 1):
        with open(path, encoding="utf-8") as f:
            md = f.read()

        title, phrase = extract_title_and_phrase(md, path)
        if phrase not in SLUG_MAP:
            print(f"[{i}] SKIP (マップ未登録): {phrase}")
            continue

        slug, cat_slug = SLUG_MAP[phrase]

        # すでに投稿済みかチェック
        if post_exists(slug, auth_header):
            print(f"[{i}] SKIP (投稿済み): {phrase}")
            continue

        # カテゴリ ID 取得
        if cat_slug not in cat_cache:
            cat_cache[cat_slug] = get_category_id(cat_slug, auth_header)

        cat_id = cat_cache[cat_slug]

        html = md_to_html(md)
        ok, info = post_article(title, html, slug, cat_id, auth_header)
        status = "OK " if ok else "NG "
        print(f"[{i}] {status} {phrase} → {info}")


if __name__ == "__main__":
    main()
