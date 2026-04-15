#!/usr/bin/env python3
"""slug→theme と theme→IG URL を結合して、WP Code Snippets用のPHP生成。"""
import json
from pathlib import Path

BASE = Path(__file__).parent
SLUG_TO_THEME = json.loads((BASE / "slug_to_theme.json").read_text(encoding="utf-8"))
EMBED_MAP = json.loads((BASE / "ig_embed_map.json").read_text(encoding="utf-8"))
OUT = BASE / "ig_embed_snippet.php"

# slug → permalink の直接マッピング生成
slug_to_url = {}
for slug, theme in SLUG_TO_THEME.items():
    if theme in EMBED_MAP:
        slug_to_url[slug] = EMBED_MAP[theme]["permalink"]

php_array = ",\n".join(
    f"    '{slug}' => '{url}'" for slug, url in slug_to_url.items()
)

php = f"""add_filter('the_content', function($content) {{
    if (!is_single() || is_feed() || is_admin()) return $content;

    $slug_to_url = [
{php_array}
    ];

    $slug = get_post_field('post_name', get_the_ID());
    if (!isset($slug_to_url[$slug])) return $content;

    $ig_url = $slug_to_url[$slug];
    $embed_url = rtrim($ig_url, '/') . '/embed';

    $embed = '<div style="max-width:540px;margin:40px auto;">
        <h3 style="text-align:center;color:#372d28;margin-bottom:16px;">🎥 Instagramで動画をチェック</h3>
        <iframe src="' . esc_url($embed_url) . '" width="100%" height="680" frameborder="0" scrolling="no" allowtransparency="true" style="border-radius:12px;"></iframe>
    </div>';

    return $content . $embed;
}});
"""

OUT.write_text(php, encoding="utf-8")
print(f"生成: {len(slug_to_url)} 記事対応 -> {OUT}")
