#!/usr/bin/env bash
# 打包技能为 zip，供 WorkBuddy 技能市场 / 分发使用。
# 用法: bash scripts/package.sh <技能目录> [输出zip路径]
#   技能目录 默认为当前目录
#   输出zip   默认 ../<技能名>.zip
set -euo pipefail

SRC="${1:-.}"
OUT="${2:-}"

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "错误：未在 $SRC 找到 SKILL.md，请确认传入的是技能根目录。" >&2
  exit 1
fi

NAME="$(basename "$(cd "$SRC" && pwd)")"
OUT="${OUT:-../${NAME}.zip}"

# 进入目录后用相对路径打包，避免 zip 内出现绝对路径
cd "$SRC"
rm -f "$OUT"
zip -r "$OUT" . -x "*.DS_Store" ".git/*" "__pycache__/*" "*.pyc" "node_modules/*" >/dev/null

# 把相对路径解析成绝对路径，方便用户定位
case "$OUT" in
  /*) ABS="$OUT" ;;
  *)  ABS="$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")" ;;
esac
echo "已打包: $ABS  ($(du -h "$ABS" | cut -f1))"
