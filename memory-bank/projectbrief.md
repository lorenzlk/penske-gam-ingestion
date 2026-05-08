# Project brief

## Purpose

Ingest Google Ad Manager notification emails into a Google Sheet so upstream reporting jobs can read a single consolidated tab.

## Scope

- Gmail → CSV attachment → append rows to Sheets (daily automation via cron or CI).
- Idempotency via Gmail label after successful append.

## Constraints

- CSV reports must keep a stable column layout matching the sheet header row.
