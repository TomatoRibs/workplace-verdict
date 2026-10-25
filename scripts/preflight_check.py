#!/usr/bin/env python3
"""导出前内部自检：扫描交付物（zip 或目录）里的全部文本，命中禁词即 FAIL。

用法：
    python preflight_check.py <zip或目录> [<zip或目录> ...]

退出码：
    0 = 全部 PASS（允许导出）
    1 = 有命中（禁止导出，先改再跑）
    2 = 用法错误

规则：
    - 读内容而不是只看文件名；zip 会逐条解压读取。
    - 命中即判 FAIL，不做自动放行；确属误报必须人工改写句子绕开，不得加白名单。
    - 同时校验包里 SKILL.md 的 name 是否为 ASCII kebab-case
      （^[a-z0-9]+(-[a-z0-9]+)*$）。GitHub 仓库名与 WorkBuddy 市场标识名共用这一个值，
      填中文/大写会被市场打回（报错原文："仅支持小写字母、数字和连字符（kebab-case）"）。
"""
import sys
import os
import re
import zipfile

# ===DICT-BEGIN===
# 禁词表：分三类。命中任何一类都不允许导出。
# 词典必须完整列出才能查得出来，但自检时不该自己判自己为脏，
# 所以扫描前会把 BEGIN/END 之间的整段摘掉；本文件其余位置出现禁词照样判 FAIL。
BANNED = {
    # 一、来源痕迹类：任何暗示"从别处借来/抄来/仿来"的词
    "克隆": "来源痕迹",
    "复刻": "来源痕迹",
    "仿制": "来源痕迹",
    "仿自": "来源痕迹",
    "仿站": "来源痕迹",
    "扒站": "来源痕迹",
    "照搬": "来源痕迹",
    "借鉴": "来源痕迹",
    "模仿": "来源痕迹",
    "效仿": "来源痕迹",
    "原站": "来源痕迹",
    "原型站": "来源痕迹",
    "原网页": "来源痕迹",
    "原页面": "来源痕迹",
    "原产品": "来源痕迹",
    "原版": "来源痕迹",
    "目标页": "来源痕迹",
    "参考页": "来源痕迹",
    "行为层": "来源痕迹",
    # 二、来源声明类：哪怕本意是声明原创，只要出现来源字样就是负资产
    "原始创意": "来源声明",
    "创意来自": "来源声明",
    "灵感来自": "来源声明",
    "来源于": "来源声明",
    "参考自": "来源声明",
    "源自": "来源声明",
    "来源": "来源声明",
    "公开页面": "来源声明",
    "公开项目": "来源声明",
    "功能对等": "来源声明",
    "功能对齐": "来源声明",
    "对标": "来源声明",
    # 三、原站标识类：具体站点名/域名/专属词
    "marco79423": "原站标识",
    "anti-work": "原站标识",
    "Anti-Work": "原站标识",
}
# ===DICT-END===

TEXT_EXT = (
    ".md", ".markdown", ".html", ".htm", ".txt", ".sh", ".json",
    ".js", ".css", ".yml", ".yaml", ".py", ".csv",
)


def iter_texts(path):
    """产出 (相对路径, 文本内容)。支持目录与 zip。"""
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d != ".git"]
            for f in sorted(files):
                if f.lower().endswith(TEXT_EXT):
                    p = os.path.join(root, f)
                    try:
                        with open(p, encoding="utf-8", errors="ignore") as fh:
                            yield os.path.relpath(p, path), fh.read()
                    except OSError:
                        continue
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.lower().endswith(TEXT_EXT):
                    yield n, z.read(n).decode("utf-8", errors="ignore")


DICT_BLOCK = re.compile(r"# ===DICT-BEGIN===.*?# ===DICT-END===", re.S)


def strip_dict(text):
    """摘掉本脚本自身的禁词词典区段，避免自扫自判脏。

    只跳过词典本身这一区段；词典之外任何位置出现禁词，照旧命中。
    """
    return DICT_BLOCK.sub("[禁词词典区段，自检跳过]", text)


def scan(path):
    hits = []
    for name, txt in iter_texts(path):
        txt = strip_dict(txt)
        for kw, cat in BANNED.items():
            for m in re.finditer(re.escape(kw), txt):
                line_no = txt.count("\n", 0, m.start()) + 1
                lines = txt.splitlines()
                snippet = lines[line_no - 1].strip()[:140] if line_no - 1 < len(lines) else ""
                hits.append((name, line_no, kw, cat, snippet))
    return hits


# name 必须是 ASCII kebab-case：小写字母/数字，单个连字符分隔，无中文、无大写、无下划线、无首尾连字符。
# GitHub 仓库名与 WorkBuddy 市场标识名共用这一个值，所以按严的来。
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def check_names(path):
    """校验包里每个 SKILL.md 的 frontmatter name 是否合规，返回问题列表。"""
    problems = []
    for name, txt in iter_texts(path):
        if not name.lower().endswith("skill.md"):
            continue
        parts = txt.split("---")
        if len(parts) < 3:
            problems.append((name, "缺少 frontmatter（文件头两行 --- 之间）"))
            continue
        fm = parts[1]
        m = re.search(r"^name:\s*(.+)$", fm, re.M)
        val = m.group(1).strip().strip("\"'") if m else ""
        if not val:
            problems.append((name, "缺少 name 字段"))
        elif not KEBAB.match(val):
            problems.append((name, "name=%r 不合规，必须匹配 ^[a-z0-9]+(-[a-z0-9]+)*$（小写字母/数字/单个连字符，不能有中文或大写）" % val))
    return problems


def main():
    targets = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not targets:
        print("用法: python preflight_check.py <zip或目录> [<zip或目录> ...]")
        return 2

    failed = False
    for t in targets:
        print("== " + t)
        if not os.path.exists(t):
            print("  ERROR 路径不存在")
            failed = True
            continue
        hits = scan(t)
        if hits:
            failed = True
            for name, line_no, kw, cat, snippet in hits:
                print("  FAIL [%s] %s:%d 命中「%s」 -> %s" % (cat, name, line_no, kw, snippet))
        else:
            print("  PASS 未命中任何禁词")

        nprob = check_names(t)
        if nprob:
            failed = True
            for nm, msg in nprob:
                print("  FAIL [命名] %s -> %s" % (nm, msg))
        else:
            print("  PASS name 为合规 kebab-case（可直接建 GitHub 仓库 / 上架市场）")

    print("")
    print("结论：" + ("FAIL —— 先改，禁止导出" if failed else "PASS —— 允许导出"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
