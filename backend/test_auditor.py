"""Tests for the Inventory Auditor (`auditor.py`) and its two HTTP entry
points in `main.py`:
- `GET  /api/auditor/run`
- `POST /api/devices/{id}/resolve-issue` ("Create service history")

The real OpenRouter/OpenAI client is mocked everywhere via the autouse
`llm` fixture (see `conftest.py`) - this whole file never makes a real,
billable network call, and is fully deterministic.
"""

import json
from datetime import date
from types import SimpleNamespace

import pytest

import auditor
import models
from conftest import create_device

# --------------------------------------------------------------------------
# auditor.py unit tests (pure function calls, no HTTP/FastAPI involved)
# --------------------------------------------------------------------------


def test_run_audit_returns_categories_from_llm(llm):
    llm(
        content=json.dumps(
            {
                "categories": [
                    {
                        "title": "\U0001F534 Critical Business Risks",
                        "issues": [
                            {
                                "device_id": 1,
                                "device_name": "Test Laptop",
                                "description": "Battery swelling reported.",
                                "actionable": True,
                            }
                        ],
                    }
                ]
            }
        )
    )
    result = auditor.run_audit([{"id": 1, "name": "Test Laptop"}])
    issue = result["categories"][0]["issues"][0]
    assert result["categories"][0]["title"] == "\U0001F534 Critical Business Risks"
    assert issue["device_id"] == 1
    assert issue["actionable"] is True


def test_run_audit_backfills_missing_device_name(llm):
    llm(
        content=json.dumps(
            {
                "categories": [
                    {
                        "title": "Data Integrity Issues",
                        "issues": [
                            {
                                "device_id": 42,
                                "description": "Brand typo.",
                                "actionable": False,
                            }
                        ],
                    }
                ]
            }
        )
    )
    result = auditor.run_audit([{"id": 42, "name": "Real Device Name"}])
    assert result["categories"][0]["issues"][0]["device_name"] == "Real Device Name"


def test_run_audit_drops_malformed_issues_and_categories(llm):
    llm(
        content=json.dumps(
            {
                "categories": [
                    {"title": "", "issues": [{"description": "no title"}]},
                    {
                        "title": "Valid Category",
                        "issues": [
                            {"description": ""},  # empty description -> dropped
                            "not-a-dict",  # malformed -> dropped
                            {"description": "Kept issue"},
                        ],
                    },
                ]
            }
        )
    )
    result = auditor.run_audit([])
    assert len(result["categories"]) == 1
    assert result["categories"][0]["title"] == "Valid Category"
    assert len(result["categories"][0]["issues"]) == 1
    assert result["categories"][0]["issues"][0]["description"] == "Kept issue"


def test_run_audit_drops_non_dict_categories(llm):
    llm(
        content=json.dumps(
            {
                "categories": [
                    "not-a-dict-category",
                    {"title": "Valid Category", "issues": [{"description": "Kept issue"}]},
                ]
            }
        )
    )
    result = auditor.run_audit([])
    assert len(result["categories"]) == 1
    assert result["categories"][0]["title"] == "Valid Category"


def test_run_audit_forces_actionable_false_without_device_id(llm):
    llm(
        content=json.dumps(
            {
                "categories": [
                    {
                        "title": "Category",
                        "issues": [
                            {
                                "device_id": None,
                                "description": "Generic issue not tied to a device.",
                                "actionable": True,
                            }
                        ],
                    }
                ]
            }
        )
    )
    result = auditor.run_audit([])
    assert result["categories"][0]["issues"][0]["actionable"] is False


def test_run_audit_no_anomalies_returns_empty_categories(llm):
    llm(content=json.dumps({"categories": []}))
    assert auditor.run_audit([]) == {"categories": []}


def test_run_audit_falls_back_to_raw_text_on_invalid_json(llm):
    llm(content="Sorry, I can't produce JSON right now.")
    result = auditor.run_audit([])
    assert result["categories"][0]["title"] == "AI Health Check"
    assert "Sorry" in result["categories"][0]["issues"][0]["description"]
    assert result["categories"][0]["issues"][0]["actionable"] is False


