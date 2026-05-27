from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
import re
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Field:
    id: str
    section: str
    label: str
    prompt: str
    required: bool = False
    input_type: str = "text"
    placeholder: str = ""
    help_text: str = ""
    options: tuple[str, ...] = ()
    allow_non_ascii: bool = False


SECTIONS: list[dict[str, str]] = [
    {
        "id": "identity",
        "title": "Identity",
        "description": "Names and biographical details exactly as the passport and civil records show them.",
    },
    {
        "id": "passport",
        "title": "Passport",
        "description": "Passport document details. Keep the physical passport nearby while filling this section.",
    },
    {
        "id": "travel",
        "title": "Travel Plan",
        "description": "Purpose, visa class, intended dates, address in the United States, and who pays.",
    },
    {
        "id": "contact",
        "title": "Contact",
        "description": "Home address, phone, email, and U.S. point of contact.",
    },
    {
        "id": "family",
        "title": "Family",
        "description": "Parents and close family context used by the application.",
    },
    {
        "id": "work_education",
        "title": "Work and Education",
        "description": "Current work or school details plus a compact employment and education history.",
    },
    {
        "id": "travel_history",
        "title": "Travel History",
        "description": "Prior U.S. travel, refusals, and recent international travel.",
    },
    {
        "id": "visa_specific",
        "title": "Visa Specific",
        "description": "Fields that apply to students, exchange visitors, and petition-based workers.",
    },
    {
        "id": "security",
        "title": "Security Review",
        "description": "This MVP only tracks whether sensitive DS-160 security questions need extra human review.",
    },
]


