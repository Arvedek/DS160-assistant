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
- 本地校验日期、护照签发/过期逻辑、英文字符提醒、F/J/M 签证 SEVIS
  提醒、petition-based worker 提醒、拒签史复核、安全问题复核
- 按 DS-160 主题分组的英文草稿
- 复制 Markdown、下载 JSON、本地保存报告
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

### 开发

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ds160_agent.py
```

项目结构：

- `ds160_agent/core.py`：字段、校验、草稿生成、保存逻辑
- `ds160_agent/web.py`：本地 HTTP 服务和 API
- `ds160_agent/static/`：浏览器界面
- `tests/test_ds160_agent.py`：核心校验测试

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
- Local validation for dates, passport chronology, English-character warnings,
  student/exchange visitor SEVIS reminders, petition-based worker reminders,
  refusal-history review, and security-answer review
- English draft table grouped by DS-160 topic
- Markdown copy, JSON download, and local report save
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

### Development

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ds160_agent.py
```

Project layout:

- `ds160_agent/core.py`: fields, validation, draft rendering, save logic
- `ds160_agent/web.py`: local HTTP server and API
- `ds160_agent/static/`: browser UI
- `tests/test_ds160_agent.py`: focused validation tests

### Safety Notes

Treat generated output as a preparation aid only. The applicant must personally
review every answer on the official DS-160 website before electronic signature
and submission. Store exported files carefully because DS-160 drafts contain
sensitive personal information.
