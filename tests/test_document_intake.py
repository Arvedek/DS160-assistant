from __future__ import annotations

from ds160_agent.document_intake import (
    ai_status,
    annotate_candidates,
    analyze_document,
    build_codex_handoff,
    extract_candidates_from_text,
    parse_codex_result,
)


def test_extract_candidates_from_labeled_text() -> None:
    text = """
    Surname: ZHANG
    Given Names: WEI
    Passport Number: E12345678
    Date of Birth: 1990/08/15
    Email: zhangwei@example.com
    Phone: +86 138 0000 1234
    """

    candidates = extract_candidates_from_text(text)
    by_field = {candidate["fieldId"]: candidate["value"] for candidate in candidates}

    assert by_field["surname"] == "ZHANG"
    assert by_field["given_names"] == "WEI"
    assert by_field["passport_number"] == "E12345678"
    assert by_field["date_of_birth"] == "1990-08-15"
    assert by_field["email"] == "zhangwei@example.com"


def test_document_analyze_text_mode_without_ai_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = analyze_document(
        {
            "useAi": True,
            "document": {
                "filename": "passport-ocr.txt",
                "mimeType": "text/plain",
                "text": "Surname: ZHANG\nGiven Names: WEI\nPassport Number: E12345678",
            },
        }
    )

    assert result["mode"] == "local_text"
    assert result["evidence"]["filename"] == "passport-ocr.txt"
    assert any(candidate["fieldId"] == "passport_number" for candidate in result["candidates"])


def test_ai_status_reports_disabled(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    status = ai_status()

    assert status["enabled"] is False
    assert "image" in status["supports"]


def test_codex_handoff_contains_prompt_and_field_catalog() -> None:
    result = build_codex_handoff(
        {
            "currentData": {"surname": "ZHANG"},
            "document": {"filename": "passport.jpg", "mimeType": "image/jpeg", "text": "Passport Number: E12345678"},
        }
    )

    assert result["mode"] == "codex_handoff"
    assert "HANDOFF PACKAGE" in result["prompt"]
    assert result["handoff"]["currentDraft"]["surname"] == "ZHANG"
    assert any(field["fieldId"] == "passport_number" for field in result["handoff"]["fieldCatalog"])


def test_parse_codex_result_normalizes_candidates() -> None:
    result = parse_codex_result(
        {
            "result": {
                "format": "ds160-codex-candidates-v1",
                "candidates": [
                    {
                        "fieldId": "passport_number",
                        "value": "E12345678",
                        "confidence": 0.9,
                        "source": "passport image",
                        "requiresReview": True,
                    }
                ],
                "notes": ["review passport number"],
            }
        }
    )

    assert result["mode"] == "codex_result"
    assert result["candidates"][0]["fieldLabel"] == "Passport Number"
    assert result["candidates"][0]["quality"]["tier"] == "check_source"
    assert result["notes"] == ["review passport number"]


def test_candidate_annotation_marks_conflict() -> None:
    candidates = [{"fieldId": "passport_number", "value": "E12345678", "confidence": 0.9}]

    annotated = annotate_candidates(candidates, {"passport_number": "E87654321"})

    assert annotated[0]["action"] == "replace_conflict"
    assert annotated[0]["conflict"] is True
    assert annotated[0]["requiresReview"] is True
    assert annotated[0]["quality"]["tier"] == "needs_review"


def test_candidate_annotation_marks_ready_high_quality_source() -> None:
    candidates = [
        {
            "fieldId": "passport_number",
            "value": "E12345678",
            "confidence": 0.96,
            "source": "materials/passport.jpg",
            "requiresReview": False,
        }
    ]

    annotated = annotate_candidates(candidates, {})

    assert annotated[0]["quality"]["tier"] == "ready"
    assert annotated[0]["quality"]["score"] >= 90
