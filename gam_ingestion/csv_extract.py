from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from typing import Any


META_KEYS = (
    "gmail_message_id",
    "gmail_internal_date_ms",
    "email_subject",
    "attachment_filename",
)


@dataclass(frozen=True)
class CsvExtractResult:
    header: list[str]
    data_rows: tuple[list[Any], ...]


def pick_csv_attachment(
    attachments: tuple[Any, ...],
    filename_pattern: str | None,
) -> tuple[str, bytes] | None:
    for att in attachments:
        name = att.filename or ""
        lower = name.lower()
        if filename_pattern:
            if not re.search(filename_pattern, name, re.IGNORECASE):
                continue
        elif not lower.endswith(".csv"):
            continue
        return name, att.data
    return None


def parse_csv_bytes(
    raw: bytes,
    encoding: str,
) -> CsvExtractResult:
    text = raw.decode(encoding)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(io.StringIO(text), dialect)
    rows = list(reader)
    if not rows:
        return CsvExtractResult(header=[], data_rows=())

    header = [h.strip() if isinstance(h, str) else str(h) for h in rows[0]]
    data = []
    for row in rows[1:]:
        if not row or all((c or "").strip() == "" for c in row):
            continue
        padded = list(row) + [""] * max(0, len(header) - len(row))
        data.append(padded[: len(header)])

    return CsvExtractResult(header=header, data_rows=tuple(data))


def build_sheet_rows(
    meta: dict[str, Any],
    header: list[str],
    data_rows: tuple[list[Any], ...],
    existing_header: list[str] | None,
) -> tuple[list[str], list[list[Any]]]:
    meta_keys = list(META_KEYS)
    meta_vals = [meta[k] for k in meta_keys]

    if existing_header is None:
        full_header = meta_keys + header
        out_rows = []
        for dr in data_rows:
            out_rows.append(meta_vals + dr)
        return full_header, out_rows

    if existing_header[: len(meta_keys)] != meta_keys:
        raise ValueError(
            "Sheet header does not start with expected ingest columns; "
            f"expected prefix {meta_keys}, got {existing_header[: len(meta_keys)]}"
        )

    expected_tail = existing_header[len(meta_keys) :]
    if expected_tail != header:
        raise ValueError(
            "CSV columns do not match the sheet header row. "
            f"Sheet: {expected_tail!r}, CSV: {header!r}"
        )

    out_rows = []
    for dr in data_rows:
        out_rows.append(meta_vals + dr)
    return existing_header, out_rows
