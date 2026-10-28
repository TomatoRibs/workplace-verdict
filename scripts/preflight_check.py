#!/usr/bin/env python3
"""导出前内部自检：禁词 + frontmatter 合法性 + 命名，三项一起过，命中即 FAIL。

用法：
    python preflight_check.py <zip或目录> [<zip或目录> ...]

退出码：
    0 = 全部 PASS（允许导出）
    1 = 有命中（禁止导出，先改再跑）
    2 = 用法错误

检查项（任何一项不过都禁止导出）：
    1. 禁词：读文件内容而不是只看文件名；zip 会逐条解压读取。
    2. frontmatter：必须是合法 YAML，且必需字段齐全、值不被 YAML 悄悄吃掉。
       —— 市场解析失败最常见的原因是"未加引号的值里出现冒号+空格"，
          例如 `description_en: a toy: pick ...`，YAML 会把 `pick` 当成新键，
          整包报 `mapping values are not allowed in this context`，链接口都进不去。
       —— 字段既允许写在顶层，也允许写在 `metadata:` 块内；校验前会先把顶层
          metadata 展平到一层再查完整性（顶层优先），两种写法一视同仁。
    3. 命名：SKILL.md 的 name 必须是 ASCII kebab-case
       （^[a-z0-9]+(-[a-z0-9]+)*$）。GitHub 仓库名与 WorkBuddy 市场标识名共用这一个值。

规则：
    - 命中即判 FAIL，不做自动放行；确属误报必须人工改写句子绕开，不得加白名单。
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


# ---------------------------------------------------------------------------
# frontmatter 校验
# ---------------------------------------------------------------------------

# name 必须是 ASCII kebab-case：小写字母/数字，单个连字符分隔，无中文、无大写、无下划线、无首尾连字符。
# GitHub 仓库名与 WorkBuddy 市场标识名共用这一个值，所以按严的来。
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# 必需字段：缺了市场表单填不满，直接判 FAIL。
REQUIRED_KEYS = ("name", "display_name", "description")
# 建议字段：缺了不拦，但会提醒。
SUGGESTED_KEYS = ("display_name_en", "description_zh", "description_en", "category", "version", "author", "license")

KEY_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s+(.*))?$")


def split_frontmatter(txt):
    """取出 --- 之间的 frontmatter 文本。返回 (fm, err)。

    不用 str.split('---')：正文里的分隔线会把切分点弄错。
    """
    s = txt.lstrip("\ufeff")
    lines = s.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "缺少 frontmatter（文件第一行必须是 ---）"
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), None
    return None, "frontmatter 未闭合（找不到第二行 ---）"


def fallback_scan(fm):
    """不依赖 PyYAML 的严格扫描，专抓"未加引号的值里带冒号+空格"这类坑。

    返回 [(行号, 说明)]，行号以 frontmatter 第一行为 1（与市场报错口径一致）。
    """
    problems = []
    seen = {}
    nested_seen = {}          # metadata: 块内的键，供 flatten 后查字段用
    block_scalar = False
    nested_ok = False
    for i, line in enumerate(fm.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))

        if block_scalar:
            if indent > 0:
                continue
            block_scalar = False

        if indent > 0:
            if nested_ok and (line.lstrip().startswith("-") or KEY_LINE.match(line.strip())):
                m2 = KEY_LINE.match(line.strip())
                if m2 and m2.group(1) not in nested_seen:
                    nested_seen[m2.group(1)] = i
                continue
            problems.append((i, "缩进错误：该行有缩进，但上一行不是块标量（>- / |）也不是空值键"))
            continue

        m = KEY_LINE.match(line)
        if not m:
            problems.append((i, "不是合法的「键: 值」行，YAML 无法解析"))
            continue
        key, val = m.group(1), (m.group(2) or "")
        if key in seen:
            problems.append((i, "键重复：%s（第 %d 行已出现过）" % (key, seen[key])))
        seen[key] = i

        if val[:1] in (">", "|"):
            block_scalar = True
            nested_ok = False
            continue
        if val == "":
            nested_ok = True
            continue
        nested_ok = False

        if val[0] in ("'", '"'):
            if len(val) < 2 or val[-1] != val[0]:
                problems.append((i, "引号未闭合：%s 的值以 %s 开头但没在行尾闭合" % (key, val[0])))
            continue

        if ": " in val:
            col = val.index(": ") + 1
            problems.append((
                i,
                "值里有「冒号+空格」（列 %d 附近），YAML 会把它当新键 -> 报 "
                "mapping values are not allowed in this context。"
                "改法：去掉冒号改写句子，或用 >- 块标量。别用单引号包（英文撇号会提前闭合）。" % col,
            ))
        if val.startswith(("-", "?", ":", "@", "`")):
            problems.append((i, "值以 YAML 保留字符 %r 开头，需要用引号包起来" % val[0]))

    for k in REQUIRED_KEYS:
        if k not in seen and k not in nested_seen:
            problems.append((0, "缺少必需字段：%s（顶层与 metadata: 块内都没有）" % k))
    return problems


def flatten_metadata(data):
    """把顶层 `metadata:` 块展平到一层，供字段完整性校验使用。

    市场目前同时接受两种写法：
        display_name: 上司图鉴                 ← 顶层
        metadata:
          display_name: 上司图鉴               ← 嵌套
    两者语义相同，校验时不该区别对待。顶层键优先（冲突时以顶层为准）。

    注意：只影响"查字段"，不回写用户文件、不改变 name 的取值来源。
    """
    if not isinstance(data, dict):
        return data
    meta = data.get("metadata")
    if not isinstance(meta, dict):
        return data
    flat = dict(meta)
    for k, v in data.items():
        if k != "metadata":
            flat[k] = v
    return flat


def yaml_scan(fm):
    """优先用 PyYAML 做权威解析；没装则退到内置严格扫描。

    返回 (problems, engine, data)。解析失败时 data 为 None。
    """
    try:
        import yaml  # noqa
    except ImportError:
        return fallback_scan(fm), "内置扫描", None

    try:
        data = yaml.safe_load(fm)
    except Exception as e:
        detail = str(e).replace("\n", " | ")[:260]
        return [(0, "YAML 解析失败：%s" % detail)], "PyYAML", None
    if not isinstance(data, dict):
        return [(0, "frontmatter 解析结果不是键值对（mapping）")], "PyYAML", None
    data = flatten_metadata(data)
    problems = []
    for k in REQUIRED_KEYS:
        if k not in data:
            problems.append((0, "缺少必需字段：%s" % k))
    return problems, "PyYAML", data


def check_frontmatter(path):
    """校验每个 SKILL.md 的 frontmatter。返回 (问题列表, 引擎集合)。"""
    problems = []
    engines = set()
    for name, txt in iter_texts(path):
        if not name.lower().endswith("skill.md"):
            continue
        fm, err = split_frontmatter(txt)
        if err:
            problems.append((name, 0, err))
            continue
        probs, engine, data = yaml_scan(fm)
        engines.add(engine)
        for line_no, msg in probs:
            problems.append((name, line_no, msg))

        if engine == "PyYAML":
            if data is None:
                continue
            val = str(data.get("name", "")).strip()
            if not val:
                problems.append((name, 0, "缺少 name 字段"))
            elif not KEBAB.match(val):
                problems.append((name, 0, "name=%r 不合规，必须匹配 ^[a-z0-9]+(-[a-z0-9]+)*$"
                                        "（小写字母/数字/单个连字符，不能有中文或大写）" % val))
            missing = [k for k in SUGGESTED_KEYS if k not in data]
            if missing:
                print("  WARN [字段] %s 建议补齐市场字段：%s" % (name, "、".join(missing)))
        else:
            m = re.search(r"^name:[ \t]*(.+)$", fm, re.M) or \
                re.search(r"^[ \t]+name:[ \t]*(.+)$", fm, re.M)
            val = m.group(1).strip().strip("\"'") if m else ""
            if val and not KEBAB.match(val):
                problems.append((name, 0, "name=%r 不合规，必须匹配 ^[a-z0-9]+(-[a-z0-9]+)*$" % val))
            missing = [k for k in SUGGESTED_KEYS if not re.search(r"^\s*%s:" % k, fm, re.M)]
            if missing:
                print("  WARN [字段] %s 建议补齐市场字段：%s" % (name, "、".join(missing)))
    return problems, engines


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

        fprob, engines = check_frontmatter(t)
        if fprob:
            failed = True
            for nm, line_no, msg in fprob:
                loc = ("%s:%d" % (nm, line_no)) if line_no else nm
                print("  FAIL [frontmatter] %s -> %s" % (loc, msg))
        else:
            print("  PASS frontmatter 为合法 YAML、必需字段齐全、name 为合规 kebab-case"
                  "（校验引擎：%s）" % ("+".join(sorted(engines)) if engines else "无 SKILL.md"))

    print("")
    print("结论：" + ("FAIL —— 先改，禁止导出" if failed else "PASS —— 允许导出"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
