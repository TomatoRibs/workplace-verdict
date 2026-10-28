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

cd "$SRC"
rm -f "$OUT"

if command -v zip >/dev/null 2>&1; then
  zip -r "$OUT" . -x "*.DS_Store" ".git/*" "__pycache__/*" "*.pyc" "node_modules/*" >/dev/null
else
  echo "未检测到 zip 命令，改用 python 打包..."
  python3 - "$OUT" <<'PY'
import os, zipfile, sys
out = sys.argv[1]
skip = {'.DS_Store'}
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f in skip or f == os.path.basename(out):
                continue
            p = os.path.join(root, f)
            z.write(p, p)
PY
fi

case "$OUT" in
  /*) ABS="$OUT" ;;
  *)  ABS="$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")" ;;
esac
echo "已打包: $ABS  ($(du -h "$ABS" | cut -f1))"
