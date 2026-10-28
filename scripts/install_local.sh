#!/usr/bin/env bash
# 一键把本技能装进本地 WorkBuddy 技能库（~/.workbuddy/skills/<名>）。
# 用法: bash scripts/install_local.sh [技能目录]
#   技能目录 默认为本脚本所在目录的上一级（即技能根目录）
#
# 安全策略：已安装同名技能时【先备份再覆盖】，不直接 rm -rf。
# 备份目录形如 ~/.workbuddy/skills/<名>.bak.20261028-021500，确认无误后可自行删除。
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ $# -ge 1 ] && [ -n "${1:-}" ]; then SRC="$(cd "$1" && pwd)"; fi

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "错误：未在 $SRC 找到 SKILL.md，请确认路径是技能根目录。" >&2
  exit 1
fi

NAME="$(basename "$SRC")"
DEST="$HOME/.workbuddy/skills/$NAME"

if [ -d "$DEST" ]; then
  BACKUP="${DEST}.bak.$(date +%Y%m%d-%H%M%S)"
  echo "检测到已存在同名技能，先备份：$BACKUP"
  mv "$DEST" "$BACKUP"
fi

mkdir -p "$DEST"
cp -R "$SRC"/. "$DEST"/

echo "已安装到本地技能库：$DEST"
echo "技能名：$NAME —— 现在可以在 WorkBuddy 中直接触发。"
