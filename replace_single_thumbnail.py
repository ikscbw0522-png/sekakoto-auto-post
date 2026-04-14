#!/usr/bin/env python3
"""特定の記事1つのサムネイルを差し替えるスクリプト"""
import sys
import os
import base64
import json
import urllib.request
from generate_thumbnails_v2 import (
    WP_SITE, WP_USER, WP_APP_PASSWORD, IMAGES_DIR, SLUG_MAP, PHRASE_QUERY,
    unsplash_search, download_image, make_thumbnail_from_photo,
    wp_upload_image, wp_get_post_id, wp_set_featured,
)

phrase = sys.argv[1] if len(sys.argv) > 1 else "よろしくお願いします"
slug = SLUG_MAP[phrase]

token = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
auth_header = f"Basic {token}"

# 既存画像を使う or 新規生成
img_path = os.path.join(IMAGES_DIR, f"{slug}.jpg")
query = PHRASE_QUERY[phrase]
url = unsplash_search(query)
bg = download_image(url)
make_thumbnail_from_photo(phrase, bg, img_path)

post_id = wp_get_post_id(slug, auth_header)
media_id = wp_upload_image(img_path, auth_header)
wp_set_featured(post_id, media_id, auth_header)
print(f"OK: {phrase} → post#{post_id} + media#{media_id}")