FIELDS: list[Field] = [
    Field("surname", "identity", "Surname", "Family name exactly as shown in the passport.", True),
    Field("given_names", "identity", "Given Names", "Given names exactly as shown in the passport.", True),
    Field(
        "native_name",
        "identity",
        "Full Name in Native Alphabet",
        "Native alphabet name if requested by the form.",
        False,
        allow_non_ascii=True,
    ),
    Field("other_names", "identity", "Other Names Used", "Maiden, religious, professional, or other names.", False),
    Field("date_of_birth", "identity", "Date of Birth", "Date of birth.", True, "date"),
    Field("place_of_birth", "identity", "Place of Birth", "City, state/province, and country of birth.", True),
    Field("sex", "identity", "Sex", "Sex as requested by the form.", True, "select", options=("Male", "Female")),
    Field("marital_status", "identity", "Marital Status", "Current marital status.", True),
    Field("nationality", "identity", "Nationality", "Current nationality/citizenship.", True),
    Field("national_id", "identity", "National ID", "National identification number, or Does Not Apply.", False),
    Field("passport_number", "passport", "Passport Number", "Passport or travel document number.", True),
    Field("passport_book_number", "passport", "Passport Book Number", "Passport book number, if applicable.", False),
    Field("passport_issue_country", "passport", "Issuing Country", "Country or authority that issued the passport.", True),
    Field("passport_issue_place", "passport", "Issuing Place", "City and country where passport was issued.", True),
    Field("passport_issue_date", "passport", "Issue Date", "Passport issue date.", True, "date"),
    Field("passport_expiration_date", "passport", "Expiration Date", "Passport expiration date.", True, "date"),
    Field("passport_lost_or_stolen", "passport", "Lost/Stolen Passport History", "Any lost or stolen passport details.", False),
    Field("visa_class", "travel", "Visa Class", "Intended visa class, for example B1/B2, F-1, J-1, H-1B.", True),
    Field("purpose_of_trip", "travel", "Purpose of Trip", "Plain English purpose of travel.", True),
    Field("arrival_date", "travel", "Intended Arrival Date", "Planned arrival date, if known.", False, "date"),
    Field("length_of_stay", "travel", "Length of Stay", "Expected stay length, for example 14 days or 4 years.", True),
    Field("us_street_address", "travel", "U.S. Stay Address", "Address where you plan to stay in the United States.", True),
    Field("us_city_state_zip", "travel", "U.S. City/State/ZIP", "City, state, and ZIP for the U.S. stay address.", True),
    Field("payer", "travel", "Person/Entity Paying", "Who is paying for the trip.", True),
    Field("travel_companions", "travel", "Travel Companions", "Names and relationship of travel companions, if any.", False),
    Field("home_address", "contact", "Home Address", "Current residential address.", True),
    Field("mailing_address", "contact", "Mailing Address", "Mailing address if different from home address.", False),
    Field("phone", "contact", "Phone", "Primary phone number.", True, "tel"),
    Field("email", "contact", "Email", "Primary email address.", True, "email"),
    Field("social_media", "contact", "Social Media Identifiers", "Platforms and handles requested by DS-160.", False),
    Field("us_contact_name", "contact", "U.S. Contact Name", "Person or organization in the United States.", True),
    Field("us_contact_relationship", "contact", "U.S. Contact Relationship", "Relationship to the U.S. contact.", True),
    Field("us_contact_address", "contact", "U.S. Contact Address", "Address of the U.S. contact.", True),
    Field("father_name", "family", "Father's Full Name", "Father's full name.", True),
    Field("mother_name", "family", "Mother's Full Name", "Mother's full name.", True),
    Field("immediate_family_us", "family", "Immediate Family in U.S.", "Immediate family in the United States, if any.", False),
    Field("spouse_details", "family", "Spouse Details", "Spouse details if married.", False),
    Field("current_occupation", "work_education", "Current Occupation", "Current occupation or student status.", True),
    Field("employer_or_school", "work_education", "Employer or School", "Current employer or school name.", True),
    Field("employer_or_school_address", "work_education", "Employer/School Address", "Current employer or school address.", True),
    Field("monthly_income", "work_education", "Monthly Income", "Monthly income if applicable, or Does Not Apply.", False),
    Field("job_duties", "work_education", "Job Duties", "Brief English description of current duties or studies.", True, "textarea"),
    Field("previous_employment", "work_education", "Previous Employment", "Previous jobs with dates, employer, title, and duties.", False, "textarea"),
    Field("education_history", "work_education", "Education History", "Schools, dates, course of study, and addresses.", False, "textarea"),
    Field("previous_us_travel", "travel_history", "Previous U.S. Travel", "Dates and lengths of prior U.S. visits.", False, "textarea"),
    Field("previous_us_visa", "travel_history", "Previous U.S. Visa", "Previous U.S. visa details, if any.", False, "textarea"),
    Field("visa_refusal_history", "travel_history", "Visa Refusal History", "Any U.S. visa refusals or immigration issues.", False, "textarea"),
    Field("five_year_international_travel", "travel_history", "Five-Year International Travel", "Countries visited in the past five years.", False, "textarea"),
    Field("sevis_id", "visa_specific", "SEVIS ID", "For F, J, and M applicants; otherwise Does Not Apply.", False),
    Field("school_program_address", "visa_specific", "School/Program Address", "For F, J, and M applicants.", False),
    Field("petition_receipt", "visa_specific", "Petition Receipt", "For petition-based workers if applicable.", False),
    Field(
        "security_communicable_disease",
        "security",
        "Communicable Disease",
        "Applicant-reviewed answer for communicable disease or public health grounds.",
        True,
        "select",
        options=("No", "Yes", "Needs review"),
    ),
    Field(
        "security_arrest_history",
        "security",
        "Arrest or Conviction History",
        "Applicant-reviewed answer for any arrest, charge, conviction, or related issue.",
        True,
        "select",
        options=("No", "Yes", "Needs review"),
    ),
    Field(
        "security_drug_violation",
        "security",
        "Drug Violation",
        "Applicant-reviewed answer for controlled substance or drug-related questions.",
        True,
        "select",
        options=("No", "Yes", "Needs review"),
    ),
    Field(
        "security_fraud_misrepresentation",
        "security",
        "Fraud or Misrepresentation",
        "Applicant-reviewed answer for fraud, misrepresentation, or immigration document issues.",
        True,
        "select",
        options=("No", "Yes", "Needs review"),
    ),
    Field(
        "security_immigration_violation",
        "security",
        "Immigration Violation",
        "Applicant-reviewed answer for overstay, removal, deportation, or visa violation questions.",
        True,
        "select",
        options=("No", "Yes", "Needs review"),
    ),
    Field(
        "security_terrorism_related",
        "security",
        "Security or Terrorism Related",
        "Applicant-reviewed answer for terrorism, violence, genocide, or related security questions.",
        True,
        "select",
        options=("No", "Yes", "Needs review"),
    ),
    Field(
        "security_public_school_violation",
        "security",
        "Public School Violation",
        "Applicant-reviewed answer for public school attendance and reimbursement questions.",
        True,
        "select",
        options=("No", "Yes", "Needs review"),
    ),
    Field("security_answers_summary", "security", "Security Answers Notes", "List any Yes or uncertain security answers and source notes.", False, "textarea"),
    Field("preparer_notes", "security", "Preparer Notes", "Who prepared the draft and what still needs applicant review.", False, "textarea"),
]


