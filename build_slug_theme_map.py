#!/usr/bin/env python3
"""WordPressから全記事のスラッグとタイトルを取得し、slug→theme マッピング作成。"""
import json
import re
from pathlib import Path

import requests

BASE = Path(__file__).parent
OUT = BASE / "slug_to_theme.json"
WP_URL = "https://sekai-kotoba.com"


def main():
    mapping = {}
    page = 1
    while True:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={"per_page": 100, "page": page, "_fields": "title,slug"},
            timeout=30,
        )
        if r.status_code != 200:
            break
        posts = r.json()
        if not posts:
            break
        for p in posts:
            title = p["title"]["rendered"]
            m = re.match(r"「(.+?)」は外国語", title)
            if m:
                mapping[p["slug"]] = m.group(1)
        if len(posts) < 100:
            break
        page += 1

    OUT.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"保存: {len(mapping)} エントリ -> {OUT}")


if __name__ == "__main__":
    main()
