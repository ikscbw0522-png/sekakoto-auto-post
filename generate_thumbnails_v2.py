#!/usr/bin/env python3
"""
アイキャッチ画像生成v2（Unsplash写真＋テキスト重ね）
- Unsplash APIで関連写真を取得
- 暗めのオーバーレイ＋白文字でタイトルを重ねる
- WordPressにアップロード → 記事に紐付け
"""

import os
import glob
import json
import base64
import random
import time
import urllib.request
import urllib.error
import urllib.parse
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ============ 設定 ============
WP_SITE = "https://sekai-kotoba.com"
WP_USER = "ik.scbw0522@gmail.com"
WP_APP_PASSWORD = "2ABi uqcs JfQj qYMn 9lmH zSRc"
UNSPLASH_KEY = "ivP-EfHevyN9etjpHNmCeUNQuBAGxxmo5nCE9yo5IN8"

ARTICLES_DIR = os.path.join(os.path.dirname(__file__), "記事サンプル")
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "thumbnails_v2")

FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
WIDTH, HEIGHT = 1200, 630

# フレーズ → Unsplash検索キーワード
PHRASE_QUERY = {
    "おはよう": "people waving smile morning",
    "こんにちは": "people greeting smile",
    "こんばんは": "friends smile evening",
    "さようなら": "people waving goodbye",
    "おやすみ": "family hug night",
    "はじめまして": "handshake business smile",
    "お元気ですか": "friends smiling talking",
    "久しぶり": "friends hug reunion smile",
    "いってきます": "family waving smile",
    "ただいま": "family hug welcome",
    "おかえり": "family welcome smile",
    "よろしくお願いします": "business handshake smile",
    "ありがとう": "thank you gratitude smile",
    "ごめんなさい": "apology sorry heart",
    "すみません": "people asking question smile",
    "感謝しています": "thank you heart gratitude",
    "助かりました": "helping hand support smile",
    "申し訳ございません": "business apology bow",
    "お世話になりました": "thank you farewell smile",
    "どういたしまして": "welcome smile friendly",
    "大丈夫です": "okay thumbs up smile",
    "おかげさまで": "happy grateful person smile",
    "お疲れ様です": "tired worker coffee break",
    "いただきます": "family dinner table food",
    "ごちそうさま": "happy after meal satisfied",
    "お先に失礼します": "leaving office goodbye wave",
    "お邪魔します": "visitor doorway greeting",
    "ようこそ": "welcome open door smile",
    "また会いましょう": "friends waving goodbye",
    "気をつけて": "waving goodbye care travel",
    "ごめんね": "sorry friends apology smile",
    "気にしないで": "comforting hug consolation",
    "許してください": "forgiveness apology hands",
    "心から感謝します": "heart hand gratitude sincere",
    "恐れ入ります": "business bowing polite",
    "本当にありがとう": "thank you deep gratitude",
    "いつもありがとう": "always thanks family love",
    "とんでもないです": "humble smile shy",
    "お気遣いありがとう": "kindness gift appreciation",
    "愛してる": "love couple heart romantic",
    "好きです": "in love confession smile",
    "嬉しい": "happy smile joy",
    "楽しい": "fun laughing friends",
    "悲しい": "sad crying person",
    "寂しい": "lonely alone quiet",
    "怒っている": "angry upset frustrated",
    "疲れた": "tired exhausted rest",
    "お腹すいた": "hungry food craving",
    "幸せ": "happy family joy smile",
    "心配しないで": "comforting reassurance hug",
    "頑張って": "cheering encouragement fist",
    "信じてる": "trust believe hands",
    "会いたい": "missing person longing",
    "大好き": "love heart cute couple",
    "おめでとう": "congratulations celebration cake",
    "かわいい": "cute baby puppy",
    "かっこいい": "cool stylish man",
    "最高": "thumbs up happy",
    "びっくりした": "surprised shocked face",
    "私の名前は": "introduction name tag meeting",
    "日本から来ました": "japan travel airport",
    "何歳です": "age birthday candle",
    "学生です": "student university books",
    "会社員です": "business office worker",
    "趣味は": "hobby painting music guitar",
    "が好きです": "favorite things smile",
    "日本語を話します": "speaking language conversation",
    "勉強しています": "studying books desk",
    "家族は何人": "family portrait together",
    "住んでいます": "house home neighborhood",
    "仕事は": "working professional job",
    "初めて来ました": "first time arrival tourist",
    "得意です": "skilled person talent",
    "ここはどこですか": "lost tourist map",
    "駅はどこ": "train station platform",
    "トイレはどこ": "restroom sign public",
    "いくらですか": "shopping price tag",
    "これをください": "shopping point select",
    "タクシー呼んで": "taxi cab hailing",
    "ホテルまで": "hotel lobby entrance",
    "地図を見せて": "map tourist showing",
    "写真を撮って": "camera photograph tourist",
    "チェックイン": "hotel reception check in",
    "チェックアウト": "hotel checkout luggage",
    "WiFiはありますか": "wifi phone cafe",
    "予約しています": "reservation booking",
    "何時ですか": "clock watch time",
    "どのくらいかかる": "waiting time schedule",
    "右に曲がって": "turn right road sign",
    "左に曲がって": "turn left road direction",
    "まっすぐ行って": "straight road path",
    "近くにコンビニ": "convenience store shop",
    "空港まで": "airport terminal travel",
    "切符はどこで": "train ticket counter",
    "この電車は止まる": "train platform station",
    "荷物を預かって": "luggage storage suitcase",
    "おすすめの観光地": "tourist attraction landmark",
    "両替したい": "currency exchange money",
    "おすすめは何": "recommendation pointing",
    "メニューを見せて": "restaurant menu book",
    "これは何": "food dish asking",
    "おいしい": "delicious food tasty",
    "まずい": "food unhappy face",
    "辛い": "spicy chili pepper",
    "甘い": "sweet dessert",
    "お会計": "restaurant bill check",
    "水をください": "water glass bottle",
    "ビールをください": "beer glass toast",
    "アレルギー": "allergy food warning",
    "ベジタリアン": "vegetarian salad vegetables",
    "持ち帰り": "takeaway food box",
    "予約したい": "reservation booking restaurant",
    "何人です": "group friends dinner",
    "禁煙席": "no smoking sign",
    "おかわり": "refill more food",
    "とても美味しかった": "happy eating satisfied",
    "辛くしないで": "mild food spoon",
    "クレジットカード": "credit card payment",
    "何がおすすめ": "menu asking waiter",
    "これと同じ": "pointing menu restaurant",
    "少なめ": "small portion plate",
    "お腹いっぱい": "full satisfied meal",
    "乾杯": "cheers toast drinks",
    "これはいくら": "price tag shopping",
    "安くして": "bargain discount shop",
    "試着": "trying clothes fitting",
    "他の色": "colorful clothes",
    "サイズ合わない": "clothes measuring size",
    "大きいサイズ": "clothes rack store",
    "小さいサイズ": "small clothing display",
    "見ているだけ": "window shopping browsing",
    "袋をください": "shopping bag",
    "レシート": "receipt cash register",
    "返品": "return package refund",
    "免税": "tax free sign shopping",
    "おすすめどれ": "shopping advice clerk",
    "プレゼント包装": "gift wrapping ribbon",
    "新しいもの": "new product shelf",
    "セール中": "sale discount sign",
    "現金のみ": "cash payment wallet",
    "お釣り": "coins change counter",
    "どこで買える": "shopping area shops",
    "お会いできて光栄": "handshake business meeting",
    "名刺をどうぞ": "business card exchange",
    "会議を始めよう": "business meeting conference",
    "確認させて": "office reviewing documents",
    "締め切り": "deadline calendar clock",
    "検討させて": "thinking office work",
    "ご連絡お待ち": "phone email office",
    "お忙しいところ": "busy office phone",
    "担当者": "office worker desk",
    "資料を送ります": "documents email office",
    "よろしくお願いいたします": "business handshake greeting",
    "お手数": "apologetic office clerk",
    "了解しました": "agreement office handshake",
    "少々お待ち": "waiting office",
    "かしこまりました": "service staff polite",
    "ご提案": "presentation meeting office",
    "予算": "calculator budget office",
    "契約書": "signing contract pen",
    "いつ届く": "delivery package waiting",
    "問題ありません": "thumbs up office ok",
    "付き合って": "couple holding hands",
    "一目惚れ": "love at first sight couple",
    "デート": "couple dating cafe",
    "連絡先": "phone contact number",
    "また会いたい": "missing friend longing",
    "ずっと一緒": "couple together forever",
    "友達になろう": "new friends handshake",
    "一緒に遊ぼう": "friends playing fun",
    "あなたが一番": "heart love gift",
    "運命の人": "couple romantic sunset",
    "結婚してください": "proposal wedding ring",
    "誕生日おめでとう": "birthday cake candle",
    "素敵ですね": "admire compliment smile",
    "一緒に写真": "friends taking selfie",
    "LINE交換": "smartphone chat app",
    "助けて": "help hands reaching",
    "警察": "police officer emergency",
    "救急車": "ambulance emergency",
    "病院はどこ": "hospital building sign",
    "気分が悪い": "sick person bed",
    "財布なくした": "lost wallet worry",
    "パスポートなくした": "lost passport airport",
    "道に迷いました": "lost confused map",
    "日本語話せる人": "speaking bubbles communication",
    "大使館": "embassy building flag",
    "盗まれました": "stolen bag worry",
    "痛いです": "pain holding head",
    "薬局": "pharmacy medicine bottles",
    "火事です": "fire emergency flames",
    "危ない": "warning sign danger",
    "やめてください": "stop hand gesture",
    "わかりません": "confused shrugging person",
    "もう一度": "repeat asking again",
    "ゆっくり話して": "slow communication",
    "英語話せる": "english speaking conversation",
    "予算はいくら": "budget calculator money",
    "何が良い": "recommendation choice menu",
}

