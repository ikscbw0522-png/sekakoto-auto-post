#!/usr/bin/env python3
"""テーマ指定で Hyperframes 縦動画を生成。

記事サンプル/{theme}_外国語.md から8言語フレーズ・カタカナ・小ネタを抽出、
edge-tts で音声生成、Hyperframes index.html をテンプレ生成、レンダ、IG再エンコード。

Usage:
    python3 render_theme.py --theme いくらですか
    python3 render_theme.py --theme おはよう --no-reencode
    python3 render_theme.py --theme おはよう --hook 2  # 4つのフックパターンから選択

Output:
    output/{theme}.mp4   — IG仕様版（faststart, AAC 48kHz 192k）
    tmp/{theme}/         — レンダ用作業ディレクトリ
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
ARTICLES = ROOT / "記事サンプル"
AVATARS = ROOT / "avatars"
OUTPUT_DIR = HERE / "output"
TMP_DIR = HERE / "tmp"

# 8言語構成（HANDOFF・generate_convo_reel.py のLANG_CONFIGと一致）
LANG_CONFIG = [
    {"id": "ko", "jp": "韓国語", "label": "Korean", "flag": "🇰🇷", "tts_voice": "ko-KR-SunHiNeural"},
    {"id": "zh", "jp": "中国語", "label": "Chinese", "flag": "🇨🇳", "tts_voice": "zh-CN-YunxiNeural"},
    {"id": "th", "jp": "タイ語", "label": "Thai", "flag": "🇹🇭", "tts_voice": "th-TH-PremwadeeNeural"},
    {"id": "vi", "jp": "ベトナム語", "label": "Vietnamese", "flag": "🇻🇳", "tts_voice": "vi-VN-HoaiMyNeural"},
    {"id": "id-scene", "jp": "インドネシア語", "label": "Indonesian", "flag": "🇮🇩", "tts_voice": "id-ID-ArdiNeural", "audio_key": "id"},
    {"id": "hi", "jp": "ヒンディー語", "label": "Hindi", "flag": "🇮🇳", "tts_voice": "hi-IN-MadhurNeural"},
    {"id": "ar", "jp": "アラビア語", "label": "Arabic", "flag": "🇸🇦", "tts_voice": "ar-SA-ZariyahNeural"},
    {"id": "tr", "jp": "トルコ語", "label": "Turkish", "flag": "🇹🇷", "tts_voice": "tr-TR-AhmetNeural"},
]

# 保存誘発型フックパターン（4種、テーマhashで選択）
HOOK_PATTERNS = [
    {"top": "旅行前に絶対保存する🔖", "bottom": "8言語 / ネイティブ音声つき"},
    {"top": "これ知らずに海外行くと詰む", "bottom": "1本で8言語マスター🎧"},
    {"top": "友達に送ると『天才』扱い", "bottom": "8言語の神フレーズ"},
    {"top": "スクショ必須の神フレーズ集", "bottom": "保存→旅先で使う"},
]


def parse_article(theme: str) -> tuple[str, list[dict]]:
    """記事から phrase, sections を抽出。"""
    md_path = ARTICLES / f"{theme}_外国語.md"
    if not md_path.exists():
        sys.exit(f"記事なし: {md_path}")
    md = md_path.read_text(encoding="utf-8")
    m = re.search(r"^#\s*「(.+?)」", md, re.MULTILINE)
    phrase = m.group(1) if m else theme

    sections = []
    for cfg in LANG_CONFIG:
        jp = cfg["jp"]
        section_re = rf"##\s+{re.escape(jp)}(?:（[^）]+）)?で「[^」]+」"
        sec_m = re.search(section_re, md)
        if not sec_m:
            continue

        after = md[sec_m.end():sec_m.end() + 1500]

        # 現地語フレーズ抽出: **native（katakana）**
        ph_m = re.search(r"\*\*([^（(*]+?)[（(]([^）)]+)[）)]\*\*", after)
        if not ph_m:
            continue
        native = ph_m.group(1).strip()
        katakana = ph_m.group(2).strip()

        # 小ネタ抽出: 最初の段落（phraseの後）から最初の文を抽出
        note = extract_note(after, ph_m.end())

        sections.append({
            **cfg,
            "native": native,
            "katakana": katakana,
            "note": note,
            "audio_key": cfg.get("audio_key", cfg["id"]),
        })

    if len(sections) < 8:
        missing = [c["jp"] for c in LANG_CONFIG if c["jp"] not in [s["jp"] for s in sections]]
        sys.exit(f"言語不足 ({len(sections)}/8): 欠落={missing}")
    return phrase, sections


def extract_note(text: str, start: int) -> str:
    """phrase直後の段落から最初の文を抽出（50〜70文字目標）。"""
    after = text[start:].strip()
    # 最初の段落を取る
    para = re.split(r"\n\s*\n", after, maxsplit=1)[0].strip()
    # 改行・箇条書き記号除去
    para = re.sub(r"^[\*\->\s]+", "", para)
    para = re.sub(r"\s+", "", para).strip()
    # 最初の「。」で区切り
    first = re.split(r"[。．]", para, maxsplit=1)[0].strip()
    # 長すぎる場合はトリム
    if len(first) > 75:
        first = first[:72] + "…"
    # markdown強調記号を除去
    first = re.sub(r"\*+", "", first)
    return first


def pick_hook(theme: str) -> dict:
    """テーマのhashでフックパターンを決定論的に選択。"""
    h = int(hashlib.md5(theme.encode()).hexdigest(), 16)
    return HOOK_PATTERNS[h % len(HOOK_PATTERNS)]


async def gen_tts_all(phrase: str, sections: list[dict], out_dir: Path):
    """8言語のTTS音声をedge_ttsで生成。"""
    import edge_tts
    out_dir.mkdir(parents=True, exist_ok=True)
    for sec in sections:
        out = out_dir / f"{sec['audio_key']}.mp3"
        if out.exists():
            continue
        # TTSは現地語フレーズそのものを喋らせる
        text = sec["native"]
        tts = edge_tts.Communicate(text, sec["tts_voice"])
        await tts.save(str(out))


def copy_avatars(sections: list[dict], out_dir: Path):
    """言語別アバター画像をassetsにコピー。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    for sec in sections:
        found = False
        for ext in (".jpeg", ".jpg", ".png"):
            src = AVATARS / f"{sec['jp']}{ext}"
            if src.exists():
                shutil.copy(src, out_dir / f"{sec['audio_key']}{ext}")
                found = True
                break
        if not found:
            print(f"⚠️  avatar 見つからない: {sec['jp']}", file=sys.stderr)


