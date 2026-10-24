#!/usr/bin/env bash
# 一键把技能推送到 GitHub。
# 优先用 gh（GitHub CLI）；未安装 gh 时回退到 git push（需已配置 remote 与凭证）。
#
# 用法: bash scripts/upload_github.sh <技能目录> [仓库名] [private|public]
#   <技能目录> 默认为当前目录
#   [仓库名]   默认取技能目录名；若以 owner/repo 形式给出则直接推到该仓库
#   [private|public]  默认 private（仅 gh 新建仓库时生效）
#
# 前置条件（满足其一即可真正“一键”）:
#   A. 已 `gh auth login` 登录，或环境变量 GITHUB_TOKEN 已设置；
#   B. 该目录已是 git 仓库且已配置好带凭证的 origin remote。
# 都不满足时，脚本会打印清晰的下一步指引，不会静默失败。
set -euo pipefail

SRC="${1:-.}"
REPO="${2:-}"
VIS="${3:-private}"

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "错误：未在 $SRC 找到 SKILL.md。" >&2
  exit 1
fi

NAME="$(basename "$(cd "$SRC" && pwd)")"
REPO="${REPO:-$NAME}"
cd "$SRC"

# 确保是 git 仓库
if [ ! -d .git ]; then
  git init -q
  git config user.email >/dev/null 2>&1 || git config user.email "skill-bot@local"
  git config user.name  >/dev/null 2>&1 || git config user.name  "Skill Bot"
fi

# 忽略常见的本地垃圾
grep -qxF '.DS_Store' .gitignore 2>/dev/null || echo '.DS_Store' >> .gitignore
git add -A
if git diff --cached --quiet; then
  echo "没有需要提交的改动。"
else
  git commit -q -m "feat: $NAME 初始版本" || true
fi

# 优先 gh
if command -v gh >/dev/null 2>&1; then
  echo "检测到 gh，使用 GitHub CLI 上传..."
  if ! gh auth status >/dev/null 2>&1; then
    if [ -n "${GITHUB_TOKEN:-}" ]; then
      echo "GITHUB_TOKEN 已设置，尝试用 token 推送..."
      git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://${GITHUB_TOKEN}@github.com/${REPO}.git"
      git push -u origin "$(git rev-parse --abbrev-ref HEAD)" && echo "已推送: https://github.com/${REPO}" && exit 0
    fi
    echo "gh 未登录。请先运行: gh auth login" >&2
    echo "或设置环境变量 GITHUB_TOKEN 后重试。" >&2
    exit 1
  fi
  if git remote get-url origin >/dev/null 2>&1; then
    BR="$(git rev-parse --abbrev-ref HEAD)"
    git push -u origin "$BR" && echo "已推送: $(git remote get-url origin)" && exit 0
  fi
  # 新建仓库并推送
  VIS_FLAG="--$VIS"
  gh repo create "$REPO" "$VIS_FLAG" --source . --push \
    && echo "已创建并推送: https://github.com/$(gh repo view "$REPO" --json owner,name -q '.owner.login + "/" + .name')" \
    && exit 0
fi

# 回退：直接用 git push（需已有带凭证的 remote）
echo "未检测到 gh，尝试 git push（需已配置带凭证的 origin remote）..."
if git remote get-url origin >/dev/null 2>&1; then
  BR="$(git rev-parse --abbrev-ref HEAD)"
  git push -u origin "$BR" && echo "已推送: $(git remote get-url origin)" && exit 0
else
  echo "既没有 gh，也没有配置 git remote。请二选一：" >&2
  echo "  1) 安装并登录 gh:  brew install gh && gh auth login" >&2
  echo "  2) 手动添加 remote: git remote add origin <url> && git push -u origin main" >&2
  exit 1
fi
