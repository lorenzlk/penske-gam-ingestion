from __future__ import annotations

from typing import Any, Iterable

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def _service(creds: Credentials):
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _a1_sheet_tab(sheet_tab: str) -> str:
    """Quote sheet title for A1 notation (escape single quotes per Sheets rules)."""
    safe = sheet_tab.replace("'", "''")
    return f"'{safe}'"


def get_first_row(creds: Credentials, spreadsheet_id: str, sheet_tab: str) -> list[str] | None:
    svc = _service(creds)
    rng = f"{_a1_sheet_tab(sheet_tab)}!1:1"
    try:
        resp = (
            svc.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=rng)
            .execute()
        )
    except Exception:
        return None
    rows = resp.get("values") or []
    if not rows:
        return None
    return [str(c) if c is not None else "" for c in rows[0]]


def append_rows(
    creds: Credentials,
    spreadsheet_id: str,
    sheet_tab: str,
    rows: Iterable[list[Any]],
    value_input_option: str,
    dry_run: bool,
) -> None:
    body_rows = [list(r) for r in rows]
    if not body_rows:
        return
    if dry_run:
        return

    svc = _service(creds)
    rng = f"{_a1_sheet_tab(sheet_tab)}!A1"
    svc.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=rng,
        valueInputOption=value_input_option,
        insertDataOption="INSERT_ROWS",
        body={"values": body_rows},
    ).execute()
