from __future__ import annotations

from ds160_agent.document_intake import ai_status, analyze_document, extract_candidates_from_text


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
