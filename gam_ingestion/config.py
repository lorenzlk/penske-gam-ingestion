from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _optional(name: str, default: str) -> str:
    return os.environ.get(name, default).strip() or default


@dataclass(frozen=True)
class Settings:
    spreadsheet_id: str
    sheet_tab: str
    gmail_query: str
    processed_label: str
    credentials_path: Path
    token_path: Path
    dry_run: bool
    value_input_option: str

    @staticmethod
    def load() -> "Settings":
        spreadsheet_id = _require("GAM_SPREADSHEET_ID")
        sheet_tab = _optional("GAM_SHEET_TAB", "Data")
        gmail_query = _optional(
            "GAM_GMAIL_QUERY",
            '"PMC _ Mula Report" has:attachment newer_than:180d in:anywhere',
        )
        processed_label = _optional("GAM_PROCESSED_LABEL", "GAM/Ingested")
        credentials_path = Path(_optional("GOOGLE_OAUTH_CLIENT_SECRETS", "credentials.json"))
        token_path = Path(_optional("GOOGLE_OAUTH_TOKEN", "token.json"))
        dry_run = os.environ.get("GAM_DRY_RUN", "").lower() in ("1", "true", "yes")
        value_input_option = _optional("GAM_VALUE_INPUT_OPTION", "USER_ENTERED")

        return Settings(
            spreadsheet_id=spreadsheet_id,
            sheet_tab=sheet_tab,
            gmail_query=gmail_query,
            processed_label=processed_label,
            credentials_path=credentials_path,
            token_path=token_path,
            dry_run=dry_run,
            value_input_option=value_input_option,
        )
