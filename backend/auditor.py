"""Inventory Auditor ("Zero-UI"): a proactive, one-shot scan of the hardware
inventory for anomalies, powered by an OpenAI model routed through OpenRouter
(https://openrouter.ai) - the OpenAI Python SDK is used as a drop-in client
pointed at OpenRouter's base URL, so no extra SDK/dependency is needed.

Two entry points:
- `run_audit`: scans the *entire* inventory and returns a structured list of
  categorized anomalies (rendered as tiles by AiHealthCheck.vue, each
  optionally tied to a specific device via `device_id`). Issues that
  describe a real physical defect (an open `issue` field) are tagged
  `actionable: true` so the UI offers the "Create service history" action.
- `resolve_device_issue` ("Naprawa Sprzętu" / Predictive Maintenance): given
  a single device's `issue` description, asks the model for a short,
  professional history entry describing the triage/repair ticket (no
  estimated repair time - just what happened). Used by the "Create service
  history" action (see POST /api/devices/{id}/resolve-issue in main.py).
"""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Load `backend/.env` by explicit, file-relative path - not just the default
# CWD-based search - so this works no matter which directory `uvicorn` is
# launched from.
load_dotenv(Path(__file__).resolve().parent / ".env")

# OpenRouter is OpenAI-API-compatible: same `openai` SDK/client, just pointed
# at OpenRouter's base URL with an OpenRouter API key (never an "sk-..." key
# from platform.openai.com directly) and an OpenRouter-style model slug
# (provider-prefixed, e.g. "openai/gpt-4o-mini" for an OpenAI model routed
# through OpenRouter).
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL_NAME = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Optional, only used for OpenRouter's own leaderboard/analytics - harmless
# to leave as-is, but can be overridden via .env if desired.
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "http://localhost:5173")
OPENROUTER_SITE_NAME = os.getenv("OPENROUTER_SITE_NAME", "Hardware Hub Booksy")

AUDITOR_SYSTEM_PROMPT = """You are a strict Data Integrity & Business Logic Auditor for an IT hardware management system.
Your current year context is 2026.
Analyze the provided JSON inventory data and flag specific anomalies.

Specifically look for:
- Logic conflicts: Devices marked as 'Available' but containing warnings like 'repair', 'damage', or 'swelling' in their "issue" field.
- Temporal errors: Purchase dates in the future (after 2026) or incorrect date formats (non-ISO).
- Incomplete data: Missing brands or unrecognized statuses (e.g., 'Unknown').
- Typographical errors: Misspelled brand names (e.g., 'Appel' instead of 'Apple').

IMPORTANT: completely IGNORE the "history" and "notes" fields for every check
above and in general. "history" is only a log of past actions already taken
on the device (e.g. "Returned by user with liquid damage." describes
something that already happened and was already handled), and "notes" is a
free-form admin field (which may contain an automated "repeat offender"
warning) - neither must have ANY influence on your analysis. Never flag,
mention, or reference anything found only in "history" or "notes"; base every
issue exclusively on "issue", "name", "brand", "purchaseDate", and "status".
If a device's "issue" field is empty/null, it has no open defect - regardless
of what "history" or "notes" says - so do not report anything about it, not
even as a non-actionable note.

Respond with ONLY a valid JSON object (no markdown, no code fences, no commentary) matching exactly this shape:
{
  "categories": [
    {
      "title": "\U0001F534 Critical Business Risks",
      "issues": [
        {
          "device_id": 3,
          "device_name": "Razer Basilisk V2",
          "description": "Marked as 'Available' but its issue field mentions battery swelling.",
          "actionable": true
        }
      ]
    },
    {
      "title": "\U0001F7E1 Data Integrity Issues",
      "issues": [
        {
          "device_id": 7,
          "device_name": "Appel MacBook Pro",
          "description": "Brand is misspelled: 'Appel' instead of 'Apple'.",
          "actionable": false
        }
      ]
    }
  ]
}

CRITICAL OUTPUT RULE (applies to EVERY issue, in EVERY category, with NO exceptions): you MUST strictly output structured JSON objects. Every issue object MUST unequivocally contain "device_id" (integer, or null only if truly not tied to one device), "device_name" (string - the exact device name copied from the inventory, or null only if "device_id" is also null), and "description" (string - ONLY the issue/anomaly text). NEVER output a flat, merged description that embeds the device name or id inside the sentence in place of the proper fields (e.g. NEVER do `"device_id": null, "device_name": null, "description": "Device 5 (Razer Basilisk V2) has a battery issue"` - that is WRONG). Whenever an issue is about one specific device, "device_id" and "device_name" MUST be populated separately from "description", with NO exceptions, even in the "\U0001F534 Critical Business Risks" category.

Rules:
- Group issues into short, clear categories (e.g. "\U0001F534 Critical Business Risks", "\U0001F7E1 Data Integrity Issues", "\U0001F535 Data Quality Notes").
- Set "device_id" and "device_name" when an issue is tied to one specific device from the inventory; otherwise use null for both.
- Set "actionable" to true ONLY for a logic conflict where a device's status is NOT already 'Repair' AND its "issue" field is non-empty and clearly describes a current physical defect that a repair workflow should resolve. Set "actionable" to false for every other kind of issue (missing brand, unrecognized status, bad dates, brand typos, etc.) - these are informational only, there is no automated fix for them.
- Never generate an issue whose description mentions or is based on "history" or "notes" content (e.g. do not report things like "history mentions past damage" or similar) - both fields are completely out of scope for this audit.
- If you find no anomalies at all, return {"categories": []}.
- Never invent devices that are not present in the provided data."""