def test_run_audit_strips_markdown_code_fences(llm):
    payload = json.dumps({"categories": []})
    llm(content=f"```json\n{payload}\n```")
    assert auditor.run_audit([]) == {"categories": []}


def test_run_audit_raises_when_api_key_missing(monkeypatch):
    monkeypatch.setattr(auditor, "OPENROUTER_API_KEY", "")
    with pytest.raises(auditor.AuditorError, match="not configured"):
        auditor.run_audit([])


def test_run_audit_wraps_client_errors(llm):
    llm(error=RuntimeError("network exploded"))
    with pytest.raises(auditor.AuditorError, match="OpenRouter request failed"):
        auditor.run_audit([])


def test_resolve_device_issue_returns_stripped_text(llm):
    llm(content="  Issue reported. Device sent to service for repair.  ")
    text = auditor.resolve_device_issue("Test Laptop", "Battery swelling")
    assert text == "Issue reported. Device sent to service for repair."


def test_resolve_device_issue_wraps_client_errors(llm):
    llm(error=RuntimeError("boom"))
    with pytest.raises(auditor.AuditorError, match="OpenRouter request failed"):
        auditor.resolve_device_issue("Test Laptop", "Battery swelling")


# --------------------------------------------------------------------------
# GET /api/auditor/run
# --------------------------------------------------------------------------


def test_auditor_endpoint_returns_sanitized_report(client, llm):
    device = create_device(client, name="Swelling Laptop", issue="Battery swelling")
    llm(
        content=json.dumps(
            {
                "categories": [
                    {
                        "title": "\U0001F534 Critical Business Risks",
                        "issues": [
                            {
                                "device_id": device["id"],
                                "device_name": device["name"],
                                "description": "Battery swelling reported.",
                                "actionable": True,
                            }
                        ],
                    }
                ]
            }
        )
    )
    response = client.get("/api/auditor/run")
    assert response.status_code == 200
    body = response.json()
    assert body["categories"][0]["issues"][0]["device_id"] == device["id"]
    assert body["categories"][0]["issues"][0]["actionable"] is True


def test_auditor_endpoint_returns_502_when_api_key_missing(client, monkeypatch):
    monkeypatch.setattr(auditor, "OPENROUTER_API_KEY", "")
    response = client.get("/api/auditor/run")
    assert response.status_code == 502
    assert "not configured" in response.json()["detail"]


def test_auditor_endpoint_returns_502_on_client_error(client, llm):
    llm(error=ValueError("totally unexpected"))
    response = client.get("/api/auditor/run")
    assert response.status_code == 502


def test_auditor_endpoint_returns_502_on_malformed_llm_response(client, llm):
    """Covers the last-resort `except Exception` branch in main.py (distinct
    from AuditorError) - triggered by a response object that doesn't even
    have the `.choices` shape the SDK normally guarantees."""
    llm(raw_response=SimpleNamespace())
    response = client.get("/api/auditor/run")
    assert response.status_code == 502


# --------------------------------------------------------------------------
# POST /api/devices/{id}/resolve-issue ("Create service history")
# --------------------------------------------------------------------------


def test_resolve_issue_happy_path_updates_status_and_history(client, llm):
    device = create_device(
        client, name="Broken Mouse", status="Available", issue="Scroll wheel is stuck."
    )
    llm(content="Issue reported: scroll wheel stuck. Device sent to service for repair.")

    response = client.post(f"/api/devices/{device['id']}/resolve-issue")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Repair"
    assert body["issue"] == ""
    assert "scroll wheel stuck" in body["history"]
    assert date.today().isoformat() in body["history"]


def test_resolve_issue_rejects_device_with_no_issue(client, llm):
    device = create_device(client, issue=None)
    response = client.post(f"/api/devices/{device['id']}/resolve-issue")
    assert response.status_code == 400


