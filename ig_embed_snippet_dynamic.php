add_filter('the_content', function($content) {
    if (!is_single() || is_feed() || is_admin()) return $content;

    // slug → theme 名マッピング（記事タイトル「〜」から抽出）
    $title = get_the_title();
    if (!preg_match('/^「(.+?)」は外国語/u', $title, $m)) return $content;
    $theme = $m[1];

    // キャッシュから取得（1時間有効）
    $cache_key = 'sekakoto_ig_embed_map';
    $map = get_transient($cache_key);
    if ($map === false) {
        $url = 'https://raw.githubusercontent.com/ikscbw0522-png/sekakoto-auto-post/main/ig_embed_map.json';
        $response = wp_remote_get($url, ['timeout' => 10]);
        if (is_wp_error($response) || wp_remote_retrieve_response_code($response) !== 200) {
            return $content;
        }
        $body = wp_remote_retrieve_body($response);
        $map = json_decode($body, true);
        if (!is_array($map)) return $content;
        set_transient($cache_key, $map, HOUR_IN_SECONDS);
    }

    if (!isset($map[$theme]) || empty($map[$theme]['permalink'])) return $content;

    $ig_url = $map[$theme]['permalink'];
    $embed_url = rtrim($ig_url, '/') . '/embed';

    $embed = '<div style="max-width:540px;margin:40px auto;">
        <h3 style="text-align:center;color:#372d28;margin-bottom:16px;">🎥 Instagramで動画をチェック</h3>
        <iframe src="' . esc_url($embed_url) . '" width="100%" height="680" frameborder="0" scrolling="no" allowtransparency="true" style="border-radius:12px;"></iframe>
    </div>';

    return $content . $embed;
});
