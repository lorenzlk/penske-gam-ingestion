# Progress

Derived from `progress.jsonl`. Do not edit by hand; append events to the JSONL file.

## 2026-05-08

- **change**: Added Python Gmail→Sheets ingestion for GAM CSV email attachments (OAuth, env config, label deduplication, README). **Implication**: Operators configure GCP OAuth, spreadsheet ID, and Gmail query; CSV columns must remain consistent across ingests.

- **change**: Documented Penske PMC Mula report columns and `PMC _ Mula Report.csv` attachment regex; added `samples/pmc_mula_report.sample.csv`; gitignored local full downloads. **Implication**: Set `GAM_ATTACHMENT_REGEX` when ingesting this report; avoid committing live CSV exports.

- **decision**: Documented example subject `Mula Inc Mail - Report_ PMC _ Mula Report …` and default `GAM_GMAIL_QUERY=subject:"PMC _ Mula Report"` so weekly date ranges in the subject do not break search; `.env.example` ships with attachment regex enabled. **Implication**: Add sender filter only if another message shares the same subject tokens.

- **constraint**: Penske KVP GAM spreadsheet ID `1TDZGpXNrQ7qoH9oePzx0KKSrBKY3iHYXIcG_5AN9VRE` and link documented in `.env.example` and README. **Implication**: Service account or user OAuth must have edit access; tab name in `GAM_SHEET_TAB` must exist.

- **correction**: Default tab name is **`Data`** (not `GAM_Data`) across `.env.example`, `gam_ingestion/config.py`, and README.

- **constraint**: Apps Script project ID `1h7Ad1fzEw2BlNRgbU6s3YlzIlkxWiRkQyf-aEoxOLLZHYn7UwtaA2nv5` recorded in README and `memory-bank/techContext.md` (reference only for the Python CLI).

- **change**: clasp wired via `apps-script/` (`@google/clasp`, `.clasp.json` → `src/`), README instructions, `node_modules` gitignored. **Implication**: Run `clasp login` once per machine, then `npm run pull` to populate `src/`.

- **constraint**: Spreadsheet shared with the OAuth Google account so Sheets API append will work for that identity after authorization.

- **change**: Apps Script `Code.gs` adds daily trigger installer + `scheduledRun` placeholder; README documents run-once flow.

- **correction**: `appsscript.json` lives under `apps-script/src/` for clasp `rootDir`; `npm run push:force` / `clasp push --force` when push is skipped.

- **change**: Root `package.json` adds `npm run clasp:push:force` (and related) so clasp works from repo root without `cd apps-script`.

- **change**: Apps Script daily trigger live; first `scheduledRun` log showed **Data** tab `lastRow` 0 (sheet empty until ingest).

- **decision**: Apps Script **`Ingest.gs`** implements the same ingest as Python; config via Script properties; **`scheduledRun`** invokes it. **Implication**: `clasp push` + Gmail authorization after deploy.

- **change**: End-to-end Apps Script ingest confirmed (2 Mula reports → 31 + 17 rows on **Data**; `GAM/Ingested` applied).

- **change**: Git repo initialized; remote [penske-gam-ingestion](https://github.com/lorenzlk/penske-gam-ingestion); `main` pushed; `*.pdf` gitignored (local report PDF not committed).