def pick_phrase_size(native: str) -> str:
    """言語スライドのphrase（現地語）サイズクラスを決定。base=116px。"""
    n = len(native)
    if n >= 10:
        return "xsmall"
    if n >= 7:
        return "small"
    return ""


def pick_hook_phrase_size(phrase_with_brackets: str) -> str:
    """hook-phraseのサイズクラスを決定。base=140px、6chars超で縮小。"""
    n = len(phrase_with_brackets)  # 「」含む
    if n >= 9:  # 「xxxxxxx」以上
        return "xsmall"
    if n >= 6:  # 「xxxx」以上
        return "small"
    return ""


def build_html(theme: str, phrase: str, sections: list[dict], hook_idx: int | None = None) -> str:
    """index.html テンプレ生成。"""
    hook = HOOK_PATTERNS[hook_idx % len(HOOK_PATTERNS)] if hook_idx is not None else pick_hook(theme)

    # シーン秒数設計
    HOOK_DUR = 3.0
    LANG_DUR = 5.0
    CTA_DUR = 6.0
    total = HOOK_DUR + LANG_DUR * len(sections) + CTA_DUR  # 49s for 8 langs

    # 言語シーン HTML
    lang_scenes = []
    audio_tags = []
    for i, sec in enumerate(sections):
        start = HOOK_DUR + LANG_DUR * i
        size_cls = pick_phrase_size(sec["native"])
        phrase_cls = f"phrase {size_cls}".strip()
        lang_scenes.append(f'''
      <div id="{sec['id']}" class="clip scene {sec['id']}"
           data-start="{start:.1f}" data-duration="{LANG_DUR:.1f}" data-track-index="0">
        <div class="counter">{i+1:02d} / {len(sections):02d}</div>
        <div class="avatar-wrap">
          <img class="avatar" src="assets/{sec['audio_key']}.jpeg" alt="" />
          <div class="flag-badge">{sec['flag']}</div>
        </div>
        <div class="label">{sec['label']}</div>
        <div class="{phrase_cls}">{sec['native']}</div>
        <div class="kana">{sec['katakana']}</div>
        <div class="note">{sec['note']}</div>
      </div>''')

        audio_start = start + 1.2  # シーン登場後1.2秒で音声開始
        audio_tags.append(
            f'      <audio id="audio-{sec["audio_key"]}" src="assets/{sec["audio_key"]}.mp3" '
            f'data-start="{audio_start:.1f}" data-duration="3" data-track-index="3" data-volume="1"></audio>'
        )

    cta_start = HOOK_DUR + LANG_DUR * len(sections)

    # GSAP タイムライン
    lang_animations = []
    for i, sec in enumerate(sections):
        s = HOOK_DUR + LANG_DUR * i
        lang_animations.append(f'''
      tl.from("#{sec['id']} .counter", {{ opacity: 0, y: -20, duration: 0.4 }}, {s});
      tl.from("#{sec['id']} .avatar-wrap", {{ scale: 0.3, opacity: 0, duration: 0.7, ease: "back.out(1.5)" }}, {s + 0.1});
      tl.from("#{sec['id']} .flag-badge", {{ scale: 0, duration: 0.5, ease: "back.out(2)" }}, {s + 0.6});
      tl.from("#{sec['id']} .label", {{ opacity: 0, y: -20, duration: 0.4 }}, {s + 0.3});
      tl.from("#{sec['id']} .phrase", {{ opacity: 0, scale: 0.7, duration: 0.7, ease: "power3.out" }}, {s + 0.9});
      tl.from("#{sec['id']} .kana", {{ opacity: 0, y: 20, duration: 0.5 }}, {s + 1.4});
      tl.from("#{sec['id']} .note", {{ opacity: 0, x: -40, duration: 0.7, ease: "power2.out" }}, {s + 1.8});''')

    html = f'''<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&family=Noto+Sans+SC:wght@400;700;900&family=Noto+Sans+KR:wght@400;700;900&family=Noto+Sans+Thai:wght@400;700;900&family=Noto+Sans+Devanagari:wght@400;700;900&family=Noto+Sans+Arabic:wght@400;700;900&family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{
        margin: 0; width: 1080px; height: 1920px; overflow: hidden;
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        font-family: "Inter", "Noto Sans JP", sans-serif;
      }}
      #root {{ position: relative; width: 100%; height: 100%; }}
      .clip {{ position: absolute; width: 100%; }}
      .scene {{
        top: 0; left: 0; height: 100%;
        display: flex; flex-direction: column;
        justify-content: flex-start; align-items: center; text-align: center;
        padding: 220px 80px 80px;
      }}
      .counter {{
        position: absolute; top: 120px; left: 0; width: 100%; text-align: center;
        font-size: 42px; font-weight: 700; color: #60a5fa; letter-spacing: 6px;
      }}
      .avatar-wrap {{ position: relative; width: 420px; height: 420px; margin-bottom: 40px; }}
      .avatar {{
        width: 100%; height: 100%; border-radius: 50%; object-fit: cover;
        border: 8px solid #fbbf24; box-shadow: 0 0 50px rgba(251, 191, 36, 0.5);
      }}
      .flag-badge {{
        position: absolute; bottom: -10px; right: -10px;
        font-size: 100px; background: #0f172a;
        border-radius: 50%; width: 140px; height: 140px;
        display: flex; align-items: center; justify-content: center;
        line-height: 1; border: 6px solid #1e293b;
      }}
      .label {{
        font-size: 44px; font-weight: 700; color: #94a3b8; letter-spacing: 6px;
        margin-bottom: 20px; text-transform: uppercase;
      }}
      .phrase {{
        font-size: 116px; font-weight: 900; color: #ffffff;
        line-height: 1.1; margin-bottom: 24px;
        text-shadow: 0 4px 40px rgba(96, 165, 250, 0.4); padding: 0 20px;
      }}
      .phrase.small {{ font-size: 88px; }}
      .phrase.xsmall {{ font-size: 68px; }}
      .kana {{
        font-size: 50px; font-weight: 700; color: #fbbf24;
        margin-bottom: 36px; font-family: "Noto Sans JP", sans-serif;
      }}
      .note {{
        font-size: 38px; font-weight: 400; color: #cbd5e1;
        font-family: "Noto Sans JP", sans-serif;
        line-height: 1.5; max-width: 880px;
        padding: 24px 36px; border-left: 6px solid #fbbf24;
        background: rgba(30, 41, 59, 0.7); border-radius: 12px; text-align: left;
      }}
      /* ===== HOOK ===== */
      .hook-scene {{ padding-top: 0; justify-content: center; }}
      .hook-scene .hook-top {{
        font-size: 72px; font-weight: 900; color: #ffffff;
        background: linear-gradient(90deg, #b4822e 0%, #d4a13a 50%, #b4822e 100%);
        padding: 24px 48px; border-radius: 20px; margin-bottom: 60px;
        box-shadow: 0 6px 30px rgba(212, 161, 58, 0.5); letter-spacing: 2px;
      }}
      .hook-scene .hook-phrase {{
        font-size: 140px; font-weight: 900; color: #ffffff;
        font-family: "Noto Sans JP", sans-serif; line-height: 1.15;
        padding: 36px 60px; border: 6px solid #fbbf24; border-radius: 28px;
        margin-bottom: 60px; white-space: nowrap;
        box-shadow: 0 0 60px rgba(251, 191, 36, 0.5), inset 0 0 30px rgba(251, 191, 36, 0.15);
        text-shadow: 0 4px 40px rgba(251, 191, 36, 0.6);
      }}
      .hook-scene .hook-phrase.small {{ font-size: 108px; }}
      .hook-scene .hook-phrase.xsmall {{ font-size: 84px; }}
      .hook-scene .hook-bottom {{
        font-size: 60px; font-weight: 900; color: #fbbf24;
        letter-spacing: 4px; font-family: "Noto Sans JP", sans-serif;
      }}
      .hook-scene .hook-play {{
        margin-top: 40px; width: 100px; height: 100px;
        border: 5px solid #fbbf24; border-radius: 50%;
        background: #d4a13a; display: flex;
        align-items: center; justify-content: center; position: relative;
      }}
      .hook-scene .hook-play::after {{
        content: ""; border-left: 32px solid white;
        border-top: 22px solid transparent; border-bottom: 22px solid transparent;
        margin-left: 12px;
      }}
      /* ===== CTA ===== */
      .cta-scene {{ padding-top: 0; justify-content: center; }}
      .cta-scene .cta-headline {{
        font-size: 140px; font-weight: 900; color: #ffffff;
        font-family: "Noto Sans JP", sans-serif; margin-bottom: 40px;
        text-shadow: 0 4px 50px rgba(251, 191, 36, 0.7); letter-spacing: -2px;
      }}
      .cta-scene .cta-accent {{
        width: 200px; height: 8px;
        background: linear-gradient(90deg, transparent, #fbbf24, transparent);
        margin-bottom: 40px;
      }}
      .cta-scene .cta-sub {{
        font-size: 52px; font-weight: 700; color: #cbd5e1;
        font-family: "Noto Sans JP", sans-serif; margin-bottom: 50px;
      }}
      .cta-scene .cta-benefits {{
        font-size: 46px; font-weight: 400; color: #e2e8f0;
        font-family: "Noto Sans JP", sans-serif; line-height: 1.7; margin-bottom: 60px;
      }}
      .cta-scene .cta-btn {{
        font-size: 64px; font-weight: 900; color: #0f172a;
        background: linear-gradient(90deg, #fbbf24, #f59e0b);
        padding: 30px 70px; border-radius: 60px;
        font-family: "Noto Sans JP", sans-serif; margin-bottom: 40px;
        box-shadow: 0 8px 40px rgba(251, 191, 36, 0.6);
      }}
      .cta-scene .cta-url {{
        font-size: 52px; font-weight: 700; color: #60a5fa; letter-spacing: 2px;
      }}
      /* 保存誘発UI（バッジ・中央右ガイド）は削除。CTAの「今すぐ保存🔖」のみに集約 */
      .brand {{
        position: absolute; bottom: 80px; width: 100%; text-align: center;
        font-size: 34px; font-weight: 700; color: #60a5fa; letter-spacing: 6px;
      }}
      .ko .phrase {{ font-family: "Noto Sans KR", sans-serif; }}
      .zh .phrase {{ font-family: "Noto Sans SC", sans-serif; }}
      .th .phrase {{ font-family: "Noto Sans Thai", sans-serif; }}
      .hi .phrase {{ font-family: "Noto Sans Devanagari", sans-serif; }}
      .ar .phrase {{ font-family: "Noto Sans Arabic", sans-serif; direction: rtl; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main"
         data-start="0" data-duration="{total:.1f}" data-width="1080" data-height="1920">

      <!-- HOOK -->
      <div id="hook" class="clip scene hook-scene"
           data-start="0" data-duration="{HOOK_DUR:.1f}" data-track-index="0">
        <div class="hook-top">{hook['top']}</div>
        <div class="hook-phrase {pick_hook_phrase_size('「' + phrase + '」')}">「{phrase}」</div>
        <div class="hook-bottom">{hook['bottom']}</div>
        <div class="hook-play"></div>
      </div>
{''.join(lang_scenes)}

      <!-- CTA -->
      <div id="cta" class="clip scene cta-scene"
           data-start="{cta_start:.1f}" data-duration="{CTA_DUR:.1f}" data-track-index="0">
        <div class="cta-headline">今すぐ保存🔖</div>
        <div class="cta-accent"></div>
        <div class="cta-sub">旅先でスマホ見ながら発音できる</div>
        <div class="cta-benefits">
          旅行前に保存しておけば<br>
          現地でさっと取り出せる<br>
          8言語まるごと旅の味方🎧
        </div>
        <div class="cta-btn">🔖 保存して旅で使う</div>
        <div class="cta-url">sekai-kotoba.com</div>
      </div>

      <!-- ブランド -->
      <div id="brand" class="clip brand"
           data-start="0" data-duration="{total:.1f}" data-track-index="1">
        @sekakoto_dict
      </div>

      <!-- 音声トラック -->
{chr(10).join(audio_tags)}
    </div>

    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});

      // HOOK — フレーム0で要素が見えるよう opacity フェードは使わない（サムネ対策）
      tl.from("#hook .hook-top", {{ y: -40, duration: 0.5, ease: "back.out(1.7)" }}, 0);
      tl.from("#hook .hook-phrase", {{ scale: 0.7, duration: 0.7, ease: "back.out(1.5)" }}, 0.3);
      tl.from("#hook .hook-bottom", {{ y: 30, duration: 0.5 }}, 0.9);
      tl.from("#hook .hook-play", {{ scale: 0.3, rotation: -180, duration: 0.6, ease: "back.out(2)" }}, 1.2);
      tl.to("#hook .hook-phrase", {{ scale: 1.03, duration: 0.3, yoyo: true, repeat: 3, ease: "power1.inOut" }}, 1.5);
{''.join(lang_animations)}

      tl.from("#cta .cta-headline", {{ opacity: 0, scale: 0.6, duration: 0.7, ease: "back.out(1.7)" }}, {cta_start});
      tl.from("#cta .cta-accent", {{ scaleX: 0, duration: 0.5 }}, {cta_start + 0.6});
      tl.from("#cta .cta-sub", {{ opacity: 0, y: 30, duration: 0.5 }}, {cta_start + 0.9});
      tl.from("#cta .cta-benefits", {{ opacity: 0, y: 30, duration: 0.6 }}, {cta_start + 1.3});
      tl.from("#cta .cta-btn", {{ opacity: 0, scale: 0.7, duration: 0.6, ease: "back.out(1.5)" }}, {cta_start + 1.9});
      tl.to("#cta .cta-btn", {{ scale: 1.05, duration: 0.4, yoyo: true, repeat: 3, ease: "power1.inOut" }}, {cta_start + 2.5});
      tl.from("#cta .cta-url", {{ opacity: 0, y: 20, duration: 0.5 }}, {cta_start + 2.3});

      tl.from("#brand", {{ y: 20, duration: 1 }}, 0);

      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
'''
    return html