# post_to_wordpress.py と同じ slug
SLUG_MAP = {
    "おはよう": "ohayou-foreign-languages",
    "こんにちは": "konnichiwa-foreign-languages",
    "こんばんは": "konbanwa-foreign-languages",
    "さようなら": "sayounara-foreign-languages",
    "おやすみ": "oyasumi-foreign-languages",
    "はじめまして": "hajimemashite-foreign-languages",
    "お元気ですか": "ogenki-desuka-foreign-languages",
    "久しぶり": "hisashiburi-foreign-languages",
    "いってきます": "ittekimasu-foreign-languages",
    "ただいま": "tadaima-foreign-languages",
    "おかえり": "okaeri-foreign-languages",
    "よろしくお願いします": "yoroshiku-foreign-languages",
    "ありがとう": "arigatou-foreign-languages",
    "ごめんなさい": "gomennasai-foreign-languages",
    "すみません": "sumimasen-foreign-languages",
    "感謝しています": "kansha-foreign-languages",
    "助かりました": "tasukarimashita-foreign-languages",
    "申し訳ございません": "moushiwake-foreign-languages",
    "お世話になりました": "osewa-foreign-languages",
    "どういたしまして": "douitashimashite-foreign-languages",
    "大丈夫です": "daijoubu-foreign-languages",
    "おかげさまで": "okagesamade-foreign-languages",
    "お疲れ様です": "otsukaresama-foreign-languages",
    "いただきます": "itadakimasu-foreign-languages",
    "ごちそうさま": "gochisousama-foreign-languages",
    "お先に失礼します": "osaki-shitsurei-foreign-languages",
    "お邪魔します": "ojama-shimasu-foreign-languages",
    "ようこそ": "youkoso-foreign-languages",
    "また会いましょう": "mata-aimashou-foreign-languages",
    "気をつけて": "kiwotsukete-foreign-languages",
    "ごめんね": "gomenne-foreign-languages",
    "気にしないで": "kinishinaide-foreign-languages",
    "許してください": "yurushite-foreign-languages",
    "心から感謝します": "kokorokara-kansha-foreign-languages",
    "恐れ入ります": "osoreirimasu-foreign-languages",
    "本当にありがとう": "hontouni-arigatou-foreign-languages",
    "いつもありがとう": "itsumo-arigatou-foreign-languages",
    "とんでもないです": "tondemonai-foreign-languages",
    "お気遣いありがとう": "okizukai-arigatou-foreign-languages",
    "愛してる": "aishiteru-foreign-languages",
    "好きです": "sukidesu-foreign-languages",
    "嬉しい": "ureshii-foreign-languages",
    "楽しい": "tanoshii-foreign-languages",
    "悲しい": "kanashii-foreign-languages",
    "寂しい": "sabishii-foreign-languages",
    "怒っている": "okotteru-foreign-languages",
    "疲れた": "tsukareta-foreign-languages",
    "お腹すいた": "onakasuita-foreign-languages",
    "幸せ": "shiawase-foreign-languages",
    "心配しないで": "shinpaishinaide-foreign-languages",
    "頑張って": "ganbatte-foreign-languages",
    "信じてる": "shinjiteru-foreign-languages",
    "会いたい": "aitai-foreign-languages",
    "大好き": "daisuki-foreign-languages",
    "おめでとう": "omedetou-foreign-languages",
    "かわいい": "kawaii-foreign-languages",
    "かっこいい": "kakkoii-foreign-languages",
    "最高": "saikou-foreign-languages",
    "びっくりした": "bikkuri-foreign-languages",
    "私の名前は": "watashi-no-namae-foreign-languages",
    "日本から来ました": "nihon-kara-foreign-languages",
    "何歳です": "nansai-foreign-languages",
    "学生です": "gakusei-foreign-languages",
    "会社員です": "kaishain-foreign-languages",
    "趣味は": "shumi-foreign-languages",
    "が好きです": "gasukidesu-foreign-languages",
    "日本語を話します": "nihongo-hanashimasu-foreign-languages",
    "勉強しています": "benkyo-foreign-languages",
    "家族は何人": "kazoku-foreign-languages",
    "住んでいます": "sundeimasu-foreign-languages",
    "仕事は": "shigoto-foreign-languages",
    "初めて来ました": "hajimete-foreign-languages",
    "得意です": "tokui-foreign-languages",
    "ここはどこですか": "kokowadoko-foreign-languages",
    "駅はどこ": "eki-doko-foreign-languages",
    "トイレはどこ": "toilet-doko-foreign-languages",
    "いくらですか": "ikura-foreign-languages",
    "これをください": "kore-kudasai-foreign-languages",
    "タクシー呼んで": "taxi-yonde-foreign-languages",
    "ホテルまで": "hotel-made-foreign-languages",
    "地図を見せて": "chizu-misete-foreign-languages",
    "写真を撮って": "shashin-totte-foreign-languages",
    "チェックイン": "checkin-foreign-languages",
    "チェックアウト": "checkout-foreign-languages",
    "WiFiはありますか": "wifi-foreign-languages",
    "予約しています": "yoyaku-foreign-languages",
    "何時ですか": "nanji-foreign-languages",
    "どのくらいかかる": "donokurai-foreign-languages",
    "右に曲がって": "migi-foreign-languages",
    "左に曲がって": "hidari-foreign-languages",
    "まっすぐ行って": "massugu-foreign-languages",
    "近くにコンビニ": "konbini-foreign-languages",
    "空港まで": "kuukou-foreign-languages",
    "切符はどこで": "kippu-foreign-languages",
    "この電車は止まる": "densha-tomaru-foreign-languages",
    "荷物を預かって": "nimotsu-azukatte-foreign-languages",
    "おすすめの観光地": "osusume-kankou-foreign-languages",
    "両替したい": "ryougae-foreign-languages",
    "おすすめは何": "osusume-nani-foreign-languages",
    "メニューを見せて": "menu-misete-foreign-languages",
    "これは何": "koreha-nani-foreign-languages",
    "おいしい": "oishii-foreign-languages",
    "まずい": "mazui-foreign-languages",
    "辛い": "karai-foreign-languages",
    "甘い": "amai-foreign-languages",
    "お会計": "okaikei-foreign-languages",
    "水をください": "mizu-kudasai-foreign-languages",
    "ビールをください": "beer-kudasai-foreign-languages",
    "アレルギー": "allergy-foreign-languages",
    "ベジタリアン": "vegetarian-foreign-languages",
    "持ち帰り": "mochikaeri-foreign-languages",
    "予約したい": "yoyaku-shitai-foreign-languages",
    "何人です": "nannin-foreign-languages",
    "禁煙席": "kinenseki-foreign-languages",
    "おかわり": "okawari-foreign-languages",
    "とても美味しかった": "totemo-oishikatta-foreign-languages",
    "辛くしないで": "karaku-shinaide-foreign-languages",
    "クレジットカード": "credit-card-foreign-languages",
    "何がおすすめ": "nani-osusume-foreign-languages",
    "これと同じ": "kore-to-onaji-foreign-languages",
    "少なめ": "sukuname-foreign-languages",
    "お腹いっぱい": "onaka-ippai-foreign-languages",
    "乾杯": "kanpai-foreign-languages",
    "これはいくら": "koreha-ikura-foreign-languages",
    "安くして": "yasuku-shite-foreign-languages",
    "試着": "shichaku-foreign-languages",
    "他の色": "hoka-no-iro-foreign-languages",
    "サイズ合わない": "size-awanai-foreign-languages",
    "大きいサイズ": "ookii-size-foreign-languages",
    "小さいサイズ": "chiisai-size-foreign-languages",
    "見ているだけ": "miteru-dake-foreign-languages",
    "袋をください": "fukuro-kudasai-foreign-languages",
    "レシート": "receipt-foreign-languages",
    "返品": "henpin-foreign-languages",
    "免税": "menzei-foreign-languages",
    "おすすめどれ": "osusume-dore-foreign-languages",
    "プレゼント包装": "present-housou-foreign-languages",
    "新しいもの": "atarashii-mono-foreign-languages",
    "セール中": "sale-chuu-foreign-languages",
    "現金のみ": "genkin-nomi-foreign-languages",
    "お釣り": "otsuri-foreign-languages",
    "どこで買える": "dokode-kaeru-foreign-languages",
    "お会いできて光栄": "oaidekite-kouei-foreign-languages",
    "名刺をどうぞ": "meishi-douzo-foreign-languages",
    "会議を始めよう": "kaigi-hajime-foreign-languages",
    "確認させて": "kakunin-sasete-foreign-languages",
    "締め切り": "shimekiri-foreign-languages",
    "検討させて": "kentou-sasete-foreign-languages",
    "ご連絡お待ち": "gorenraku-omachi-foreign-languages",
    "お忙しいところ": "oisogashii-foreign-languages",
    "担当者": "tantousha-foreign-languages",
    "資料を送ります": "shiryou-okurimasu-foreign-languages",
    "よろしくお願いいたします": "yoroshiku-itashimasu-foreign-languages",
    "お手数": "otesuu-foreign-languages",
    "了解しました": "ryoukai-foreign-languages",
    "少々お待ち": "shoushou-omachi-foreign-languages",
    "かしこまりました": "kashikomarimashita-foreign-languages",
    "ご提案": "goteian-foreign-languages",
    "予算": "yosan-foreign-languages",
    "契約書": "keiyakusho-foreign-languages",
    "いつ届く": "itsu-todoku-foreign-languages",
    "問題ありません": "mondai-arimasen-foreign-languages",
    "付き合って": "tsukiatte-foreign-languages",
    "一目惚れ": "hitomebore-foreign-languages",
    "デート": "date-foreign-languages",
    "連絡先": "renrakusaki-foreign-languages",
    "また会いたい": "mata-aitai-foreign-languages",
    "ずっと一緒": "zutto-issho-foreign-languages",
    "友達になろう": "tomodachi-ninarou-foreign-languages",
    "一緒に遊ぼう": "issho-ni-asobou-foreign-languages",
    "あなたが一番": "anataga-ichiban-foreign-languages",
    "運命の人": "unmei-no-hito-foreign-languages",
    "結婚してください": "kekkon-foreign-languages",
    "誕生日おめでとう": "tanjoubi-omedetou-foreign-languages",
    "素敵ですね": "suteki-foreign-languages",
    "一緒に写真": "issho-ni-shashin-foreign-languages",
    "LINE交換": "line-koukan-foreign-languages",
    "助けて": "tasukete-foreign-languages",
    "警察": "keisatsu-foreign-languages",
    "救急車": "kyuukyuusha-foreign-languages",
    "病院はどこ": "byouin-doko-foreign-languages",
    "気分が悪い": "kibun-warui-foreign-languages",
    "財布なくした": "saifu-nakushita-foreign-languages",
    "パスポートなくした": "passport-nakushita-foreign-languages",
    "道に迷いました": "michi-mayoi-foreign-languages",
    "日本語話せる人": "nihongo-hanaseru-foreign-languages",
    "大使館": "taishikan-foreign-languages",
    "盗まれました": "nusumareta-foreign-languages",
    "痛いです": "itai-foreign-languages",
    "薬局": "yakkyoku-foreign-languages",
    "火事です": "kaji-foreign-languages",
    "危ない": "abunai-foreign-languages",
    "やめてください": "yamete-foreign-languages",
    "わかりません": "wakarimasen-foreign-languages",
    "もう一度": "mouichido-foreign-languages",
    "ゆっくり話して": "yukkuri-hanashite-foreign-languages",
    "英語話せる": "eigo-hanaseru-foreign-languages",
    "予算はいくら": "yosan-ikura-foreign-languages",
    "何が良い": "nani-ga-ii-foreign-languages",
}


