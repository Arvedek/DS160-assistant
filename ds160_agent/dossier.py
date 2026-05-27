from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from .core import FIELD_BY_ID, FIELDS, SECTIONS, Issue


DOSSIER_FORMAT = "ds160-assistant-dossier-v1"


def build_dossier(data: dict[str, str], issues: list[Issue]) -> dict[str, Any]:
    """Build a portable dossier contract from flat form answers."""
    return {
        "format": DOSSIER_FORMAT,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "caseId": _case_id(data),
        "data": dict(data),
        "sections": build_section_status(data, issues),
        "fieldMap": build_field_map(data, issues),
        "evidenceCatalog": build_evidence_catalog(data),
        "safety": {
            "humanSignatureRequired": True,
            "officialSubmissionAutomated": False,
            "containsSensitivePersonalData": True,
        },
    }


def build_section_status(data: dict[str, str], issues: list[Issue]) -> list[dict[str, Any]]:
    by_section: dict[str, list[Issue]] = {}
    for issue in issues:
        by_section.setdefault(issue.section, []).append(issue)

    statuses: list[dict[str, Any]] = []
    for section in SECTIONS:
        section_fields = [field for field in FIELDS if field.section == section["id"]]
        required = [field for field in section_fields if field.required]
        answered = [field for field in required if data.get(field.id)]
        section_issues = by_section.get(section["id"], [])
        error_count = sum(1 for issue in section_issues if issue.level == "error")
        warning_count = sum(1 for issue in section_issues if issue.level == "warning")
        review_count = sum(1 for issue in section_issues if issue.level == "review")
        status = "ready"
        if error_count:
            status = "blocked"
        elif warning_count or review_count or len(answered) < len(required):
            status = "needs_review"
        statuses.append(
            {
                "sectionId": section["id"],
                "title": section["title"],
                "requiredAnswered": len(answered),
                "requiredTotal": len(required),
                "errorCount": error_count,
                "warningCount": warning_count,
                "reviewCount": review_count,
                "status": status,
            }
        )
    return statuses


def build_field_map(data: dict[str, str], issues: list[Issue]) -> list[dict[str, Any]]:
    issue_by_field: dict[str, list[Issue]] = {}
    for issue in issues:
        issue_by_field.setdefault(issue.field_id, []).append(issue)

    mapped = []
    for field in FIELDS:
        field_issues = issue_by_field.get(field.id, [])
        value = data.get(field.id, "")
        status = _field_status(value, field.required, field_issues)
        mapped.append(
            {
                "fieldId": field.id,
                "section": field.section,
                "label": field.label,
                "value": value or None,
                "status": status,
                "confidence": _confidence(status, field_issues),
                "evidenceRefs": _evidence_refs(field.section),
                "notes": [issue.message for issue in field_issues],
            }
        )
    return mapped


def build_evidence_catalog(data: dict[str, str]) -> list[dict[str, str]]:
    catalog = [
        {"id": "passport", "kind": "passport", "description": "Passport bio page and passport document details."},
        {"id": "identity", "kind": "identity", "description": "Applicant identity and civil records."},
        {"id": "travel", "kind": "travel_plan", "description": "Itinerary, invitation, hotel, or school/petition context."},
        {"id": "contact", "kind": "contact", "description": "Applicant contact and U.S. contact information."},
        {"id": "family", "kind": "family", "description": "Family names and relationship context."},
        {"id": "work_education", "kind": "employment_education", "description": "Employment, income, school, and training records."},
        {"id": "travel_history", "kind": "travel_history", "description": "Prior U.S. travel, visa, refusal, and international travel records."},
        {"id": "security", "kind": "security_review", "description": "Applicant-reviewed security and background answers."},
    ]
    if data.get("sevis_id") or data.get("school_program_address"):
        catalog.append({"id": "sevis", "kind": "student_exchange", "description": "SEVIS and school/program information."})
    if data.get("petition_receipt"):
        catalog.append({"id": "petition", "kind": "petition", "description": "Petition receipt or approval notice."})
    return catalog


def dossier_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://local.ds160-assistant/dossier.schema.json",
        "title": "DS160 Assistant Dossier",
        "type": "object",
        "required": ["format", "generatedAt", "caseId", "data", "sections", "fieldMap", "evidenceCatalog"],
        "properties": {
            "format": {"const": DOSSIER_FORMAT},
            "generatedAt": {"type": "string"},
            "caseId": {"type": "string"},
            "data": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    field.id: {"type": "string"}
                    for field in FIELDS
                },
            },
            "sections": {"type": "array"},
            "fieldMap": {"type": "array"},
            "evidenceCatalog": {"type": "array"},
            "safety": {"type": "object"},
        },
    }


def render_dossier_json(dossier: dict[str, Any]) -> str:
    return json.dumps(dossier, ensure_ascii=False, indent=2)


def _case_id(data: dict[str, str]) -> str:
    surname = _slug(data.get("surname") or "APPLICANT")
    given = _slug(data.get("given_names") or "")
    birth = data.get("date_of_birth", "").replace("-", "")
    passport_tail = (data.get("passport_number") or "")[-4:]
    parts = [part for part in (surname, given, birth, passport_tail) if part]
    return "-".join(parts) or "DS160-DRAFT"


def _field_status(value: str, required: bool, issues: list[Issue]) -> str:
    if any(issue.level == "error" for issue in issues) or (required and not value):
        return "blocked"
    if any(issue.level == "review" for issue in issues):
        return "needs_review"
    if any(issue.level == "warning" for issue in issues):
        return "warning"
    if value:
        return "ready"
    return "optional_missing"


def _confidence(status: str, issues: list[Issue]) -> float:
    if status == "ready":
        return 0.92
    if status == "warning":
        return 0.72
    if status == "needs_review":
        return 0.5
    if status == "optional_missing":
        return 0.35
    return 0.0


def _evidence_refs(section_id: str) -> list[str]:
    field = FIELD_BY_ID.get(section_id)
    if field:
        return [field.section]
    return {
        "passport": ["passport"],
        "identity": ["identity", "passport"],
        "travel": ["travel"],
        "contact": ["contact"],
        "family": ["family"],
        "work_education": ["work_education"],
        "travel_history": ["travel_history"],
        "visa_specific": ["sevis", "petition", "travel"],
        "security": ["security"],
    }.get(section_id, [section_id])


def _slug(value: str) -> str:
    cleaned = "".join(char for char in value.upper() if char.isalnum())
    return cleaned[:24]
