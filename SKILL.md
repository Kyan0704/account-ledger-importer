---
name: account-ledger-importer
description: "从账号注册/登录截图中自动提取平台名称、用户名、密码、手机号等信息，并录入飞书多维表格（账号台账）。当用户提供包含账号密码信息的截图/图片，并要求填入、记录、存储到多维表格或账号台账时使用。覆盖：图片信息提取、Base 表结构解析、字段映射、记录创建、截图附件上传、回读验证全流程。"
---

# 账号台账录入助手

## Overview

将账号注册/登录页面截图中的信息结构化提取，自动映射到飞书多维表格的账号台账字段并创建记录，同时将原始截图作为附件上传，最后回读验证。

## 使用前配置（重要）

本技能不绑定任何特定的多维表格，使用前需准备好你自己的飞书多维表格：

1. **创建账号台账表**：在飞书中新建多维表格，包含你需要的字段（平台名称、账号/用户名、登录密码、绑定手机号、会员类型、开通时间等）。字段名可自定义，技能会通过 `+field-list` 自动读取实际字段名进行映射。
2. **获取表格链接**：打开你的多维表格，复制浏览器地址栏中的 URL（格式如 `https://xxx.feishu.cn/base/xxxxxxxx`）。
3. **提供给 AI**：使用时将截图和你的多维表格 URL 一起发给 AI，技能会自动解析 URL 获取 `base_token` 和 `table_id`，无需手动填写。
4. **字段映射**：如果你的表字段名与常见命名不同，技能会按实际字段名匹配；参考 [references/field-mapping.md](references/field-mapping.md) 中的常见字段对照表进行调整。
5. **依赖**：需要已安装并登录 `lark-cli`（飞书命令行工具），且当前用户对目标多维表格有编辑权限。

## 工作流程

按以下步骤顺序执行，每步成功后再进入下一步。

### 1. 分析截图提取信息

用 `Read` 工具打开截图，提取以下信息（有则提取，无则标记）：

- 平台名称（页面标题/Logo/品牌名）
- 用户名/展示名称/登录账号
- 密码（明文，注意点击眼睛图标后的内容）
- 手机号（通常脱敏如 183****5175）
- 邮箱
- 会员类型/付费状态/到期时间（如有显示）

提取结果先在内部整理为字段-值映射，不要急于写入。

### 2. 解析多维表格

```bash
lark-cli base +url-resolve --url "<base_url>" --as user
lark-cli base +table-list --base-token "<base_token>" --as user
lark-cli base +field-list --base-token "<base_token>" --table-id "<table_id>" --as user
```

从 `+field-list` 结果中确认：
- 目标表的实际字段名和类型（以返回为准，不凭印象猜）
- 单选字段的已有选项（select 只能写已有选项）
- 附件字段的 field_id（用于上传截图）
- 只读字段（formula/auto_number/updated_at），写入时排除

字段映射的详细规则见 [references/field-mapping.md](references/field-mapping.md)。

### 3. 构造记录数据

根据截图信息和当前日期填充字段：

- **开通时间**：当前日期，格式 `YYYY-MM-DD 00:00:00`
- **会员类型**：无付费信息默认"免费"
- **付费金额**：免费注册填 0
- **自动续费**：默认"否"
- **账号状态**：默认"正常使用"
- **到期时间**：免费账号留空，仅截图明确显示时填写
- **绑定邮箱/手机号**：截图无则留空

只包含存储字段，不包含 formula/auto_number/updated_at 等只读字段。

### 4. 创建记录（PowerShell 关键步骤）

**必须使用辅助脚本写 JSON 文件，不要直接在命令行内联 JSON。** PowerShell 会剥离 JSON 中的双引号并导致中文编码错乱。

```bash
# 步骤 A：通过管道将字段 JSON 传给脚本，写入 UTF-8 文件（输出文件名）
# 注意：必须用管道 + --stdin，不要直接作为命令行参数（PowerShell 会剥离引号）
'{"平台名称":"模课","账号/用户名":"Kyan07","登录密码":"Xxyk040704","绑定手机号":"183****5175","会员类型":"免费","开通时间":"2026-09-06 00:00:00","付费金额":0,"自动续费":"否","账号状态":"正常使用"}' | python "<skill_dir>/scripts/write_record_json.py" --stdin

# 步骤 B：用 --% 停止解析符 + @文件 方式创建记录
lark-cli base +record-batch-create --base-token "<base_token>" --table-id "<table_id>" --as user --% --json @_record_payload.json
```

`--%` 之后的内容按字面传递，`@_record_payload.json` 指向当前工作目录下的文件。记录创建成功后从返回中取 `record_id`。

> 如果脚本路径含空格，用双引号包裹；脚本输出的文件名直接用于 `@文件名`。

### 5. 上传截图附件

如果目标表有 attachment 类型字段（如"备注"），将原始截图上传：

```bash
# 截图路径可能不在允许列表，先复制到当前工作目录
Copy-Item "<原始截图路径>" "screenshot_<平台名>.png" -Force
lark-cli base +record-upload-attachment --base-token "<base_token>" --table-id "<table_id>" --record-id "<record_id>" --field-id "<attachment_field_id>" --file "screenshot_<平台名>.png" --as user
```

lark-cli 的 `--file` 只允许当前工作目录、临时目录或 home 下 files 目录，不在范围内的文件必须先复制。

### 6. 回读验证

```bash
lark-cli base +record-get --base-token "<base_token>" --table-id "<table_id>" --record-id "<record_id>" --as user
```

逐项核对：平台名称、用户名、密码、手机号、开通时间、会员类型、账号状态、附件是否存在。全部正确后清理临时文件（`_record_payload.json`、复制的截图）。

## 关键坑点

| 问题 | 现象 | 解决 |
|---|---|---|
| PowerShell 剥离 JSON 引号 | `invalid character 'c' looking for beginning of object key string` | 用 write_record_json.py 写文件 + `--% --json @文件` |
| 中文乱码 | 字段值变成 `鍚嶇О` 等乱码 | 脚本已用 UTF-8 无 BOM 写入，不要手动转码 |
| @文件路径不在允许列表 | `outside the built-in allowlist` | 文件放在当前工作目录，用相对路径 `@文件名` |
| --file 路径不在允许列表 | `unsafe file path` | 先 Copy-Item 到工作目录再上传 |
| select 选项不存在 | 写入失败或自动新增选项 | 先 `+field-list` 确认已有选项，只写已有值 |
| 写了只读字段 | 返回 ignored_fields / READONLY | 排除 formula、auto_number、updated_at 字段 |
| 日期格式错误 | 1254015 字段值类型不匹配 | 用 `YYYY-MM-DD HH:mm:ss` 字符串 |

## 资源

- `scripts/write_record_json.py` — 将字段 JSON 写入 UTF-8 文件，解决 PowerShell 编码/引号问题
- `references/field-mapping.md` — 常见账号台账字段映射表、默认值、单选选项约定、只读字段清单