def render_hyperframes(project_dir: Path, output_mp4: Path) -> None:
    """hyperframes render を実行。"""
    cmd = ["npx", "hyperframes", "render", "--output", str(output_mp4)]
    r = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"hyperframes render failed: {r.stderr[-500:]}\n{r.stdout[-500:]}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--theme", required=True)
    p.add_argument("--hook", type=int, default=None, help="フックパターンindex (0-3)")
    p.add_argument("--no-reencode", action="store_true")
    args = p.parse_args()

    theme = args.theme
    print(f"📝 Parsing 記事サンプル/{theme}_外国語.md ...")
    phrase, sections = parse_article(theme)
    print(f"  phrase: {phrase} / {len(sections)}言語")

    tmp = TMP_DIR / theme
    tmp.mkdir(parents=True, exist_ok=True)

    # meta.json
    (tmp / "meta.json").write_text(
        f'{{"id": "{theme}_hf", "name": "{theme}_hf"}}', encoding="utf-8"
    )
    # hyperframes.json (必要)
    (tmp / "hyperframes.json").write_text('{"version": "1"}', encoding="utf-8")

    assets_dir = tmp / "assets"

    # TTS生成
    print("🎤 TTS生成中...")
    asyncio.run(gen_tts_all(phrase, sections, assets_dir))

    # アバターコピー
    print("👤 アバターコピー中...")
    copy_avatars(sections, assets_dir)

    # HTML生成
    print("🎨 HTML生成中...")
    html = build_html(theme, phrase, sections, hook_idx=args.hook)
    (tmp / "index.html").write_text(html, encoding="utf-8")

    # lint（returncodeで判定、"0 errors" 誤検出を避ける）
    print("🔍 lint...")
    r = subprocess.run(["npx", "hyperframes", "lint"], cwd=tmp, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"lint error:\n{r.stdout}\n{r.stderr}")

    # レンダ
    raw_mp4 = tmp / f"{theme}_raw.mp4"
    print(f"🎬 レンダ中... → {raw_mp4}")
    render_hyperframes(tmp, raw_mp4)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_mp4 = OUTPUT_DIR / f"{theme}.mp4"

    if args.no_reencode:
        shutil.copy(raw_mp4, out_mp4)
        print(f"✅ {out_mp4} ({out_mp4.stat().st_size/1024/1024:.1f}MB, no re-encode)")
    else:
        # IG再エンコード
        print("🎞️  IG再エンコード中...")
        from reencode_for_ig import reencode_for_ig
        reencode_for_ig(raw_mp4, out_mp4)
        print(f"✅ {out_mp4} ({out_mp4.stat().st_size/1024/1024:.1f}MB, IG-ready)")


if __name__ == "__main__":
    main()