def unsplash_search(query: str):
    """Unsplashで検索し、ランダムに1枚の画像URLを返す。失敗時は None"""
    q = urllib.parse.quote(query)
    url = f"https://api.unsplash.com/search/photos?query={q}&per_page=10&orientation=landscape&client_id={UNSPLASH_KEY}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read())
            results = data.get("results", [])
            if not results:
                return None
            photo = random.choice(results)
            return photo["urls"]["regular"]
    except Exception:
        return None


def make_solid_bg(palette_idx: int) -> Image.Image:
    """Unsplash失敗時のフォールバック：単色グラデ背景"""
    palettes = [
        (45, 52, 97), (44, 95, 45), (120, 40, 60),
        (33, 102, 172), (176, 91, 45), (80, 40, 120),
        (55, 90, 110), (100, 60, 90),
    ]
    color = palettes[palette_idx % len(palettes)]
    img = Image.new("RGB", (WIDTH, HEIGHT), color)
    # 斜めグラデの演出
    draw = ImageDraw.Draw(img)
    for i in range(0, WIDTH, 8):
        alpha_shift = int(i * 0.15)
        draw.rectangle(
            [(i, 0), (i + 8, HEIGHT)],
            fill=(
                min(255, color[0] + alpha_shift),
                min(255, color[1] + alpha_shift),
                min(255, color[2] + alpha_shift),
            ),
        )
    return img


