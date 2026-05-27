from __future__ import annotations

from ds160_agent.core import analyze_application, validate_application


def complete_payload() -> dict[str, str]:
    return {
        "surname": "ZHANG",
        "given_names": "WEI",
        "date_of_birth": "1998-02-03",
        "place_of_birth": "Shanghai, China",
        "sex": "Male",
        "marital_status": "Single",
        "nationality": "China",
        "passport_number": "E12345678",
        "passport_issue_country": "China",
        "passport_issue_place": "Shanghai, China",
        "passport_issue_date": "2024-01-01",
        "passport_expiration_date": "2034-01-01",
        "visa_class": "B1/B2",
        "purpose_of_trip": "Tourism and business meetings",
        "arrival_date": "2026-08-01",
        "length_of_stay": "14 days",
        "us_street_address": "100 Main Street",
        "us_city_state_zip": "New York, NY 10001",
        "payer": "Self",
        "home_address": "Shanghai, China",
        "phone": "+86 138 0000 0000",
        "email": "wei@example.com",
        "us_contact_name": "ABC Hotel",
        "us_contact_relationship": "Hotel",
        "us_contact_address": "100 Main Street, New York, NY 10001",
        "father_name": "ZHANG MIN",
        "mother_name": "LI HUA",
        "current_occupation": "Software Engineer",
        "employer_or_school": "Example Technology Ltd",
        "employer_or_school_address": "Shanghai, China",
        "job_duties": "Develop and maintain business software.",
        "security_communicable_disease": "No",
        "security_arrest_history": "No",
        "security_drug_violation": "No",
        "security_fraud_misrepresentation": "No",
        "security_immigration_violation": "No",
        "security_terrorism_related": "No",
        "security_public_school_violation": "No",
        "security_answers_summary": "All No",
    }


def test_complete_payload_has_no_blocking_errors() -> None:
    issues = validate_application(complete_payload())

    assert [issue for issue in issues if issue.level == "error"] == []


def test_missing_required_fields_are_reported() -> None:
    result = analyze_application({"data": {"surname": "ZHANG"}})

    errors = [issue for issue in result["issues"] if issue["level"] == "error"]
    assert errors
    assert result["completeness"]["requiredAnswered"] == 1


def test_student_payload_warns_for_missing_sevis() -> None:
    payload = complete_payload()
    payload["visa_class"] = "F-1"

    issues = validate_application(payload)

    assert any(issue.field_id == "sevis_id" and issue.level == "warning" for issue in issues)


def test_non_ascii_warning_excludes_native_name() -> None:
    payload = complete_payload()
    payload["given_names"] = "张伟"
    payload["native_name"] = "张伟"

    issues = validate_application(payload)

    assert any(issue.field_id == "given_names" for issue in issues)
    assert not any(issue.field_id == "native_name" for issue in issues)


def test_analysis_includes_dossier_and_section_status() -> None:
    result = analyze_application({"data": complete_payload()})

    assert result["dossier"]["format"] == "ds160-assistant-dossier-v1"
    assert result["dossier"]["caseId"].startswith("ZHANG-WEI")
    assert result["sectionStatus"]
    assert all("status" in section for section in result["sectionStatus"])
    assert result["productGuidance"]["readinessScore"] > 80
    assert result["reviewPacket"]["summary"]["readyForOfficialCopy"] is True


def test_security_yes_answer_requires_review() -> None:
    payload = complete_payload()
    payload["security_arrest_history"] = "Yes"

    issues = validate_application(payload)

    assert any(issue.field_id == "security_arrest_history" and issue.level == "review" for issue in issues)


def test_missing_required_fields_show_in_review_packet() -> None:
    result = analyze_application({"data": {"surname": "ZHANG"}})

    assert result["productGuidance"]["stage"] == "collect"
    assert result["reviewPacket"]["summary"]["missingRequired"] > 0
    assert result["reviewPacket"]["summary"]["readyForOfficialCopy"] is False
