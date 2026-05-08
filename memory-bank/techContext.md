# Technical context

## Stack

- Python 3.10+, Gmail API + Sheets API (OAuth desktop client).
- Daily runner: cron or CI invoking `python -m gam_ingestion.run`.
- **clasp** (`apps-script/package.json`): `cd apps-script && npm install && npx clasp login && npm run pull`.

## External IDs

| Resource | Value |
|----------|--------|
| Penske KVP GAM spreadsheet | `1TDZGpXNrQ7qoH9oePzx0KKSrBKY3iHYXIcG_5AN9VRE` |
| Worksheet tab | `Data` |
| Apps Script project | `1h7Ad1fzEw2BlNRgbU6s3YlzIlkxWiRkQyf-aEoxOLLZHYn7UwtaA2nv5` |

Apps Script is documented for operator reference; the repo ingest path does not call the Apps Script API unless extended later.
