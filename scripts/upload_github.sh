#!/usr/bin/env bash
# 一键把技能推送到 GitHub（本地保存后紧接着执行）。
# 走 gh（GitHub CLI）建仓并推送；需先 gh auth login，本脚本不代登录。
#
# 用法:
#   bash scripts/upload_github.sh <技能目录> <英文仓库名> [public|private] \
#        [--desc "仓库描述"] [--topics "a,b"]
#
#   <英文仓库名> 必须只含 字母 / 数字 / . / _ / - 。
#   GitHub 不收中文仓库名，所以不能用中文技能目录名直接建仓——
#   填第 3 步定好的 ASCII slug（如 moyu-qiantong、workplace-verdict）。
set -euo pipefail

DESC=""; TOPICS=""; ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --desc)     DESC="$2";     shift 2 ;;
    --topics)   TOPICS="$2";   shift 2 ;;
    --desc=*)   DESC="${1#*=}";     shift ;;
    --topics=*) TOPICS="${1#*=}";   shift ;;
    *) ARGS+=("$1"); shift ;;
  esac
done

SRC="${ARGS[0]:-.}"
SLUG="${ARGS[1]:-}"
VIS="${ARGS[2]:-public}"

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "错误：未在 $SRC 找到 SKILL.md。" >&2
  exit 1
fi
if [ -z "$SLUG" ]; then
  echo "错误：缺少英文仓库名（第 2 个参数）。" >&2
  echo "GitHub 仓库名只认 字母/数字/./_/-，中文目录名不能直接当仓库名。" >&2
  echo "用法：bash scripts/upload_github.sh <技能目录> <英文slug> public" >&2
  exit 1
fi
if ! printf '%s' "$SLUG" | grep -qE '^[A-Za-z0-9._-]+$'; then
  echo "错误：仓库名「$SLUG」不合法，只可含 字母/数字/./_/-，不能含中文或空格。" >&2
  exit 1
fi
if ! command -v gh >/dev/null 2>&1; then
  echo "错误：未安装 gh。请安装并登录：" >&2
  echo "  winget install --id GitHub.cli -e --source winget" >&2
  echo "  gh auth login" >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "错误：gh 未登录。请先在终端执行 gh auth login（需本人授权）。" >&2
  exit 1
fi

NAME="$(basename "$(cd "$SRC" && pwd)")"
cd "$SRC"

if [ ! -d .git ]; then
  git init -q
fi
git config user.email >/dev/null 2>&1 || git config user.email "skill-bot@local"
git config user.name  >/dev/null 2>&1 || git config user.name  "番茄排骨"
grep -qxF '.DS_Store' .gitignore 2>/dev/null || echo '.DS_Store' >> .gitignore

git add -A
if git diff --cached --quiet; then
  echo "没有需要提交的改动。"
else
  git commit -q -m "feat: ${NAME} 初始版本"
fi

OWNER="$(gh api user --jq .login)"

# 确保仓库存在（不带 --push，推送单独做，便于失败时切 API 方案）
if ! gh repo view "${OWNER}/${SLUG}" >/dev/null 2>&1; then
  CREATE_ARGS=(repo create "$SLUG" "--${VIS}")
  if [ -n "$DESC" ]; then
    CREATE_ARGS+=(--description "$DESC")
  fi
  gh "${CREATE_ARGS[@]}"
  if [ -n "$TOPICS" ]; then
    gh repo edit "${OWNER}/${SLUG}" --add-topic "$TOPICS"
  fi
  echo "已创建仓库: https://github.com/${OWNER}/${SLUG}"
fi

# 对齐到仓库默认分支
DEFAULT_BR="$(gh repo view "${OWNER}/${SLUG}" --json defaultBranchRef -q '.defaultBranchRef.name' 2>/dev/null || true)"
if [ -z "$DEFAULT_BR" ]; then
  DEFAULT_BR="main"   # 全新空仓库取不到默认分支，兜底 main
fi
git branch -M "$DEFAULT_BR" 2>/dev/null || true

git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/${OWNER}/${SLUG}.git"

# 推送：优先 git push；不通（代理只放行 api.github.com 时）改用 API 提交
if git push -u origin "$DEFAULT_BR"; then
  echo "已推送: https://github.com/${OWNER}/${SLUG}"
else
  echo "git push 不通（多为网络/代理限制），改用 GitHub API 提交..."
  HELPER="$(cd "$(dirname "$0")" && pwd)/push_via_api.py"
  if [ -f "$HELPER" ]; then
    python "$HELPER" "${OWNER}/${SLUG}" "$(pwd)" "feat: ${NAME} 初始版本" "$DEFAULT_BR"
  else
    echo "错误：git push 失败，且同目录未找到 push_via_api.py" >&2
    exit 1
  fi
fi
