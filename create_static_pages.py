#!/usr/bin/env python3
"""AdSense審査用の固定ページ3点を作成"""
import base64
import json
import urllib.request
import urllib.error

WP_SITE = "https://sekai-kotoba.com"
WP_USER = "ik.scbw0522@gmail.com"
WP_APP_PASSWORD = "2ABi uqcs JfQj qYMn 9lmH zSRc"
CONTACT_EMAIL = "ik.scbw0522@gmail.com"

PRIVACY_POLICY = """
<h2>はじめに</h2>
<p>当サイト「世界のことば辞典」（https://sekai-kotoba.com、以下「当サイト」）をご利用いただきありがとうございます。当サイトでは、利用者の皆様のプライバシーを尊重し、個人情報の保護を最重要視しています。本プライバシーポリシーでは、当サイトがどのように情報を収集し、利用するかを説明します。</p>

<h2>個人情報の収集について</h2>
<p>当サイトでは、お問い合わせフォーム等を通じて、お名前、メールアドレス等の個人情報をご提供いただく場合があります。これらの個人情報はお問い合わせへの回答や必要な情報をご連絡する目的以外には利用いたしません。</p>

<h2>アクセス解析ツールについて</h2>
<p>当サイトでは、Googleによるアクセス解析ツール「Googleアナリティクス」を利用しています。このGoogleアナリティクスはトラフィックデータの収集のためにCookieを使用しています。このトラフィックデータは匿名で収集されており、個人を特定するものではありません。</p>
<p>この機能はCookieを無効にすることで収集を拒否することが出来ますので、お使いのブラウザの設定をご確認ください。この規約に関して、詳しくは<a href="https://marketingplatform.google.com/about/analytics/terms/jp/" target="_blank" rel="noopener">こちら</a>をご覧ください。</p>

<h2>広告の配信について</h2>
<p>当サイトは、第三者配信の広告サービス（Google AdSense 等）を利用することがあります。こうした広告配信事業者は、ユーザーの興味に応じた商品やサービスの広告を表示するため、当サイトや他サイトへのアクセスに関する情報『Cookie』（氏名、住所、メール アドレス、電話番号は含まれません）を使用することがあります。</p>
<p>Google による広告での Cookie の使用を無効にする方法については、<a href="https://policies.google.com/technologies/ads?hl=ja" target="_blank" rel="noopener">広告 – ポリシーと規約 – Google</a> をご覧ください。</p>

<h2>Amazonアソシエイト・プログラム</h2>
<p>当サイトは、Amazon.co.jpを宣伝しリンクすることによってサイトが紹介料を獲得できる手段を提供することを目的に設定されたアフィリエイト・プログラムである、Amazonアソシエイト・プログラムの参加者となる場合があります。</p>

<h2>免責事項</h2>
<p>当サイトで掲載している言語情報やフレーズの翻訳については、最大限正確を期しておりますが、言語の地域差・時代による変化等により誤りや不正確な情報が含まれている場合があります。当サイトの情報を利用したことによるいかなる損害についても、当サイトは一切の責任を負いかねますので、ご了承ください。</p>
<p>当サイトから他のサイトへリンクしている場合がありますが、リンク先のサイトで提供される情報、サービス等について一切の責任を負いません。</p>

<h2>著作権について</h2>
<p>当サイトで掲載している文章・画像等の著作物の無断転載を禁止します。引用の際は、当サイトのURLを明記のうえリンクを設置してください。</p>

<h2>プライバシーポリシーの変更について</h2>
<p>当サイトは、必要に応じてこのプライバシーポリシーの内容を変更します。その場合、変更した内容について当ページに掲載します。</p>

<h2>お問い合わせ</h2>
<p>当サイトのプライバシーポリシーに関するお問い合わせは、<a href="/contact/">お問い合わせフォーム</a>よりご連絡ください。</p>

<p>初版制定日：2026年4月14日</p>
"""

