# Penske GAM Ingestion

Daily job that reads **Google Ad Manager** notification emails from Gmail, extracts the **CSV attachment**, and **appends rows** to a Google Sheet for downstream reporting.

You can run that flow either as **Python** (local / CI + `.env`) or **entirely in Google Apps Script** (time-driven trigger + Script properties — no `credentials.json`).

## What it does

1. Runs a Gmail search (`GAM_GMAIL_QUERY`) for messages not yet labeled.
2. Finds the first `.csv` attachment (or one matching `GAM_ATTACHMENT_REGEX`).
3. Parses the CSV and appends rows to the configured tab.
4. Applies a Gmail label (`GAM_PROCESSED_LABEL`) so the same email is not ingested twice.

**Duplicate guard:** before appending, both Python and Apps Script read **`gmail_message_id`** values already in **column A**. If a message id is already present, that message is **skipped** (no duplicate rows). The ingest label is still applied so Gmail stays in sync. After you clear the sheet, existing ids are gone—either rely on labels until you remove them, or accept that those threads could be re-imported once.

The sheet gets four leading columns on every row:

`gmail_message_id`, `gmail_internal_date_ms`, `email_subject`, `attachment_filename`, then the CSV columns from the report.

The **first successful run** writes the header row; later runs must use reports with the **same CSV columns** as row 1 (the script verifies this).

## Prerequisites

- Python 3.10+
- Google Cloud project with **Gmail API** and **Google Sheets API** enabled
- OAuth **Desktop** client (`credentials.json`) with the scopes used in `gam_ingestion/google_auth.py`
- Destination spreadsheet **Penske KVP GAM** (`GAM_SPREADSHEET_ID` is preset in `.env.example`):  
  https://docs.google.com/spreadsheets/d/1TDZGpXNrQ7qoH9oePzx0KKSrBKY3iHYXIcG_5AN9VRE/edit?gid=0#gid=0  
  Ensure the OAuth account has **edit** access, and that tab `GAM_SHEET_TAB` exists (default `Data`).

## Setup

