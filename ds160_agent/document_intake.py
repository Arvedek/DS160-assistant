from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any
from uuid import uuid4

from .core import FIELD_BY_ID, FIELDS


AI_MODEL_ENV = "DS160_AI_MODEL"
AI_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_MODEL = "gpt-4o-mini"
MAX_TEXT_CHARS = 12000
MAX_FILE_BYTES = 8 * 1024 * 1024
CODEX_HANDOFF_FORMAT = "ds160-codex-handoff-v1"
CODEX_MATERIALS_HANDOFF_FORMAT = "ds160-codex-materials-handoff-v1"
CODEX_RESULT_FORMAT = "ds160-codex-candidates-v1"


def analyze_document(payload: dict[str, Any]) -> dict[str, Any]:
    document = payload.get("document") if isinstance(payload.get("document"), dict) else {}
    current_data = payload.get("currentData") if isinstance(payload.get("currentData"), dict) else {}
    text = str(document.get("text") or "").strip()
    filename = str(document.get("filename") or "uploaded-document")
    mime_type = str(document.get("mimeType") or "text/plain")
    data_b64 = str(document.get("dataBase64") or "")
    evidence = _evidence_record(filename, mime_type, bool(data_b64), bool(text))

    if _should_use_ai(payload, document):
        ai_result = _analyze_with_openai(document, current_data)
        ai_result["evidence"] = evidence
        return ai_result

    candidates = annotate_candidates(extract_candidates_from_text(text), current_data)
    notes = []
    if data_b64 and not text:
        notes.append("File was attached as evidence, but no AI key is configured and no extractable text was provided.")
    if not candidates and text:
        notes.append("No strong field candidates were found. Try pasting clearer OCR text or enable AI analysis.")
    return {
        "mode": "local_text",
        "model": None,
        "evidence": evidence,
        "candidates": candidates,
        "notes": notes,
        "rawTextPreview": text[:1200],
    }


def ai_status() -> dict[str, Any]:
    return {
        "enabled": bool(os.environ.get(AI_KEY_ENV)),
        "model": os.environ.get(AI_MODEL_ENV, DEFAULT_MODEL),
        "provider": "openai-responses",
        "supports": ["image", "pdf", "text"],
    }


def build_codex_handoff(payload: dict[str, Any]) -> dict[str, Any]:
    document = payload.get("document") if isinstance(payload.get("document"), dict) else {}
    current_data = payload.get("currentData") if isinstance(payload.get("currentData"), dict) else {}
    text = str(document.get("text") or "").strip()
    filename = str(document.get("filename") or "uploaded-document")
    mime_type = str(document.get("mimeType") or "text/plain")
    has_file = bool(document.get("dataBase64"))
    non_empty = {field.id: current_data.get(field.id, "") for field in FIELDS if current_data.get(field.id)}
    field_catalog = [{"fieldId": field.id, "label": field.label, "section": field.section} for field in FIELDS]
    prompt = (
        "You are helping extract DS-160 draft facts from user-provided materials. "
        "Use only the attached files/images/PDFs and the text below. Do not invent facts. "
        "Return JSON only in this exact shape:\n\n"
        "{\n"
        f'  "format": "{CODEX_RESULT_FORMAT}",\n'
        '  "candidates": [\n'
        '    {"fieldId": "passport_number", "value": "E12345678", "confidence": 0.86, "source": "passport image", "requiresReview": true}\n'
        "  ],\n"
        '  "notes": ["short note if needed"]\n'
        "}\n\n"
        "Allowed field IDs are listed in the handoff package. If a field is uncertain, include it only with low confidence and requiresReview=true. "
        "For security/background questions, extract only explicit statements; do not infer a final answer."
    )
    handoff = {
        "format": CODEX_HANDOFF_FORMAT,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "document": {
            "filename": filename,
            "mimeType": mime_type,
            "hasAttachedFile": has_file,
            "textPreview": text[:MAX_TEXT_CHARS],
        },
        "currentDraft": non_empty,
        "fieldCatalog": field_catalog,
        "instructions": prompt,
    }
    return {
        "mode": "codex_handoff",
        "handoff": handoff,
        "prompt": prompt + "\n\nHANDOFF PACKAGE:\n" + json.dumps(handoff, ensure_ascii=False, indent=2),
        "notes": [
            "Attach the original image/PDF files directly in Codex when possible.",
            "Paste the Codex JSON result back into the app to review and apply candidates.",
        ],
    }


