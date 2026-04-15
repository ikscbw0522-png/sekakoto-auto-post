add_filter('the_content', function($content) {
    if (!is_single() || is_feed() || is_admin()) return $content;

    $slug_to_url = [
    'kanpai-foreign-languages' => 'https://www.instagram.com/p/DXHQY7hGETo/',
    'oishii-foreign-languages' => 'https://www.instagram.com/p/DXIWf36kjlX/',
    'ikura-foreign-languages' => 'https://www.instagram.com/p/DXIXtqClVN7/',
    'gomennasai-foreign-languages' => 'https://www.instagram.com/reel/DXIehjcjL97/'
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
});