```bash
cd /path/to/Penske-GAM-Ingestion
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your spreadsheet ID and Gmail query. Place `credentials.json` from Google Cloud next to the project (or set `GOOGLE_OAUTH_CLIENT_SECRETS`).

First auth run opens a browser and saves `token.json`:

```bash
python -m gam_ingestion.run
```

Optional: inspect one message without writing to Sheets:

```bash
python -m gam_ingestion.run --dump-message <GMAIL_MESSAGE_ID>
```

## Daily schedule

**macOS (cron)** — run as the user who owns the OAuth token:

```cron
15 7 * * * cd /path/to/Penske-GAM-Ingestion && . .venv/bin/activate && set -a && . .env && set +a && python -m gam_ingestion.run >> /tmp/gam-ingest.log 2>&1
```

**GitHub Actions** — store `credentials.json`, `token.json`, and `.env` values as encrypted secrets and invoke the same command on a schedule.

Tune `GAM_GMAIL_QUERY` so it matches **only** the scheduled report email you want (sender + subject). Narrow queries reduce accidental matches.

## Query tuning

If Google sends from a specific address (example only — verify in your inbox):

```env
GAM_GMAIL_QUERY=from:ads-noreply@google.com subject:"Your exact subject"
```

If the attachment name is fixed:

```env
GAM_ATTACHMENT_REGEX=^daily_report\\.csv$
```

## Penske PMC Mula report (`PMC _ Mula Report.csv`)

**Subject lines vary by sender.** Examples:

- `Report: PMC | Mula Report May 1 – 7, 2026` (observed for **makemula.ai** inbox)
- `Mula Inc Mail - Report_ PMC _ Mula Report Apr 30 – May 6, 2026` (alternate wording seen elsewhere)

The CSV attachment name stays **`PMC _ Mula Report.csv`**. Use a Gmail query that matches **stable** text (not the rolling dates). If **`subject:"..."`** returns nothing in Apps Script but the Gmail web UI finds mail for **`"PMC _ Mula Report"`**, use the **quoted phrase** form (see `.env.example`).

Examples:

```env
GAM_GMAIL_QUERY="\"PMC _ Mula Report\" has:attachment newer_than:180d in:anywhere"
```

```env
GAM_GMAIL_QUERY=subject:"PMC _ Mula Report"
```

If another mailbox sends similarly named mail, add `from:known-sender@...` once you confirm the From address in Gmail.

Exports use comma-separated UTF-8 with this header row:

`Date`, `Key-values`, `Ad unit (top level)`, `Device category`, `Total impressions`

To select this attachment when other `.csv` files are present:

```env
GAM_ATTACHMENT_REGEX=PMC\s+_\s+Mula\s+Report\.csv
```

A non-production schema sample lives at `samples/pmc_mula_report.sample.csv`. Keep full downloads out of git (see `.gitignore`).

## Google Apps Script + clasp

**Project ID:** `1h7Ad1fzEw2BlNRgbU6s3YlzIlkxWiRkQyf-aEoxOLLZHYn7UwtaA2nv5`  
**Web editor:** [script.google.com → project](https://script.google.com/home/projects/1h7Ad1fzEw2BlNRgbU6s3YlzIlkxWiRkQyf-aEoxOLLZHYn7UwtaA2nv5/edit)

The Apps Script sources are managed under `apps-script/` with **[clasp](https://github.com/google/clasp)**. With `rootDir: "src"`, the manifest must live at **`apps-script/src/appsscript.json`** (not the parent folder).

One-time setup:

```bash
cd apps-script
npm install
npx clasp login
npm run pull
```

From the **repository root**, you can use the same commands without `cd`:

```bash
npm run clasp:install
npm run clasp:login
npm run clasp:pull
npm run clasp:push:force
```

`clasp login` stores credentials under your user profile (`~/.clasprc.json`); it is not committed. After `pull`, script files from Google appear in `apps-script/src/` (you can remove `src/.gitkeep` once real files exist).

Common commands (run from `apps-script/`):

| npm script | clasp command |
|------------|----------------|
| `npm run pull` | Download cloud project → local |
| `npm run push` | Upload local → cloud |
| `npm run push:force` | Same as `clasp push --force` (use if clasp reports *Skipping push*) |
| `npm run open` | Open project in the browser |
| `npm run status` | Show tracked vs ignored files |

### Full ingest in Apps Script (no Python)

`apps-script/src/Ingest.gs` implements the same pipeline as `python -m gam_ingestion.run`: Gmail search → CSV attachment → append to Sheet → user label.

**Configuration — Script properties** (Apps Script editor → **Project Settings** → **Script properties**). Same names as `.env`:

| Property | Example | Required |
|----------|---------|----------|
| `GAM_GMAIL_QUERY` | `subject:"PMC _ Mula Report"` | Has default if unset |
| `GAM_ATTACHMENT_REGEX` | `PMC\s+_\s+Mula\s+Report\.csv` | Optional (first `.csv` wins if empty) |
| `GAM_SPREADSHEET_ID` | (Penske sheet ID) | Falls back to `Code.gs` constant |
| `GAM_SHEET_TAB` | `Data` | Falls back to `Code.gs` constant |
| `GAM_PROCESSED_LABEL` | `GAM/Ingested` | Optional |
| `GAM_DRY_RUN` | `true` / `false` | Optional |
| `GAM_MAX_THREADS` | `50` | Optional |

One-time: run **`setupDefaultScriptProperties`** once from the editor (then adjust values in Project Settings), or set properties manually.

**Run manually:** select **`ingestGmailReportToSheet`** → Run. First run will ask for **Gmail** and **Spreadsheet** access.

**Scheduled:** `scheduledRun()` calls **`ingestGmailReportToSheet()`** — use **`installDailyTrigger`** as before.

**Push updates:** `npm run clasp:push:force` from repo (or `cd apps-script`).

**Quotas:** Apps Script has Gmail and runtime limits; for heavy volume keep Python as an option.

**Troubleshooting `candidates=0`:** Gmail returned no threads for `GAM_GMAIL_QUERY`. Run **`debugGmailIngestSearch`** and read **Executions → View logs**. The first log line now includes **`Session.getEffectiveUser().getEmail()`** — that is the **only** mailbox `GmailApp.search` can see. Open **Gmail in a browser** signed in as **that exact address** and paste the same query into search; results must match. If probes in the log show threads and sample subjects, copy a stable phrase from the real subject into **`GAM_GMAIL_QUERY`**. If **all** probes return 0, the report is not in this account (different user, alias-only, or Google Group archive you do not own as Gmail).

### Time-driven trigger (daily)

`apps-script/src/Code.gs` defines:

| Function | Purpose |
|----------|---------|
| `installDailyTrigger(hour)` | Creates a **daily** trigger that runs `scheduledRun` at `hour` (0–23, **America/New_York** by default). Removes older `scheduledRun` triggers first. |
| `uninstallDailyTriggers()` | Deletes triggers that call `scheduledRun`. |
| `listTriggersDebug()` | Logs trigger IDs (check **Executions** / logs after running). |
| `scheduledRun()` | Calls **`ingestGmailReportToSheet()`** (Gmail → Sheet ingest). |

**Apply:** `cd apps-script && npm run push:force`, open the project in the browser, select **`installDailyTrigger`**, click **Run**, and approve authorization once. Confirm under **Triggers** (clock icon) in the Apps Script UI.

**Note:** If you previously used **`clasp pull`** and the cloud project already has files, merge sources before **`push`** so you do not overwrite remote code.

## Limitations

- Expects a **CSV** attachment. Other formats (PDF, inline HTML tables) are not parsed yet.
- All ingested reports must share the **same column layout** so appended rows align with the header row.

If your email has no CSV or a different format, share a sanitized sample and the ingestion logic can be extended.
