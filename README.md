# DS160 Assistant

Local MVP for preparing a DS-160 draft before manually completing the official
U.S. nonimmigrant visa application.

The app is intentionally human-in-the-loop. It helps collect answers, checks
required fields and common consistency issues, and generates Markdown/JSON
drafts. It does not submit, sign, bypass captchas, or make legal decisions for
the applicant.

## Features

- Browser-based local data entry
- Required-field completeness tracking
- Local validation for dates, passport chronology, English-character warnings,
  student/exchange visitor SEVIS reminders, petition-based worker reminders,
  refusal-history review, and security-answer review
- English draft table grouped by DS-160 topic
- Markdown copy, JSON download, and local report save
- No cloud API dependency in the MVP

## Quick Start

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

## Development

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ds160_agent.py
```

Project layout:

- `ds160_agent/core.py`: fields, validation, draft rendering, save logic
- `ds160_agent/web.py`: local HTTP server and API
- `ds160_agent/static/`: browser UI
- `tests/test_ds160_agent.py`: focused validation tests

## Safety Notes

Treat generated output as a preparation aid only. The applicant must personally
review every answer on the official DS-160 website before electronic signature
and submission. Store exported files carefully because DS-160 drafts contain
sensitive personal information.
