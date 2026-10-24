#!/usr/bin/env python3
"""把整个目录作为一次提交推到 GitHub（走 api.github.com）。

用途：某些环境下 git push 到 github.com 不通（代理只放行 api.github.com），
此时改用 GitHub Git Data API 直接建 blob/tree/commit 并更新分支引用。

用法：
    python push_via_api.py <owner/repo> <目录> [提交信息] [分支]

依赖：gh 已登录（用 gh auth token 取令牌）；仅用 Python 标准库。
"""
import sys
import os
import json
import base64
import subprocess
import urllib.request
import urllib.error

API = "https://api.github.com"


def get_token():
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def api(method, path, payload=None, tok=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "workbuddy-skill-uploader")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:400]
        raise SystemExit("API 失败 %s %s -> %s %s" % (method, path, e.code, body))


def collect(directory):
    out = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in sorted(files):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, directory).replace(os.sep, "/")
            out.append((rel, p))
    return out


def main():
    if len(sys.argv) < 3:
        print("用法: python push_via_api.py <owner/repo> <目录> [提交信息] [分支]")
        return 2
    repo = sys.argv[1]
    directory = sys.argv[2]
    message = sys.argv[3] if len(sys.argv) > 3 else "feat: 初始版本"
    branch_arg = sys.argv[4] if len(sys.argv) > 4 else ""

    if not os.path.isdir(directory):
        print("错误：目录不存在 " + directory)
        return 1

    tok = get_token()
    info = api("GET", "/repos/" + repo, None, tok)
    branch = branch_arg or info.get("default_branch") or "main"

    items = collect(directory)
    if not items:
        print("错误：目录为空，没有可提交的文件")
        return 1

    parent = None
    try:
        ref = api("GET", "/repos/%s/git/ref/heads/%s" % (repo, branch), None, tok)
        parent = ref["object"]["sha"]
    except SystemExit:
        parent = None

    if parent is None:
        rel0, path0 = items[0]
        with open(path0, "rb") as fh:
            c0 = fh.read()
        boot = api("PUT", "/repos/%s/contents/%s" % (repo, rel0), {
            "message": message,
            "content": base64.b64encode(c0).decode("ascii"),
            "branch": branch,
        }, tok)
        parent = boot["commit"]["sha"]
        print("  初始化空仓库 -> " + rel0)

    tree = []
    for rel, path in items:
        with open(path, "rb") as fh:
            blob_bytes = fh.read()
        mode = "100755" if rel.endswith(".sh") else "100644"
        blob = api("POST", "/repos/%s/git/blobs" % repo, {
            "content": base64.b64encode(blob_bytes).decode("ascii"),
            "encoding": "base64",
        }, tok)
        tree.append({"path": rel, "mode": mode, "type": "blob", "sha": blob["sha"]})
        print("  blob  " + rel)

    payload = {"tree": tree}
    if parent:
        payload["base_tree"] = parent
    tree_obj = api("POST", "/repos/%s/git/trees" % repo, payload, tok)

    commit_payload = {"message": message, "tree": tree_obj["sha"]}
    if parent:
        commit_payload["parents"] = [parent]
    commit = api("POST", "/repos/%s/git/commits" % repo, commit_payload, tok)

    if parent:
        api("PATCH", "/repos/%s/git/refs/heads/%s" % (repo, branch), {"sha": commit["sha"]}, tok)
    else:
        api("POST", "/repos/%s/git/refs" % repo, {
            "ref": "refs/heads/" + branch,
            "sha": commit["sha"],
        }, tok)

    print("已提交 %s -> %s@%s" % (commit["sha"][:7], repo, branch))
    print("https://github.com/%s" % repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