REQUIRED_FIELD_IDS = {field.id for field in FIELDS if field.required}
FIELD_BY_ID = {field.id: field for field in FIELDS}
SECTION_BY_ID = {section["id"]: section for section in SECTIONS}
DATE_FIELD_IDS = {field.id for field in FIELDS if field.input_type == "date"}

SECURITY_BACKGROUND_FIELD_IDS = {
    "security_communicable_disease",
    "security_arrest_history",
    "security_drug_violation",
    "security_fraud_misrepresentation",
    "security_immigration_violation",
    "security_terrorism_related",
    "security_public_school_violation",
}

SECURITY_OPTIONS = ("No", "Yes", "Needs review")


def schema_payload() -> dict[str, Any]:
    return {
        "sections": SECTIONS,
        "fields": [
            {
                "id": field.id,
                "section": field.section,
                "label": field.label,
                "prompt": field.prompt,
                "required": field.required,
                "inputType": field.input_type,
                "placeholder": field.placeholder,
                "helpText": field.help_text,
                "options": list(field.options),
            }
            for field in FIELDS
        ],
    }


def analyze_application(payload: dict[str, Any]) -> dict[str, Any]:
    data = _clean_payload(payload)
    issues = validate_application(data)
    draft = build_draft(data)
    from .dossier import build_dossier

    dossier = build_dossier(data, issues)
    required_answered = sum(1 for field_id in REQUIRED_FIELD_IDS if data.get(field_id))
    completeness = {
        "requiredAnswered": required_answered,
        "requiredTotal": len(REQUIRED_FIELD_IDS),
        "percent": round((required_answered / len(REQUIRED_FIELD_IDS)) * 100),
    }
    return {
        "data": data,
        "issues": [issue.as_payload() for issue in issues],
        "draft": draft,
        "dossier": dossier,
        "sectionStatus": dossier["sections"],
        "fieldMap": dossier["fieldMap"],
        "productGuidance": build_product_guidance(data, issues, completeness, dossier["sections"]),
        "reviewPacket": build_review_packet(data, issues),
        "markdown": render_markdown(data, draft, issues, completeness),
        "completeness": completeness,
        "nextSteps": next_steps(issues),
    }


