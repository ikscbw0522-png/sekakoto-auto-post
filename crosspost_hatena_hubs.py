#!/usr/bin/env python3
"""未転載のWPハブ記事をはてなに自動投稿。

対象: ID3321（愛）, ID3318（感謝・謝罪）, ID3299（海外旅行）
既存の repurpose_content.py を import して使用。
"""
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

# repurpose_content.py の関数を再利用
sys.path.insert(0, str(__file__).rsplit("/", 1)[0])
from repurpose_content import (
    publish_hatena,
    extract_links_from_html,
    generate_hatena_content,
)
import requests

TARGETS = [
    {"id": 3299, "categories": ["海外旅行", "多言語"]},
    {"id": 3318, "categories": ["感謝", "多言語"]},
    {"id": 3321, "categories": ["愛", "多言語"]},
]


def fetch_wp_post(post_id):
    r = requests.get(
        f"https://sekai-kotoba.com/wp-json/wp/v2/posts/{post_id}",
        params={"_fields": "id,title,content,link"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main():
    results = []
    for t in TARGETS:
        print(f"\n━━━ ID{t['id']} ━━━")
        try:
            post = fetch_wp_post(t["id"])
            title = post["title"]["rendered"]
            wp_url = post["link"]
            html = post["content"]["rendered"]
            links = extract_links_from_html(html)
            print(f"  タイトル: {title}")
            print(f"  内部リンク抽出: {len(links)}本")

            content = generate_hatena_content(title, links, wp_url)
            print(f"  はてな投稿中...")
            hatena_url = publish_hatena(title, content, t["categories"])
            if hatena_url:
                print(f"  ✅ {hatena_url}")
                results.append({"id": t["id"], "title": title, "hatena": hatena_url})
            else:
                print(f"  ❌ 投稿失敗")
                results.append({"id": t["id"], "title": title, "error": "post failed"})
            time.sleep(2)  # rate limit保護
        except Exception as e:
            print(f"  ❌ {e}")
            results.append({"id": t["id"], "error": str(e)})

    print("\n━━━ サマリー ━━━")
    for r in results:
        status = r.get("hatena") or f"FAILED: {r.get('error')}"
        print(f"  ID{r['id']}: {status}")


if __name__ == "__main__":
    main()
