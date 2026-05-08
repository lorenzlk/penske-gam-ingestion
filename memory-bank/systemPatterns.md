# System patterns

## Layout

- `gam_ingestion/` — library code (config, Gmail, Sheets, CSV parsing, runner).
- `scripts/ingest_gam_to_sheet.py` — optional entry that adds repo root to `sys.path`.
- `apps-script/` — clasp project (`npm install`, `.clasp.json`, `src/` for `.gs` / `.html`). `Code.gs` triggers; `Ingest.gs` Gmail→Sheet (Script properties mirror `.env` keys).
- `.env` — local configuration (not committed).

## Conventions

- OAuth desktop flow; token stored in `token.json`.
- Environment variables prefixed with `GAM_` for ingest settings, `GOOGLE_OAUTH_*` for auth files.

## Continuity files

- `techContext.md` holds spreadsheet tab name, spreadsheet ID, Apps Script project ID, and stack notes.
