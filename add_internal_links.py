#!/usr/bin/env python3
"""各記事の末尾に「関連記事」セクション（同カテゴリ4本）を追加"""
import base64
import json
import random
import urllib.request
import urllib.error

WP_SITE = "https://sekai-kotoba.com"
WP_USER = "ik.scbw0522@gmail.com"
WP_APP_PASSWORD = "2ABi uqcs JfQj qYMn 9lmH zSRc"

MARKER = "<!-- auto-related-start -->"
END_MARKER = "<!-- auto-related-end -->"


def fetch_all_posts(auth_header):
    """全記事を取得（カテゴリID、タイトル、リンク付き）"""
    posts = []
    page = 1
    while True:
        url = f"{WP_SITE}/wp-json/wp/v2/posts?per_page=100&page={page}&_fields=id,title,link,categories,content"
        req = urllib.request.Request(url, headers={"Authorization": auth_header})
        try:
            with urllib.request.urlopen(req) as r:
                batch = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 400:
                break
            raise
        if not batch:
            break
        posts.extend(batch)
        page += 1
    return posts


def update_post(post_id, new_content, auth_header):
    url = f"{WP_SITE}/wp-json/wp/v2/posts/{post_id}"
    payload = json.dumps({"content": new_content}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return r.status == 200


def build_related_html(related_posts):
    """関連記事セクションのHTMLを生成"""
    items = "\n".join(
        f'<li><a href="{p["link"]}">{p["title"]["rendered"]}</a></li>'
        for p in related_posts
    )
    return f"""
{MARKER}
<h2>関連記事</h2>
<ul class="related-posts">
{items}
</ul>
{END_MARKER}
"""


def strip_old_related(content: str) -> str:
    """既存の自動生成関連記事セクションを除去"""
    if MARKER in content and END_MARKER in content:
        start = content.index(MARKER)
        end = content.index(END_MARKER) + len(END_MARKER)
        return content[:start].rstrip() + content[end:]
    return content


def main():
    token = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
    auth = f"Basic {token}"

    print("全記事を取得中...")
    posts = fetch_all_posts(auth)
    print(f"取得記事数: {len(posts)}")

    # カテゴリ別に分類
    by_category = {}
    for p in posts:
        for cat in p.get("categories", []):
            by_category.setdefault(cat, []).append(p)

    updated = 0
    failed = 0
    for i, post in enumerate(posts, 1):
        cats = post.get("categories", [])
        if not cats:
            continue

        # 同カテゴリの他記事から4本ランダム選出
        candidates = [
            p for p in by_category[cats[0]]
            if p["id"] != post["id"]
        ]
        if len(candidates) < 2:
            continue

        related = random.sample(candidates, min(4, len(candidates)))
        related_html = build_related_html(related)

        # 既存の関連セクションを除去して新規追加
        content = post["content"]["rendered"]
        content = strip_old_related(content)
        new_content = content.rstrip() + "\n" + related_html

        try:
            update_post(post["id"], new_content, auth)
            updated += 1
            if i % 20 == 0:
                print(f"[{i}/{len(posts)}] 更新済み: {updated}")
        except urllib.error.HTTPError as e:
            failed += 1
            print(f"FAIL post#{post['id']}: {e.code}")

    print(f"\n完了: {updated} 記事更新、{failed} 失敗")


if __name__ == "__main__":
    main()