def test_resolve_issue_device_not_found(client, llm):
    response = client.post("/api/devices/9999/resolve-issue")
    assert response.status_code == 404


def test_resolve_issue_returns_502_on_ai_error(client, llm):
    device = create_device(client, issue="Something is broken.")
    llm(error=RuntimeError("network exploded"))
    response = client.post(f"/api/devices/{device['id']}/resolve-issue")
    assert response.status_code == 502


def test_resolve_issue_returns_502_on_malformed_llm_response(client, llm):
    device = create_device(client, issue="Something is broken.")
    llm(raw_response=SimpleNamespace())
    response = client.post(f"/api/devices/{device['id']}/resolve-issue")
    assert response.status_code == 502


def test_resolve_issue_falls_back_to_generic_text_when_ai_returns_blank(client, llm):
    device = create_device(client, issue="Cracked screen.")
    llm(content="")  # model returns an empty string
    response = client.post(f"/api/devices/{device['id']}/resolve-issue")
    assert response.status_code == 200
    assert "Cracked screen." in response.json()["history"]


def test_resolve_issue_appends_to_existing_history(client, llm):
    device = create_device(
        client, issue="Keyboard sticky.", history="[2020-01-01] Initial setup."
    )
    llm(content="Issue reported: keyboard sticky. Device sent to service for repair.")
    response = client.post(f"/api/devices/{device['id']}/resolve-issue")
    body = response.json()
    assert "Initial setup." in body["history"]
    assert "keyboard sticky" in body["history"]
    assert body["history"].count("\n") >= 1


def test_resolve_issue_lemon_detection_flags_repeat_offenders(client, llm):
    current_year = date.today().year
    history = f"[{current_year}-01-01] Repaired once.\n[{current_year}-02-01] Repaired twice."
    device = create_device(client, issue="Third failure.", history=history)
    llm(content="Issue reported: third failure. Device sent to service for repair.")

    response = client.post(f"/api/devices/{device['id']}/resolve-issue")
    assert response.status_code == 200
    body = response.json()
    assert body["history"].count(str(current_year)) >= 3
    assert "Failure-prone device" in body["notes"]


def test_resolve_issue_lemon_detection_does_not_overwrite_existing_notes(client, llm):
    current_year = date.today().year
    history = f"[{current_year}-01-01] Repaired once.\n[{current_year}-02-01] Repaired twice."
    device = create_device(
        client, issue="Third failure.", history=history, notes="Under extended warranty."
    )
    llm(content="Issue reported: third failure. Device sent to service for repair.")

    response = client.post(f"/api/devices/{device['id']}/resolve-issue")
    assert response.status_code == 200
    assert response.json()["notes"] == "Under extended warranty."


def test_resolve_issue_no_lemon_warning_below_threshold(client, llm):
    current_year = date.today().year
    device = create_device(
        client, issue="Second failure.", history=f"[{current_year}-01-01] Repaired once."
    )
    llm(content="Issue reported: second failure. Device sent to service for repair.")

    response = client.post(f"/api/devices/{device['id']}/resolve-issue")
    assert response.json()["notes"] in (None, "")


def test_resolve_issue_race_condition_returns_409(client, llm, db_session_factory):
    """The atomic `UPDATE ... WHERE issue == defect_text` guard: if another
    request changes/clears this device's `issue` while the (mocked) AI call
    for THIS request is still "in flight", the final UPDATE must see 0
    matching rows and reject with 409 instead of silently overwriting the
    concurrent change."""
    device = create_device(client, issue="Original issue text.")

    def sneaky_side_effect(*_args, **_kwargs):
        session = db_session_factory()
        try:
            row = session.get(models.Device, device["id"])
            row.issue = "Changed by a concurrent request."
            session.commit()
        finally:
            session.close()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Some generated text."))]
        )

    llm(side_effect=sneaky_side_effect)

    response = client.post(f"/api/devices/{device['id']}/resolve-issue")
    assert response.status_code == 409