def validate_application(data: dict[str, str]) -> list["Issue"]:
    issues: list[Issue] = []
    for field in FIELDS:
        value = data.get(field.id, "")
        if field.required and not value:
            issues.append(Issue("error", field.id, field.section, f"{field.label} is required."))
        if value and field.options and value not in field.options:
            issues.append(Issue("error", field.id, field.section, f"{field.label} must be one of: {', '.join(field.options)}."))
        if value and not field.allow_non_ascii and _has_non_ascii(value):
            issues.append(
                Issue(
                    "warning",
                    field.id,
                    field.section,
                    f"{field.label} contains non-English characters. DS-160 answers generally need English characters.",
                )
            )

    for field_id in DATE_FIELD_IDS:
        value = data.get(field_id, "")
        if value and _parse_date(value) is None:
            field = FIELD_BY_ID[field_id]
            issues.append(Issue("error", field.id, field.section, f"{field.label} must use YYYY-MM-DD."))

    email = data.get("email", "")
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        issues.append(Issue("warning", "email", "contact", "Email format looks unusual."))

    passport_expiry = _parse_date(data.get("passport_expiration_date", ""))
    arrival = _parse_date(data.get("arrival_date", ""))
    issue_date = _parse_date(data.get("passport_issue_date", ""))
    birth_date = _parse_date(data.get("date_of_birth", ""))

    if issue_date and passport_expiry and issue_date >= passport_expiry:
        issues.append(Issue("error", "passport_expiration_date", "passport", "Passport expiration must be after issue date."))
    if birth_date and issue_date and birth_date >= issue_date:
        issues.append(Issue("warning", "passport_issue_date", "passport", "Passport issue date is not after date of birth."))
    if arrival and arrival < date.today():
        issues.append(Issue("warning", "arrival_date", "travel", "Intended arrival date is in the past."))
    if arrival and passport_expiry and passport_expiry <= arrival:
        issues.append(Issue("error", "passport_expiration_date", "passport", "Passport expires before or on intended arrival date."))

    visa_class = data.get("visa_class", "").upper()
    if any(code in visa_class for code in ("F", "J", "M")):
        _require_if_missing(data, issues, "sevis_id", "visa_specific", "SEVIS ID is usually needed for F, J, and M applicants.")
        _require_if_missing(
            data,
            issues,
            "school_program_address",
            "visa_specific",
            "School or program address is usually needed for F, J, and M applicants.",
        )
    if any(code in visa_class for code in ("H", "L", "O", "P", "R", "CW")):
        _require_if_missing(
            data,
            issues,
            "petition_receipt",
            "visa_specific",
            "Petition receipt details are usually needed for petition-based workers.",
        )

    for field_id in SECURITY_BACKGROUND_FIELD_IDS:
        answer = data.get(field_id, "")
        if answer in {"Yes", "Needs review"}:
            field = FIELD_BY_ID[field_id]
            issues.append(
                Issue(
                    "review",
                    field_id,
                    "security",
                    f"{field.label} is marked {answer}; applicant should review source facts carefully before signing.",
                )
            )

    security = data.get("security_answers_summary", "").lower()
    if security and security not in {"all no", "all no after review", "all no - reviewed"} and "yes" in security:
        issues.append(
            Issue(
                "review",
                "security_answers_summary",
                "security",
                "A Yes security answer needs careful applicant review and may need professional advice.",
            )
        )
    if data.get("visa_refusal_history"):
        issues.append(
            Issue(
                "review",
                "visa_refusal_history",
                "travel_history",
                "Refusal or immigration history should be copied accurately from records; do not paraphrase casually.",
            )
        )

    return issues