def build_codex_materials_handoff(payload: dict[str, Any], materials_bundle: dict[str, Any]) -> dict[str, Any]:
    current_data = payload.get("currentData") if isinstance(payload.get("currentData"), dict) else {}
    non_empty = {field.id: current_data.get(field.id, "") for field in FIELDS if current_data.get(field.id)}
    field_catalog = [{"fieldId": field.id, "label": field.label, "section": field.section} for field in FIELDS]
    prompt = (
        "TASK: Review a local DS-160 applicant materials folder and return structured candidates for the local app. "
        "Step 1: Inspect the materials manifest and read every accessible file under materialsRoot. "
        "Step 2: Extract only facts that appear in source materials or the current draft; never infer facts from silence. "
        "Step 3: Cross-check documents for conflicts in names, dates, passport details, visa class, school/employer, U.S. contact, travel plans, and prior visa/travel history. "
        "Step 4: Assign confidence based on source quality: 0.90+ for direct official-document matches, 0.75-0.89 for clear secondary evidence, below 0.75 for partial/ambiguous evidence. "
        "Step 5: Mark requiresReview=true for conflicts, low confidence, security/background fields, refusal/overstay/arrest/drug/immigration history, or any value copied from a non-official source. "
        "If you are running in the same Codex workspace, read files from the provided materialsRoot path directly. "
        "If a file cannot be read in your environment, add a note asking the user to attach that specific file instead of guessing. "
        "Return JSON only in this exact shape:\n\n"
        "{\n"
        f'  "format": "{CODEX_RESULT_FORMAT}",\n'
        '  "candidates": [\n'
        '    {"fieldId": "passport_number", "value": "E12345678", "confidence": 0.9, "source": "materials/passport.jpg", "requiresReview": true}\n'
        "  ],\n"
        '  "notes": ["conflict, missing source, unreadable file, or final review note"]\n'
        "}\n\n"
        "Allowed field IDs are listed in fieldCatalog. Prefer source labels that include the material relative path. "
        "Do not include candidates for fields that are not in fieldCatalog."
    )
    handoff = {
        "format": CODEX_MATERIALS_HANDOFF_FORMAT,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "materialsRoot": materials_bundle["root"],
        "materials": materials_bundle,
        "currentDraft": non_empty,
        "fieldCatalog": field_catalog,
        "instructions": prompt,
    }
    return {
        "mode": "codex_materials_handoff",
        "handoff": handoff,
        "prompt": prompt + "\n\nMATERIALS HANDOFF PACKAGE:\n" + json.dumps(handoff, ensure_ascii=False, indent=2),
        "notes": [
            "This package is optimized for reviewing every supported file in materials/ together.",
            "Text files include previews; image and PDF files should be read from the local workspace or attached in Codex.",
        ],
    }


def parse_codex_result(payload: dict[str, Any]) -> dict[str, Any]:
    current_data = payload.get("currentData") if isinstance(payload.get("currentData"), dict) else {}
    raw = payload.get("result")
    if isinstance(raw, str):
        parsed = _parse_ai_json(raw)
    elif isinstance(raw, dict):
        parsed = raw
    else:
        raise ValueError("Codex result must be a JSON object or JSON text.")
    if parsed.get("format") != CODEX_RESULT_FORMAT:
        raise ValueError(f"Codex result must include format={CODEX_RESULT_FORMAT}.")
    candidates = annotate_candidates(_normalize_ai_candidates(parsed.get("candidates", [])), current_data)
    notes = parsed.get("notes") if isinstance(parsed.get("notes"), list) else []
    return {
        "mode": "codex_result",
        "model": "codex-handoff",
        "evidence": _evidence_record("codex-handoff-result", "application/json", False, True),
        "candidates": candidates,
        "notes": notes,
        "rawTextPreview": json.dumps(parsed, ensure_ascii=False)[:1200],
    }


