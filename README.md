# DS160 Assistant

[中文](#中文说明) | [English](#english)

## 中文说明

DS160 Assistant 是一个本地 MVP，用来在手动填写美国非移民签证
DS-160 官方表格之前，先整理和检查申请草稿。

这个应用刻意设计为 human-in-the-loop。它可以帮助收集答案、检查必填项
和常见一致性问题，并生成 Markdown/JSON 草稿。它不会提交表格、不会代替
申请人电子签名、不会绕过验证码，也不会为申请人做法律判断。

### 功能

- 浏览器本地录入资料
- 必填项完成度追踪
- Product Cockpit 工作台：显示 readiness score、当前阶段和下一步最佳动作
- 标准化 dossier JSON 契约，包含 case ID、分区状态、字段映射、证据目录和安全边界
- 本地校验日期、护照签发/过期逻辑、英文字符提醒、F/J/M 签证 SEVIS
  提醒、petition-based worker 提醒、拒签史复核、安全问题复核
- Security/background 分项复核，不再只依赖一段自由文本
- 按 DS-160 主题分组的英文草稿
- 复制 Markdown、下载 dossier JSON、本地保存报告
- 浏览器端加密导出/导入，使用 Web Crypto AES-GCM 和 PBKDF2
- 不记录完整个人信息的本地活动日志
- 示例 B1/B2 dossier：`sample_data/china_b1b2_sample.json`
- 文档输入面板支持图片、PDF、文本、JSON 上传；可粘贴 OCR/复制文本并抽取候选字段
- 配置 `OPENAI_API_KEY` 后，图片/PDF 会通过 OpenAI Responses API 做视觉/文件分析；未配置时使用本地文本规则抽取
- Codex Handoff 模式：没有 API key 时，可以生成分析包，复制到 Codex 对话，Codex 返回候选字段 JSON 后再导入本地审阅
- 候选字段会标记填空、重复值或替换冲突；冲突项默认不自动勾选
- Final Review Packet 汇总缺失必填项、风险复核项、材料清单和最终检查
- MVP 不依赖云端 API

### 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ds160_agent.web --port 8780
```

打开：

```text
http://127.0.0.1:8780
```

保存的报告会写入：

```text
outputs/ds160/
```

如果要启用图片/PDF AI 分析：

```powershell
$env:OPENAI_API_KEY="你的 key"
$env:DS160_AI_MODEL="gpt-4o-mini"
.\.venv\Scripts\python.exe -m ds160_agent.web --port 8780
```

### Codex 模式流程

没有 OpenAI API key 时，推荐用 Codex Handoff：

1. 在右侧“文档输入”里选择图片/PDF/TXT/JSON，或粘贴 OCR/复制文本。
2. 在“Codex 模式”点击 `1. 生成 Codex 分析包`。
3. 点击 `2. 复制给 Codex`。
4. 在 Codex 对话里上传原始图片/PDF，并粘贴分析包。
5. 让 Codex 只返回 `ds160-codex-candidates-v1` JSON。
6. 把 JSON 粘贴回 `3. 把 Codex 返回的候选字段 JSON 粘贴到这里`。
7. 点击 `解析 Codex 结果`，再勾选候选字段并应用到表单。

推荐给 Codex 的材料组合：

- 护照照片或扫描件
- I-20 / DS-2019 / petition receipt
- 邀请信、行程单、酒店或联系人信息
- 工作证明、在读证明、收入证明
- 旧签证、拒签/行政处理说明、旅行记录文本

### 开发

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ds160_agent.py
```

项目结构：

- `ds160_agent/core.py`：字段、校验、草稿生成、保存逻辑
- `ds160_agent/dossier.py`：dossier 契约、字段映射、分区 readiness
- `ds160_agent/audit.py`：隐私友好的本地审计日志
- `ds160_agent/document_intake.py`：文档上传、AI 分析、本地文本候选字段抽取
- `ds160_agent/web.py`：本地 HTTP 服务和 API
- `ds160_agent/static/`：浏览器界面
- `tests/test_ds160_agent.py`：核心校验测试
- `tests/test_document_intake.py`：文档输入和文本抽取测试
- `sample_data/china_b1b2_sample.json`：示例资料

### 安全说明

生成结果只能作为准备材料。申请人必须在官方 DS-160 网站上逐项检查所有答案，
并亲自完成电子签名和提交。导出的文件包含敏感个人信息，请谨慎保存和分享。

## English

DS160 Assistant is a local MVP for preparing a DS-160 draft before manually
completing the official U.S. nonimmigrant visa application.

The app is intentionally human-in-the-loop. It helps collect answers, checks
required fields and common consistency issues, and generates Markdown/JSON
drafts. It does not submit, sign, bypass captchas, or make legal decisions for
the applicant.

### Features

- Browser-based local data entry
- Required-field completeness tracking
- Product Cockpit with readiness score, current stage, and next best action
- Standard dossier JSON contract with case ID, section readiness, field map,
  evidence catalog, and safety boundaries
- Local validation for dates, passport chronology, English-character warnings,
  student/exchange visitor SEVIS reminders, petition-based worker reminders,
  refusal-history review, and security-answer review
- Structured security/background review fields instead of one free-text-only
  note
- English draft table grouped by DS-160 topic
- Markdown copy, dossier JSON download, and local report save
- Browser-side encrypted export/import using Web Crypto AES-GCM and PBKDF2
- Privacy-conscious local activity log that avoids full personal answers
- Sample B1/B2 dossier: `sample_data/china_b1b2_sample.json`
- Document intake panel for image, PDF, text, and JSON uploads; pasted OCR or
  copied text can be converted into candidate fields
- With `OPENAI_API_KEY`, images/PDFs are analyzed through the OpenAI Responses
  API; without it, local text heuristics still work
- Codex Handoff mode: generate a package for this Codex chat, paste back the
  candidate JSON, then review and apply fields locally
- Candidate fields are labeled as fill-empty, duplicate, or replace-conflict;
  conflicts are not selected by default
- Final Review Packet with missing required fields, risk items, source
  checklist, and final checks
- No cloud API dependency in the MVP

### Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ds160_agent.web --port 8780
```

Open:

```text
http://127.0.0.1:8780
```

Saved reports are written under:

```text
outputs/ds160/
```

To enable AI analysis for images/PDFs:

```powershell
$env:OPENAI_API_KEY="your key"
$env:DS160_AI_MODEL="gpt-4o-mini"
.\.venv\Scripts\python.exe -m ds160_agent.web --port 8780
```

### Codex Handoff Flow

When you do not have an OpenAI API key:

1. In Document Intake, choose an image/PDF/TXT/JSON or paste OCR/copied text.
2. In Codex Mode, click `1. Generate Codex package`.
3. Click `2. Copy for Codex`.
4. In the Codex chat, upload the original image/PDF and paste the package.
5. Ask Codex to return only `ds160-codex-candidates-v1` JSON.
6. Paste that JSON into the Codex result box.
7. Click `Parse Codex result`, then review and apply selected candidates.

### Development

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ds160_agent.py
```

Project layout:

- `ds160_agent/core.py`: fields, validation, draft rendering, save logic
- `ds160_agent/dossier.py`: dossier contract, field map, section readiness
- `ds160_agent/audit.py`: privacy-conscious local audit log
- `ds160_agent/document_intake.py`: document upload, AI analysis, local text
  candidate extraction
- `ds160_agent/web.py`: local HTTP server and API
- `ds160_agent/static/`: browser UI
- `tests/test_ds160_agent.py`: focused validation tests
- `tests/test_document_intake.py`: document intake and text extraction tests
- `sample_data/china_b1b2_sample.json`: sample data

### Safety Notes

Treat generated output as a preparation aid only. The applicant must personally
review every answer on the official DS-160 website before electronic signature
and submission. Store exported files carefully because DS-160 drafts contain
sensitive personal information.
