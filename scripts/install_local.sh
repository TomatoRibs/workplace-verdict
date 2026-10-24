#!/usr/bin/env bash
# 一键把技能装进本地 WorkBuddy 技能库（即 ~/.workbuddy/skills/<名>）。
# 装完后即可在 WorkBuddy 中直接触发使用。
# 用法: bash scripts/install_local.sh <技能目录>
set -euo pipefail

SRC="${1:-.}"
if [ ! -f "$SRC/SKILL.md" ]; then
  echo "错误：未在 $SRC 找到 SKILL.md。" >&2
  exit 1
fi

NAME="$(basename "$(cd "$SRC" && pwd)")"
DEST="$HOME/.workbuddy/skills/$NAME"

if [ -d "$DEST" ]; then
  echo "检测到已存在 $DEST，先移除旧版本..."
  rm -rf "$DEST"
fi

cp -R "$SRC" "$DEST"
echo "已安装到本地技能库: $DEST"
echo "技能名: $NAME  —— 现在可以在 WorkBuddy 中使用了。"