def extract_candidates_from_text(text: str) -> list[dict[str, Any]]:
    normalized = _normalize_text(text)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(field_id: str, value: str, confidence: float, source: str) -> None:
        cleaned = _clean_value(value)
        if not cleaned or field_id in seen:
            return
        field = FIELD_BY_ID.get(field_id)
        if not field:
            return
        candidates.append(
            {
                "fieldId": field_id,
                "fieldLabel": field.label,
                "value": cleaned,
                "confidence": confidence,
                "source": source,
                "requiresReview": confidence < 0.82,
            }
        )
        seen.add(field_id)

    for field_id, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE | re.MULTILINE)
            if match:
                add(field_id, match.group(1), 0.82, "label_match")
                break

    date_patterns = {
        "date_of_birth": [r"(?:date of birth|birth date|dob|出生日期)[:：\s]+([0-9]{4}[-/年.][0-9]{1,2}[-/月.][0-9]{1,2})"],
        "passport_issue_date": [r"(?:date of issue|issue date|签发日期)[:：\s]+([0-9]{4}[-/年.][0-9]{1,2}[-/月.][0-9]{1,2})"],
        "passport_expiration_date": [r"(?:date of expiry|expiry date|expiration date|有效期至)[:：\s]+([0-9]{4}[-/年.][0-9]{1,2}[-/月.][0-9]{1,2})"],
        "arrival_date": [r"(?:arrival date|intended arrival|抵达日期)[:：\s]+([0-9]{4}[-/年.][0-9]{1,2}[-/月.][0-9]{1,2})"],
    }
    for field_id, patterns in date_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if match:
                add(field_id, _normalize_date(match.group(1)), 0.86, "date_label_match")
                break

    passport_match = re.search(r"\b([EGP][0-9A-Z]{7,9})\b", normalized)
    if passport_match:
        add("passport_number", passport_match.group(1), 0.72, "passport_pattern")

    email_match = re.search(r"([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})", normalized, flags=re.IGNORECASE)
    if email_match:
        add("email", email_match.group(1), 0.8, "email_pattern")

    phone_match = re.search(r"(\+\d{1,3}[\s\-]?(?:\d[\s\-]?){7,16})", normalized)
    if phone_match:
        add("phone", phone_match.group(1), 0.68, "phone_pattern")

    return candidates


def annotate_candidates(candidates: list[dict[str, Any]], current_data: dict[str, Any]) -> list[dict[str, Any]]:
    annotated = []
    for candidate in candidates:
        field_id = str(candidate.get("fieldId") or "")
        value = str(candidate.get("value") or "").strip()
        existing = str(current_data.get(field_id) or "").strip()
        action = "fill_empty"
        conflict = False
        if existing and _same_answer(existing, value):
            action = "same_value"
        elif existing and value:
            action = "replace_conflict"
            conflict = True
        next_candidate = dict(candidate)
        next_candidate["currentValue"] = existing
        next_candidate["action"] = action
        next_candidate["conflict"] = conflict
        if conflict:
            next_candidate["requiresReview"] = True
        next_candidate["quality"] = _candidate_quality(next_candidate)
        annotated.append(next_candidate)
    return annotated


def _candidate_quality(candidate: dict[str, Any]) -> dict[str, Any]:
    confidence = float(candidate.get("confidence") or 0)
    source = str(candidate.get("source") or "").strip()
    reasons = []
    if candidate.get("conflict"):
        reasons.append("conflicts_with_current_draft")
    if candidate.get("requiresReview"):
        reasons.append("requires_human_review")
    if confidence < 0.75:
        reasons.append("low_confidence")
    elif confidence < 0.9:
        reasons.append("medium_confidence")
    if not source or source in {"ai_document_analysis", "label_match", "passport_pattern", "email_pattern", "phone_pattern"}:
        reasons.append("weak_or_generic_source")
    if candidate.get("action") == "same_value":
        reasons.append("already_matches_current_draft")

    if candidate.get("conflict") or confidence < 0.75:
        tier = "needs_review"
        recommendation = "Review source before applying."
    elif candidate.get("requiresReview") or confidence < 0.9 or "weak_or_generic_source" in reasons:
        tier = "check_source"
        recommendation = "Good candidate, but verify source."
    elif candidate.get("action") == "same_value":
        tier = "already_confirmed"
        recommendation = "Matches the current draft."
    else:
        tier = "ready"
        recommendation = "Likely safe to apply after normal applicant review."

    return {
        "tier": tier,
        "score": round(max(0, min(100, confidence * 100 - (18 if candidate.get("conflict") else 0) - (8 if "weak_or_generic_source" in reasons else 0)))),
        "reasons": reasons,
        "recommendation": recommendation,
    }


