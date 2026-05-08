from __future__ import annotations

import base64
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


@dataclass(frozen=True)
class EmailAttachment:
    filename: str
    mime_type: str
    data: bytes


@dataclass(frozen=True)
class FetchedMessage:
    message_id: str
    thread_id: str
    subject: str
    internal_date_ms: str | None
    snippet: str
    raw_bytes: bytes
    attachments: tuple[EmailAttachment, ...]


def _service(creds: Credentials):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def ensure_label_id(creds: Credentials, label_name: str) -> str:
    svc = _service(creds)
    resp = svc.users().labels().list(userId="me").execute()
    labels = resp.get("labels", [])
    for lab in labels:
        if lab.get("name") == label_name:
            return lab["id"]

    body: dict[str, Any] = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = svc.users().labels().create(userId="me", body=body).execute()
    return created["id"]


def list_candidate_messages(creds: Credentials, query: str, max_results: int = 50) -> list[str]:
    svc = _service(creds)
    resp = (
        svc.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    return [m["id"] for m in resp.get("messages", [])]


def get_message_full(creds: Credentials, message_id: str) -> FetchedMessage:
    svc = _service(creds)
    raw = (
        svc.users()
        .messages()
        .get(userId="me", id=message_id, format="raw")
        .execute()
    )
    raw_b64 = raw["raw"]
    raw_bytes = base64.urlsafe_b64decode(raw_b64.encode("utf-8"))

    meta = (
        svc.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["Subject"],
        )
        .execute()
    )

    subject = ""
    for h in meta.get("payload", {}).get("headers", []):
        if h.get("name", "").lower() == "subject":
            subject = h.get("value", "") or ""
            break

    internal_date_ms = meta.get("internalDate")
    snippet = meta.get("snippet", "") or ""

    msg = _parse_rfc822(raw_bytes)

    attachments: list[EmailAttachment] = []
    for part in msg.walk():
        disp = part.get_content_disposition()
        if disp != "attachment":
            continue
        filename = part.get_filename() or "attachment"
        payload = part.get_payload(decode=True) or b""
        attachments.append(
            EmailAttachment(
                filename=filename,
                mime_type=part.get_content_type(),
                data=payload,
            )
        )

    return FetchedMessage(
        message_id=message_id,
        thread_id=meta.get("threadId", ""),
        subject=subject,
        internal_date_ms=str(internal_date_ms) if internal_date_ms else None,
        snippet=snippet,
        raw_bytes=raw_bytes,
        attachments=tuple(attachments),
    )


def _parse_rfc822(raw_bytes: bytes):
    return BytesParser(policy=policy.default).parsebytes(raw_bytes)


def message_has_label(creds: Credentials, message_id: str, label_id: str) -> bool:
    svc = _service(creds)
    m = svc.users().messages().get(userId="me", id=message_id, format="minimal").execute()
    return label_id in (m.get("labelIds") or [])


def add_label_to_message(creds: Credentials, message_id: str, label_id: str) -> None:
    svc = _service(creds)
    svc.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id]},
    ).execute()


def export_message_debug_json(msg: FetchedMessage) -> dict[str, Any]:
    return {
        "message_id": msg.message_id,
        "thread_id": msg.thread_id,
        "subject": msg.subject,
        "internal_date_ms": msg.internal_date_ms,
        "snippet": msg.snippet,
        "attachments": [
            {"filename": a.filename, "mime_type": a.mime_type, "size": len(a.data)}
            for a in msg.attachments
        ],
    }
