# Active context

## Current state

- Initial Python ingestion pipeline added: Gmail search → CSV attachment → Google Sheets append with label-based deduplication.

## Destination sheet

- **Penske KVP GAM** spreadsheet ID `1TDZGpXNrQ7qoH9oePzx0KKSrBKY3iHYXIcG_5AN9VRE`, tab **`Data`** (see `.env.example` and README for URL).

## Apps Script

- Project ID `1h7Ad1fzEw2BlNRgbU6s3YlzIlkxWiRkQyf-aEoxOLLZHYn7UwtaA2nv5`; clasp root `apps-script/` (`npm install`, `clasp login`, `npm run pull`).
- **Ingest:** `Ingest.gs` — **`ingestGmailReportToSheet`** verified: **2 threads**, **31 + 17** rows from **`PMC _ Mula Report.csv`**, `processed=2`, append uses **`getRange(..., numRows, numCols)`** correctly.
- **Triggers:** `scheduledRun()` runs the same ingest daily for new mail (already labeled threads skipped).

## Next steps for operators

1. Create GCP OAuth client and enable Gmail + Sheets APIs.
2. ~~Confirm OAuth account can edit the workbook~~ — workbook shared with that Google account; tab **`Data`** must still exist.
3. Run once locally to complete OAuth and validate a real email (use the **same** account for Gmail + Sheets if mail lives in that inbox).
4. Schedule daily run (cron or CI).

## Report format

- PMC Mula CSV: columns `Date`, `Key-values`, `Ad unit (top level)`, `Device category`, `Total impressions`; attachment name `PMC _ Mula Report.csv`. Regex example in `.env.example` / README.
- Example subjects: `Report: PMC | Mula Report …` (makemula inbox) or alternate `Mula Inc Mail - Report_ …`; Gmail query default uses quoted phrase `"PMC _ Mula Report"` + filters — verified **2 threads** for **logan@makemula.ai** with debug run.

## Open items

- Add `from:...` to `GAM_GMAIL_QUERY` only if another sender collides with the subject filter.
- If reports are not CSV, extend parsers beyond `csv_extract.py`.