FIELD_PATTERNS: dict[str, list[str]] = {
    "surname": [r"(?:surname|family name|last name|姓)[:：\s]+([A-Z\u4e00-\u9fff][A-Z\u4e00-\u9fff \t'-]{1,60})"],
    "given_names": [r"(?:given names?|first name|名)[:：\s]+([A-Z\u4e00-\u9fff][A-Z\u4e00-\u9fff \t'-]{1,60})"],
    "native_name": [r"(?:native name|chinese name|中文名|姓名)[:：\s]+([\u4e00-\u9fff]{2,20})"],
    "place_of_birth": [r"(?:place of birth|birth place|出生地)[:：\s]+([A-Z\u4e00-\u9fff][^\n\r]{1,120})"],
    "sex": [r"(?:sex|gender|性别)[:：\s]+(Male|Female|M|F|男|女)"],
    "nationality": [r"(?:nationality|citizenship|国籍)[:：\s]+([A-Z\u4e00-\u9fff][^\n\r]{1,80})"],
    "passport_issue_country": [r"(?:issuing country|country of issue|签发国家)[:：\s]+([A-Z\u4e00-\u9fff][^\n\r]{1,80})"],
    "passport_issue_place": [r"(?:place of issue|issuing place|签发地点)[:：\s]+([A-Z\u4e00-\u9fff][^\n\r]{1,80})"],
    "visa_class": [r"(?:visa class|visa type|签证类型)[:：\s]+([A-Z0-9/\-]{1,20})"],
    "purpose_of_trip": [r"(?:purpose of trip|travel purpose|旅行目的)[:：\s]+([^\n\r]{2,140})"],
    "length_of_stay": [r"(?:length of stay|duration|停留时间)[:：\s]+([^\n\r]{2,80})"],
    "payer": [r"(?:payer|paying for trip|费用支付)[:：\s]+([^\n\r]{2,120})"],
    "home_address": [r"(?:home address|residential address|家庭地址|住址)[:：\s]+([^\n\r]{6,180})"],
    "us_contact_name": [r"(?:u\.?s\.? contact name|contact name|美国联系人)[:：\s]+([^\n\r]{2,120})"],
    "us_contact_address": [r"(?:u\.?s\.? contact address|美国联系人地址)[:：\s]+([^\n\r]{6,180})"],
    "employer_or_school": [r"(?:employer|school name|company|雇主|学校)[:：\s]+([^\n\r]{2,140})"],
    "employer_or_school_address": [r"(?:employer address|school address|单位地址|学校地址)[:：\s]+([^\n\r]{6,180})"],
    "current_occupation": [r"(?:occupation|job title|职位|职业)[:：\s]+([^\n\r]{2,80})"],
    "monthly_income": [r"(?:monthly income|salary|月收入)[:：\s]+([^\n\r]{2,80})"],
    "father_name": [r"(?:father'?s? full name|father name|父亲姓名)[:：\s]+([^\n\r]{2,80})"],
    "mother_name": [r"(?:mother'?s? full name|mother name|母亲姓名)[:：\s]+([^\n\r]{2,80})"],
}


def _should_use_ai(payload: dict[str, Any], document: dict[str, Any]) -> bool:
    if payload.get("useAi") is False:
        return False
    if not os.environ.get(AI_KEY_ENV):
        return False
    return bool(document.get("dataBase64") or document.get("text"))