def build_draft(data: dict[str, str]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for section in SECTIONS:
        rows = []
        for field in FIELDS:
            if field.section != section["id"]:
                continue
            value = data.get(field.id, "")
            if value:
                rows.append({"fieldId": field.id, "label": field.label, "value": value, "required": field.required})
            elif field.required:
                rows.append({"fieldId": field.id, "label": field.label, "value": "[NEEDS ANSWER]", "required": True})
        groups.append({"sectionId": section["id"], "title": section["title"], "rows": rows})
    return groups


def render_markdown(
    data: dict[str, str],
    draft: list[dict[str, Any]],
    issues: list["Issue"],
    completeness: dict[str, int],
) -> str:
    lines = [
        "# DS-160 Local Draft",
        "",
        "This is a local preparation draft only. The applicant must review the official DS-160 before signing or submitting.",
        "",
        f"Required completeness: {completeness['requiredAnswered']} / {completeness['requiredTotal']} ({completeness['percent']}%).",
        "",
        "## Section Readiness",
    ]
    from .dossier import build_section_status

    for section in build_section_status(data, issues):
        lines.append(
            f"- {section['title']}: {section['status']} "
            f"({section['requiredAnswered']}/{section['requiredTotal']} required, "
            f"{section['errorCount']} errors, {section['warningCount']} warnings, {section['reviewCount']} review)"
        )

    lines.extend(
        [
            "",
        "## Review Issues",
        ]
    )
    if issues:
        for issue in issues:
            field = FIELD_BY_ID.get(issue.field_id)
            label = field.label if field else issue.field_id
            lines.append(f"- {issue.level.upper()}: {label} - {issue.message}")
    else:
        lines.append("- No blocking issues found by the local checker.")

    for group in draft:
        lines.extend(["", f"## {group['title']}"])
        for row in group["rows"]:
            lines.append(f"- **{row['label']}**: {row['value']}")

    lines.extend(
        [
            "",
            "## Final Human Checklist",
            "- Compare every answer against the passport and source documents.",
            "- Confirm all answers are in English characters unless the official form asks for native alphabet.",
            "- Confirm sensitive security, refusal, arrest, overstay, and immigration answers personally.",
            "- Applicant must personally review, sign, and submit the official application.",
        ]
    )
    if data.get("preparer_notes"):
        lines.extend(["", "## Preparer Notes", data["preparer_notes"]])
    return "\n".join(lines)


def next_steps(issues: list["Issue"]) -> list[str]:
    if any(issue.level == "error" for issue in issues):
        return [
            "Finish every required field marked as an error.",
            "Re-run the local checker until there are no blocking errors.",
            "Then review warning and review items before using the official DS-160 website.",
        ]
    if issues:
        return [
            "Review each warning and review item with source documents.",
            "Use the draft as a copy aid only after the applicant confirms accuracy.",
            "Do not sign or submit until the official form has been reviewed page by page.",
        ]
    return [
        "Export the draft for your records.",
        "Open the official DS-160 site manually and copy answers carefully.",
        "Applicant should do the final page-by-page review and electronic signature.",
    ]


def build_product_guidance(
    data: dict[str, str],
    issues: list["Issue"],
    completeness: dict[str, int],
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    error_count = sum(1 for issue in issues if issue.level == "error")
    warning_count = sum(1 for issue in issues if issue.level == "warning")
    review_count = sum(1 for issue in issues if issue.level == "review")
    score = max(0, completeness["percent"] - error_count * 4 - review_count * 2 - warning_count)
    if error_count:
        stage = "collect"
        next_action = "Finish required fields before relying on generated drafts."
    elif review_count or warning_count:
        stage = "review"
        next_action = "Resolve review items and compare answers against source documents."
    elif completeness["percent"] < 100:
        stage = "complete"
        next_action = "Complete optional-but-important history fields and save a local report."
    else:
        stage = "export"
        next_action = "Export the review packet and manually copy answers into the official DS-160."

    return {
        "readinessScore": score,
        "stage": stage,
        "nextBestAction": next_action,
        "workflow": [
            _workflow_step("collect", "Collect source docs", _has_core_identity(data), "Passport and basic identity are started."),
            _workflow_step("extract", "Extract candidates", any(data.get(field.id) for field in FIELDS), "Use documents, Codex, or local text extraction."),
            _workflow_step("complete", "Complete required fields", completeness["percent"] == 100, f"{completeness['requiredAnswered']} of {completeness['requiredTotal']} required answered."),
            _workflow_step("review", "Resolve review items", error_count == 0 and review_count == 0 and warning_count == 0, f"{error_count} errors, {warning_count} warnings, {review_count} review items."),
            _workflow_step("export", "Export and copy manually", error_count == 0 and completeness["percent"] == 100, "Applicant signs and submits only after official page review."),
        ],
        "sectionFocus": [
            {
                "sectionId": section["sectionId"],
                "title": section["title"],
                "status": section["status"],
            }
            for section in sections
            if section["status"] != "ready"
        ][:4],
    }


def build_review_packet(data: dict[str, str], issues: list["Issue"]) -> dict[str, Any]:
    missing_required = [
        {"fieldId": field.id, "label": field.label, "section": field.section}
        for field in FIELDS
        if field.required and not data.get(field.id)
    ]
    risk_items = [
        {
            "level": issue.level,
            "fieldId": issue.field_id,
            "label": FIELD_BY_ID.get(issue.field_id, Field(issue.field_id, issue.section, issue.field_id, "")).label,
            "message": issue.message,
        }
        for issue in issues
        if issue.level in {"warning", "review"}
    ]
    return {
        "summary": {
            "missingRequired": len(missing_required),
            "riskItems": len(risk_items),
            "readyForOfficialCopy": not missing_required and not any(issue.level == "error" for issue in issues),
        },
        "missingRequired": missing_required,
        "riskItems": risk_items,
        "sourceChecklist": source_document_checklist(data),
        "finalChecks": [
            "Applicant reviewed every answer against source documents.",
            "All non-native-alphabet DS-160 answers use English characters.",
            "Security/background answers were reviewed by the applicant personally.",
            "Official DS-160 review pages were checked before electronic signature.",
        ],
    }


def source_document_checklist(data: dict[str, str]) -> list[dict[str, str]]:
    items = [
        ("passport", "Passport bio page", "Needed for identity and passport fields."),
        ("travel", "Travel itinerary or visit plan", "Needed for purpose, dates, stay address, and payer."),
        ("contact", "U.S. contact or hotel details", "Needed for U.S. contact and address fields."),
        ("work", "Employment or school proof", "Needed for occupation, employer/school, income, and duties."),
        ("family", "Family names and spouse details", "Needed for family section."),
        ("history", "Prior U.S. visa/travel/refusal records", "Needed for travel history accuracy."),
        ("security", "Applicant security/background review", "Needed before final signature."),
    ]
    visa_class = data.get("visa_class", "").upper()
    if any(code in visa_class for code in ("F", "J", "M")):
        items.append(("sevis", "I-20/DS-2019 and SEVIS details", "Needed for student/exchange visitor cases."))
    if any(code in visa_class for code in ("H", "L", "O", "P", "R", "CW")):
        items.append(("petition", "Petition receipt or approval notice", "Needed for petition-based worker cases."))
    return [{"id": item[0], "label": item[1], "why": item[2]} for item in items]


def _workflow_step(step_id: str, label: str, done: bool, detail: str) -> dict[str, Any]:
    return {"id": step_id, "label": label, "status": "done" if done else "open", "detail": detail}


def _has_core_identity(data: dict[str, str]) -> bool:
    return bool(data.get("surname") and data.get("given_names") and data.get("passport_number"))


def save_analysis(analysis: dict[str, Any], output_root: Path | str = "outputs/ds160") -> dict[str, str]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = root / f"ds160-draft-{stamp}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(analysis.get("markdown", ""), encoding="utf-8")
    return {"jsonPath": str(json_path), "markdownPath": str(md_path)}


@dataclass(frozen=True)
class Issue:
    level: str
    field_id: str
    section: str
    message: str

    def as_payload(self) -> dict[str, str]:
        field = FIELD_BY_ID.get(self.field_id)
        return {
            "level": self.level,
            "fieldId": self.field_id,
            "section": self.section,
            "fieldLabel": field.label if field else self.field_id,
            "message": self.message,
        }


def _clean_payload(payload: dict[str, Any]) -> dict[str, str]:
    source = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    cleaned: dict[str, str] = {}
    for field in FIELDS:
        raw = source.get(field.id, "")
        if raw is None:
            value = ""
        elif isinstance(raw, list):
            value = "\n".join(str(item).strip() for item in raw if str(item).strip())
        else:
            value = str(raw).strip()
        cleaned[field.id] = _normalize_answer(value)
    return cleaned


def _normalize_answer(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value.replace("\r\n", "\n")).strip()


def _has_non_ascii(value: str) -> bool:
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return True
    return False


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _require_if_missing(data: dict[str, str], issues: list[Issue], field_id: str, section: str, message: str) -> None:
    if not data.get(field_id):
        issues.append(Issue("warning", field_id, section, message))