def download_image(url: str) -> Image.Image:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as res:
        return Image.open(BytesIO(res.read())).convert("RGB")


def make_thumbnail_from_photo(phrase: str, bg_img: Image.Image, out_path: str):
    # 背景をリサイズしてクロップ（1200x630）
    ratio = max(WIDTH / bg_img.width, HEIGHT / bg_img.height)
    new_w, new_h = int(bg_img.width * ratio), int(bg_img.height * ratio)
    bg = bg_img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - WIDTH) // 2
    top = (new_h - HEIGHT) // 2
    bg = bg.crop((left, top, left + WIDTH, top + HEIGHT))

    # 軽くだけぼかす
    bg = bg.filter(ImageFilter.GaussianBlur(radius=1))

    # 白っぽいオーバーレイ（明るく保ちつつ文字を読みやすく）
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 50))
    bg = bg.convert("RGBA")
    bg = Image.alpha_composite(bg, overlay)

    # 中央に半透明の白い箱（文字背景用）
    box = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(box)
    bdraw.rectangle([(80, 170), (WIDTH - 80, 560)], fill=(255, 255, 255, 200))
    bg = Image.alpha_composite(bg, box)

    draw = ImageDraw.Draw(bg)

    # メインタイトル（濃い紺色）全記事で統一サイズ
    main_color = (30, 50, 110)
    phrase_text = f"「{phrase}」"
    font_size = 90  # さらに小さめに統一
    font_phrase = ImageFont.truetype(FONT_PATH, font_size)
    bbox = draw.textbbox((0, 0), phrase_text, font=font_phrase)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, 235), phrase_text, font=font_phrase, fill=main_color)

    # サブタイトル
    font_sub = ImageFont.truetype(FONT_PATH, 52)
    sub_text = "は外国語で何て言う？"
    bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, 395), sub_text, font=font_sub, fill=main_color)

    # アクセント帯（黄色のライン）
    draw.rectangle([(WIDTH // 2 - 120, 480), (WIDTH // 2 + 120, 486)], fill=(255, 165, 0))

    # 下部：10言語
    font_bottom = ImageFont.truetype(FONT_PATH, 36)
    bottom_text = "10言語での言い方・発音まとめ"
    bbox = draw.textbbox((0, 0), bottom_text, font=font_bottom)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, 510), bottom_text, font=font_bottom, fill=main_color)

    bg.convert("RGB").save(out_path, "JPEG", quality=88)


def wp_upload_image(image_path: str, auth_header: str, max_retry: int = 2) -> int:
    url = f"{WP_SITE}/wp-json/wp/v2/media"
    with open(image_path, "rb") as f:
        data = f.read()

    # タイムスタンプ＋ランダム文字で一意なファイル名に（SiteGuard回避）
    for attempt in range(max_retry + 1):
        unique = f"thumb-{int(time.time() * 1000)}-{random.randint(1000, 9999)}.jpg"
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Authorization": auth_header,
                "Content-Type": "image/jpeg",
                "Content-Disposition": f'attachment; filename="{unique}"',
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as res:
                return json.loads(res.read())["id"]
        except urllib.error.HTTPError as e:
            if e.code == 403 and attempt < max_retry:
                time.sleep(5)
                continue
            raise


def wp_get_post_id(slug: str, auth_header: str) -> int:
    url = f"{WP_SITE}/wp-json/wp/v2/posts?slug={slug}"
    req = urllib.request.Request(url, headers={"Authorization": auth_header})
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read())
        return data[0]["id"] if data else 0


