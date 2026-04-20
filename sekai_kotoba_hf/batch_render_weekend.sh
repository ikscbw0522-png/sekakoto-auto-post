#!/bin/bash
# 週末用Hyperframes動画を5本順次レンダ。並列実行はChrome workerタイムアウトリスクあるので直列。

set -e
cd "$(dirname "$0")"

THEMES=("現金のみ" "クレジットカード" "両替したい" "安くして" "これはいくら")

START=$(date +%s)
echo "🎬 Batch render start: ${#THEMES[@]}本"
echo ""

for i in "${!THEMES[@]}"; do
  theme="${THEMES[$i]}"
  idx=$((i+1))
  echo "━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "[$idx/${#THEMES[@]}] $theme"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━"
  t_start=$(date +%s)
  if python3 render_theme.py --theme "$theme" 2>&1; then
    t_end=$(date +%s)
    echo "✅ $theme 完了 ($(( t_end - t_start ))秒)"
  else
    echo "❌ $theme 失敗"
  fi
  echo ""
done

END=$(date +%s)
TOTAL=$((END - START))
echo "━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 全テーマ完了: $((TOTAL / 60))分$((TOTAL % 60))秒"
ls -lh output/ | tail -10