def _analyze_with_openai(document: dict[str, Any], current_data: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get(AI_KEY_ENV)
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    filename = str(document.get("filename") or "document")
    mime_type = str(document.get("mimeType") or "text/plain")
    data_b64 = str(document.get("dataBase64") or "")
    text = str(document.get("text") or "").strip()
    if data_b64:
        _validate_file_payload(data_b64)

    content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": _ai_prompt(text, current_data),
        }
    ]
    if data_b64:
        if mime_type == "application/pdf":
            content.insert(0, {"type": "input_file", "filename": filename, "file_data": data_b64})
        elif mime_type.startswith("image/"):
            content.insert(0, {"type": "input_image", "image_url": f"data:{mime_type};base64,{data_b64}"})
        else:
            content[0]["text"] += f"\n\nUnsupported file MIME type for AI vision: {mime_type}. Analyze text only."

    request_payload = {
        "model": os.environ.get(AI_MODEL_ENV, DEFAULT_MODEL),
        "input": [{"role": "user", "content": content}],
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - explicit OpenAI API call
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"OpenAI document analysis failed: {exc.code} {body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"OpenAI document analysis failed: {exc.reason}") from exc

    output_text = _extract_response_text(raw)
    parsed = _parse_ai_json(output_text)
    candidates = annotate_candidates(_normalize_ai_candidates(parsed.get("candidates", [])), current_data)
    notes = parsed.get("notes") if isinstance(parsed.get("notes"), list) else []
    return {
        "mode": "ai",
        "model": request_payload["model"],
        "candidates": candidates,
        "notes": notes,
        "rawTextPreview": output_text[:1200],
    }


def _ai_prompt(text: str, current_data: dict[str, Any]) -> str:
    field_list = "\n".join(f"- {field.id}: {field.label}" for field in FIELDS)
    current = {field.id: current_data.get(field.id, "") for field in FIELDS if current_data.get(field.id)}
    return (
        "You are extracting applicant facts for a local DS-160 drafting assistant. "
        "Return JSON only, with no markdown. Do not invent facts. If a value is uncertain, lower confidence and set requiresReview true. "
        "Never decide final security/background answers; only extract what the document explicitly says.\n\n"
        "Allowed fields:\n"
        f"{field_list}\n\n"
        "JSON shape:\n"
        '{"candidates":[{"fieldId":"passport_number","value":"E12345678","confidence":0.88,'
        '"source":"passport image","requiresReview":true}],"notes":["..."]}\n\n'
        f"Existing non-empty draft data for context:\n{json.dumps(current, ensure_ascii=False)}\n\n"
        f"User-provided OCR or notes, if any:\n{text[:MAX_TEXT_CHARS]}"
    )


def _normalize_ai_candidates(items: Any) -> list[dict[str, Any]]:
    candidates = []
    if not isinstance(items, list):
        return candidates
    for item in items:
        if not isinstance(item, dict):
            continue
        field_id = str(item.get("fieldId") or "")
        field = FIELD_BY_ID.get(field_id)
        value = _clean_value(str(item.get("value") or ""))
        if not field or not value:
            continue
        try:
            confidence = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        candidates.append(
            {
                "fieldId": field_id,
                "fieldLabel": field.label,
                "value": value,
                "confidence": max(0.0, min(1.0, confidence)),
                "source": str(item.get("source") or "ai_document_analysis")[:140],
                "requiresReview": bool(item.get("requiresReview", confidence < 0.85)),
            }
        )
    return candidates


def _parse_ai_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
    raise ValueError("AI response did not contain valid JSON.")


def _extract_response_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(str(content.get("text") or ""))
    if parts:
        return "\n".join(parts).strip()
    if payload.get("output_text"):
        return str(payload["output_text"]).strip()
    return json.dumps(payload, ensure_ascii=False)


def _validate_file_payload(data_b64: str) -> None:
    try:
        size = len(base64.b64decode(data_b64, validate=True))
    except ValueError as exc:
        raise ValueError("Uploaded file data is not valid base64.") from exc
    if size > MAX_FILE_BYTES:
        raise ValueError("Uploaded file is too large for this MVP. Limit is 8 MB.")


def _evidence_record(filename: str, mime_type: str, has_file: bool, has_text: bool) -> dict[str, Any]:
    return {
        "id": f"doc-{uuid4().hex[:10]}",
        "filename": filename,
        "mimeType": mime_type,
        "hasFile": has_file,
        "hasText": has_text,
        "receivedAt": datetime.now(timezone.utc).isoformat(),
    }


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n")).strip()


def _clean_value(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value.replace("\r", "").strip(" \t\n:：,，;；"))


def _same_answer(left: str, right: str) -> bool:
    return re.sub(r"\s+", " ", left).strip().casefold() == re.sub(r"\s+", " ", right).strip().casefold()


def _normalize_date(value: str) -> str:
    text = value.replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-").replace(".", "-")
    match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text.strip())
    if not match:
        return value
    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"
