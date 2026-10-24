# 上传到 WorkBuddy 技能市场（公开上架）

> 说明：WorkBuddy 技能市场**没有公开的自动发布 API**，必须通过开放平台的网页界面提交 + 审核。下面是一键“本地安装”之外的**公开上架**流程。脚本 `install_local.sh` 已完成“装进本地技能库”这一步；本文件补齐“对外发布”这一步。

## 两种方式

### 方式 A：在 WorkBuddy 客户端内打包并提交
1. 在 WorkBuddy 中对智能体说：「帮我把 `<技能名>` 这个 Skill 打包」。
2. 客户端会自动校验 frontmatter 并生成 zip。
3. 进入【专家 · 技能 · 连接器】→【技能】→【技能市场】→ 右上角【添加技能】/【创建技能】。
4. 上传 zip 或粘贴 SKILL.md，填写展示信息，提交审核。

### 方式 B：开放平台网页提交
1. 打开 <https://open.workbuddy.cn>。
2. 注册 / 登录开发者账号（公开发布通常需要实名）。
3. 进入【技能】→【添加技能】→【创建技能】。
4. 上传 `scripts/package.sh` 生成的 zip，或粘贴 SKILL.md。
5. 填写以下信息（可复用技能内 `02_方法论与宣传口径.md`）：
   - 展示名（display_name / display_name_en）
   - 简介（description_zh / description_en）
   - 分类（category，按平台下拉选项选）
   - 图标 / 封面图（建议用页面截图或演示视频首帧）
   - 长介绍与演示（演示视频可用录屏产物）
   - 版本说明 / changelog
6. 提交 → 安全扫描 + 人工审核 → 上架。

## 上架前必查
- `SKILL.md` 的 frontmatter 字段齐全：`name` / `display_name` / `description_zh` / `description_en` / `category` / `version` / `author` / `license`。
- **`author` 必填**，且须为真实作者 / 团队名（本地安装可留占位，公开发布必须填）。
- `category` 必须落在平台枚举内（如 `productivity` / `developer-tools` / 其他），以平台下拉为准。
- 技能内不得含网络请求、密钥、外部脚本（本技能产出的页面均为离线单文件，应可直接过安全扫描）。
- 对外文案须保留免责声明：非标准化量表、未做信效度检验、不做临床诊断。