RESOLVE_ISSUE_SYSTEM_PROMPT = """You are an IT service desk assistant. Analyze the provided issue description for a device.
Generate a short, professional history log entry documenting that the issue was reported and the device was sent to service.
Return ONLY the generated text (e.g. "Issue reported: [description]. Device sent to service for repair."). Do NOT include any estimated repair time or duration. No greetings, no formatting, English only."""


class AuditorError(RuntimeError):
    """Raised when the auditor cannot produce a report (bad config, API error, ...)."""


def _require_client() -> OpenAI:
    if not OPENROUTER_API_KEY:
        raise AuditorError(
            "OPENROUTER_API_KEY is not configured on the server. Add it to backend/.env."
        )
    return OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        default_headers={
            # Optional attribution headers OpenRouter uses for its public
            # rankings - not required for the request to succeed.
            "HTTP-Referer": OPENROUTER_SITE_URL,
            "X-Title": OPENROUTER_SITE_NAME,
        },
    )


def _strip_code_fences(text: str) -> str:
    """Models sometimes wrap JSON in ```json ... ``` despite instructions not to."""
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    return match.group(1) if match else text


def _sanitize_categories(categories: list, devices: list[dict]) -> list:
    """Defensive normalization layer between the raw LLM response and the
    API/UI: the system prompt *tells* the model to always separate
    "device_id"/"device_name" from "description", but LLM output is never
    100% reliable, and a single malformed issue (e.g. a flat string with a
    null device_id/device_name) used to make a tile silently render without
    its name/locate-icon. Rather than trust the response as-is, every issue
    is repaired/normalized here so the UI always gets a consistent shape.
    """
    devices_by_id = {d.get("id"): d.get("name") for d in devices if d.get("id") is not None}

    sanitized = []
    for category in categories:
        if not isinstance(category, dict):
            continue
        title = category.get("title")
        if not isinstance(title, str) or not title.strip():
            continue

        clean_issues = []
        for issue in category.get("issues") or []:
            if not isinstance(issue, dict):
                continue

            description = issue.get("description")
            if not isinstance(description, str) or not description.strip():
                continue

            device_id = issue.get("device_id")
            device_id = device_id if isinstance(device_id, int) else None

            # Backfill a missing/blank device_name from the inventory
            # whenever device_id IS set - this is what keeps the tile's
            # name + locate-icon showing even if the model forgot to
            # populate "device_name" on its own.
            device_name = issue.get("device_name")
            if (not isinstance(device_name, str) or not device_name.strip()) and device_id is not None:
                device_name = devices_by_id.get(device_id)
            device_name = device_name.strip() if isinstance(device_name, str) and device_name.strip() else None

            clean_issues.append(
                {
                    "device_id": device_id,
                    "device_name": device_name,
                    "description": description.strip(),
                    "actionable": bool(issue.get("actionable")) and device_id is not None,
                }
            )

        if clean_issues:
            sanitized.append({"title": title.strip(), "issues": clean_issues})

    return sanitized


def run_audit(devices: list[dict]) -> dict:
    """Returns `{"categories": [{"title": str, "issues": [...]}]}`.

    Falls back to a single non-actionable tile (rather than raising) if the
    model doesn't return parseable JSON, since the raw text is still useful
    to a human reader.
    """
    client = _require_client()

    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL_NAME,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": AUDITOR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Here is the current hardware inventory as a JSON array. "
                        "Audit it now and respond with the JSON object described in "
                        "your instructions.\n\n" + json.dumps(devices, indent=2)
                    ),
                },
            ],
        )
    except Exception as exc:  # noqa: BLE001 - surfaced as a clean 502 by the caller
        raise AuditorError(f"OpenRouter request failed: {exc}") from exc

    raw = response.choices[0].message.content or "{}"

    try:
        data = json.loads(_strip_code_fences(raw))
    except json.JSONDecodeError:
        return {
            "categories": [
                {
                    "title": "AI Health Check",
                    "issues": [
                        {
                            "device_id": None,
                            "device_name": None,
                            "description": raw.strip(),
                            "actionable": False,
                        }
                    ],
                }
            ]
        }

    categories = data.get("categories") if isinstance(data, dict) else None
    categories = categories if isinstance(categories, list) else []
    return {"categories": _sanitize_categories(categories, devices)}


def resolve_device_issue(device_name: str, issue_text: str) -> str:
    """Asks the model to turn one device's `issue` description into a
    repair-ticket style history entry. Returns the raw generated text
    (caller stamps it with a date before appending it to the device's
    `history` column)."""
    client = _require_client()

    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL_NAME,
            messages=[
                {"role": "system", "content": RESOLVE_ISSUE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Device: {device_name}\nIssue: {issue_text}",
                },
            ],
        )
    except Exception as exc:  # noqa: BLE001 - surfaced as a clean 502 by the caller
        raise AuditorError(f"OpenRouter request failed: {exc}") from exc

    text = response.choices[0].message.content
    return (text or "").strip()
