from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from gam_ingestion.config import Settings
from gam_ingestion.csv_extract import (
    META_KEYS,
    build_sheet_rows,
    parse_csv_bytes,
    pick_csv_attachment,
)
from gam_ingestion.google_auth import SCOPES, get_credentials
from gam_ingestion import gmail_ops
from gam_ingestion import sheets_ops


log = logging.getLogger(__name__)


def run_once(settings: Settings) -> int:
    creds = get_credentials(
        settings.credentials_path,
        settings.token_path,
        SCOPES,
    )

    label_id = gmail_ops.ensure_label_id(creds, settings.processed_label)
    candidate_ids = gmail_ops.list_candidate_messages(creds, settings.gmail_query)

    existing_ids = sheets_ops.get_existing_gmail_message_ids(
        creds,
        settings.spreadsheet_id,
        settings.sheet_tab,
    )

    encoding = os.environ.get("GAM_CSV_ENCODING", "utf-8-sig")
    att_pattern = os.environ.get("GAM_ATTACHMENT_REGEX", "").strip() or None

    processed = 0
    skipped = 0

    for mid in candidate_ids:
        if gmail_ops.message_has_label(creds, mid, label_id):
            skipped += 1
            continue

        msg = gmail_ops.get_message_full(creds, mid)

        picked = pick_csv_attachment(msg.attachments, att_pattern)
        if not picked:
            log.warning(
                "No matching CSV attachment for message %s (%s); skipping label.",
                mid,
                msg.subject,
            )
            skipped += 1
            continue

        filename, raw_bytes = picked
        meta = {
            "gmail_message_id": msg.message_id,
            "gmail_internal_date_ms": msg.internal_date_ms or "",
            "email_subject": msg.subject,
            "attachment_filename": filename,
        }

        if msg.message_id in existing_ids:
            log.info(
                "Skip duplicate: message %s already present in sheet column A",
                mid,
            )
            if not settings.dry_run:
                gmail_ops.add_label_to_message(creds, mid, label_id)
            skipped += 1
            continue

        extract = parse_csv_bytes(raw_bytes, encoding)
        if not extract.header:
            log.warning("Empty CSV for message %s; skipping.", mid)
            skipped += 1
            continue

        existing_header = sheets_ops.get_first_row(
            creds, settings.spreadsheet_id, settings.sheet_tab
        )
        is_empty = (
            existing_header is None
            or len(existing_header) == 0
            or all(c == "" for c in existing_header)
        )

        try:
            header_out, body_rows = build_sheet_rows(
                meta,
                extract.header,
                extract.data_rows,
                None if is_empty else existing_header,
            )
        except ValueError as e:
            log.error("Column mismatch for message %s: %s", mid, e)
            skipped += 1
            continue

        to_write: list[list[object]] = []
        if is_empty:
            to_write.append(header_out)
        to_write.extend(body_rows)

        sheets_ops.append_rows(
            creds,
            settings.spreadsheet_id,
            settings.sheet_tab,
            to_write,
            settings.value_input_option,
            settings.dry_run,
        )

        if not settings.dry_run:
            gmail_ops.add_label_to_message(creds, mid, label_id)
            existing_ids.add(msg.message_id)

        processed += 1
        log.info(
            "Ingested message %s rows=%s attachment=%s",
            mid,
            len(body_rows),
            filename,
        )

    log.info(
        "Done. processed=%s skipped_or_no_op=%s candidates=%s",
        processed,
        skipped,
        len(candidate_ids),
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="Ingest GAM email CSV into Google Sheets.")
    parser.add_argument(
        "--dump-message",
        metavar="MESSAGE_ID",
        help="Print attachment summary for a Gmail message id and exit (no sheet writes).",
    )
    args = parser.parse_args(argv)

    settings = Settings.load()

    if args.dump_message:
        creds = get_credentials(
            settings.credentials_path,
            settings.token_path,
            SCOPES,
        )
        msg = gmail_ops.get_message_full(creds, args.dump_message)
        print(json.dumps(gmail_ops.export_message_debug_json(msg), indent=2))
        return 0

    return run_once(settings)


if __name__ == "__main__":
    sys.exit(main())