def wp_post_has_featured(slug: str, auth_header: str) -> bool:
    """記事にすでにアイキャッチが設定されているか"""
    url = f"{WP_SITE}/wp-json/wp/v2/posts?slug={slug}"
    req = urllib.request.Request(url, headers={"Authorization": auth_header})
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read())
        if not data:
            return False
        return data[0].get("featured_media", 0) > 0


def wp_set_featured(post_id: int, media_id: int, auth_header: str):
    url = f"{WP_SITE}/wp-json/wp/v2/posts/{post_id}"
    req = urllib.request.Request(
        url,
        data=json.dumps({"featured_media": media_id}).encode(),
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as res:
        return res.status == 200


def main(only_phrase=None, retry_list=None):
    import time
    os.makedirs(IMAGES_DIR, exist_ok=True)
    token = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
    auth_header = f"Basic {token}"

    if only_phrase:
        phrases = [only_phrase]
    elif retry_list:
        phrases = retry_list
    else:
        phrases = list(SLUG_MAP.keys())
    print(f"処理対象: {len(phrases)} 記事\n")

    for i, phrase in enumerate(phrases, 1):
        slug = SLUG_MAP[phrase]
        query = PHRASE_QUERY.get(phrase, "travel culture")
        img_path = os.path.join(IMAGES_DIR, f"{slug}.jpg")

        # すでにアイキャッチが設定されている記事はスキップ
        if not only_phrase:
            try:
                if wp_post_has_featured(slug, auth_header):
                    print(f"[{i}] SKIP (画像済): {phrase}")
                    continue
            except Exception:
                pass

        # 1. Unsplashから写真取得（失敗時は単色背景にフォールバック）
        photo_url = unsplash_search(query)
        if photo_url:
            try:
                bg = download_image(photo_url)
            except Exception:
                bg = make_solid_bg(i)
        else:
            bg = make_solid_bg(i)

        # 2. 合成
        make_thumbnail_from_photo(phrase, bg, img_path)

        if only_phrase:
            print(f"[{i}] 生成完了（テスト）: {img_path}")
            return

        # 3. WordPressへアップロード＆紐付け
        try:
            post_id = wp_get_post_id(slug, auth_header)
            media_id = wp_upload_image(img_path, auth_header)
            wp_set_featured(post_id, media_id, auth_header)
            print(f"[{i}] OK  {phrase} → post#{post_id} + media#{media_id}")
        except urllib.error.HTTPError as e:
            print(f"[{i}] 失敗: {phrase} - {e.code}")

        # レート制限回避
        time.sleep(3)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        main(only_phrase="おはよう")
    elif len(sys.argv) > 1 and sys.argv[1] == "retry":
        main(retry_list=["こんにちは", "さようなら", "はじめまして", "いってきます"])
    elif len(sys.argv) > 1 and sys.argv[1] == "new":
        # 全記事をチェック、画像未設定のみ処理
        main()
    else:
        main()
