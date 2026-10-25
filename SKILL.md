---
name: workplace-verdict
display_name: 同事判刑书
display_name_en: Workplace Verdict
author: 番茄排骨
description: 本地单文件的解压玩具网页——选同事的离谱行为，生成一份带印章的「判刑书」和竖版分享海报。零上传、可离线、可一键存图转发。当用户要做职场解压、吐槽同事、生成趣味判刑海报，或提到「同事判刑书」时启用。
description_zh: 本地单文件的解压玩具网页——选同事的离谱行为，生成一份带印章的「判刑书」和竖版分享海报。零上传、可离线、可一键存图转发。
description_en: An offline single-file stress-relief toy: pick a coworker's absurd behaviour, get a stamped "verdict" sheet plus a vertical shareable poster. No upload, fully offline, one-click PNG export.
category: productivity
version: 1.0.0
license: 个人非商用
---

# 同事判刑书

原创单文件 HTML 解压玩具。用户挑选同事的恼人行为，网页在本地即时生成一份「判刑书」加竖版海报，全程零上传。

## 何时使用
- 用户想做职场解压、吐槽同事、生成趣味判刑海报
- 用户明确提到「同事判刑书」

## 交付物
技能自带完整网页：`assets/workplace-verdict.html`（单文件、零依赖、可离线双击打开）。

## 用法
当用户要使用本技能时：
1. 将 `assets/workplace-verdict.html` 复制到用户工作区（或用户指定目录）。
2. 用 `present_files` 打开预览，或直接告知用户双击即可使用。

网页内置：5 步向导（案发现场 → 犯罪土壤 → 减刑事由 → 被告登记 → 当庭宣判）、本地判决生成、Canvas 竖版海报（可下载 PNG / 复制图片 / 复制全文 / 生成分享链接）。全部在浏览器端完成，不经过任何服务器。

## 注意
- 纯属虚构解压玩具，不构成任何实名评价、职场建议或人身攻击。
- 不引用任何外部站点、框架或素材，全部原生实现。