CONTACT = f"""
<h2>お問い合わせ</h2>
<p>当サイト「世界のことば辞典」に関するお問い合わせは、以下のメールアドレスまでご連絡ください。</p>

<h3>お問い合わせ先</h3>
<p><strong>メールアドレス：</strong> {CONTACT_EMAIL}</p>

<h3>お問い合わせ内容の例</h3>
<ul>
<li>記事内容に関するご質問・ご指摘</li>
<li>翻訳・発音に関する修正のご提案</li>
<li>掲載希望の言語・フレーズのリクエスト</li>
<li>取材・提携のご相談</li>
<li>広告・プロモーションのお問い合わせ</li>
</ul>

<h3>お問い合わせの際のお願い</h3>
<ul>
<li>件名に「世界のことば辞典について」と記載いただけるとスムーズです</li>
<li>内容を具体的にご記入ください</li>
<li>3営業日以内の返信を心がけておりますが、内容により時間をいただく場合があります</li>
</ul>

<h3>個人情報の取り扱い</h3>
<p>お問い合わせの際にご提供いただいた個人情報は、<a href="/privacy-policy/">プライバシーポリシー</a>に則り、適切に管理いたします。お問い合わせ対応以外の目的で使用することはありません。</p>
"""

ABOUT = """
<h2>運営者情報</h2>

<h3>サイト名</h3>
<p>世界のことば辞典</p>

<h3>サイトURL</h3>
<p>https://sekai-kotoba.com</p>

<h3>運営者</h3>
<p>Ikehata Ko</p>

<h3>サイトの目的</h3>
<p>「世界のことば辞典」は、日本語の日常フレーズを世界10言語で知ることができる多言語フレーズ辞書サイトです。韓国語、中国語、タイ語、ベトナム語、インドネシア語、タガログ語、マレー語、ヒンディー語、アラビア語、トルコ語という、比較的情報が少ないアジア・中東の言語を中心に、旅行・ビジネス・日常会話で役立つフレーズをまとめてご紹介しています。</p>

<h3>サイトの特徴</h3>
<ul>
<li>日本語1フレーズに対して10言語の言い方を網羅</li>
<li>現地文字と日本人が読みやすいカタカナ表記を併記</li>
<li>丁寧表現とカジュアル表現を使い分けて解説</li>
<li>文化的背景や言語の由来にも触れる</li>
<li>実際の会話で使える例文付き</li>
</ul>

<h3>取り扱うジャンル</h3>
<ul>
<li>あいさつ・基本表現</li>
<li>感謝・謝罪</li>
<li>感情・気持ち</li>
<li>自己紹介</li>
<li>旅行・移動</li>
<li>食事・レストラン</li>
<li>買い物</li>
<li>ビジネス・仕事</li>
<li>恋愛・友情</li>
<li>緊急・トラブル</li>
</ul>

<h3>こんな方におすすめ</h3>
<ul>
<li>海外旅行に行く方</li>
<li>外国人の友人とのコミュニケーションを深めたい方</li>
<li>複数の言語を比較しながら学びたい方</li>
<li>国際的な仕事をされている方</li>
<li>語学学習のきっかけを探している方</li>
</ul>

<h3>お問い合わせ</h3>
<p>記事に関するご質問・ご提案・その他のお問い合わせは、<a href="/contact/">お問い合わせページ</a>よりお願いいたします。</p>
"""


def create_page(title: str, content: str, slug: str, auth_header: str):
    url = f"{WP_SITE}/wp-json/wp/v2/pages"
    payload = {
        "title": title,
        "content": content,
        "slug": slug,
        "status": "publish",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read())["link"]
    except urllib.error.HTTPError as e:
        return f"ERROR {e.code}: {e.read().decode()[:200]}"


def main():
    token = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
    auth = f"Basic {token}"

    pages = [
        ("プライバシーポリシー", PRIVACY_POLICY, "privacy-policy"),
        ("お問い合わせ", CONTACT, "contact"),
        ("運営者情報", ABOUT, "about"),
    ]
    for title, content, slug in pages:
        result = create_page(title, content, slug, auth)
        print(f"{title}: {result}")


if __name__ == "__main__":
    main()
