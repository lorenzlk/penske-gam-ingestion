/**
 * Penske KVP GAM — Apps Script triggers + shared constants.
 * Full ingest: ingestGmailReportToSheet() in Ingest.gs (Gmail → CSV → Sheet).
 * Time zone for `.atHour()` comes from appsscript.json (America/New_York).
 */

var SPREADSHEET_ID = '1TDZGpXNrQ7qoH9oePzx0KKSrBKY3iHYXIcG_5AN9VRE';
var SHEET_TAB = 'Data';

/**
 * Create (or refresh) a daily time-driven trigger that runs scheduledRun at `hour` (0–23).
 * Run once from the Apps Script editor (▶) after deploy; safe to run again—dedupes same handler.
 *
 * @param {number} [hour=7] Hour in the script project time zone.
 */
function installDailyTrigger(hour) {
  hour = hour === undefined || hour === null ? 7 : hour;
  deleteTriggersForFunction_('scheduledRun');
  ScriptApp.newTrigger('scheduledRun')
    .timeBased()
    .everyDays(1)
    .atHour(hour)
    .create();
}

/** Remove time-driven triggers that invoke scheduledRun. */
function uninstallDailyTriggers() {
  deleteTriggersForFunction_('scheduledRun');
}

/**
 * Lists trigger IDs + handler names (View → Logs in editor after running).
 */
function listTriggersDebug() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    Logger.log('%s -> %s', t.getUniqueId(), t.getHandlerFunction());
  });
}

function deleteTriggersForFunction_(functionName) {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === functionName) {
      ScriptApp.deleteTrigger(t);
    }
  });
}

/**
 * Runs once per day when the trigger fires — Gmail Mula CSV → Sheet (see Ingest.gs).
 */
function scheduledRun() {
  ingestGmailReportToSheet();
}
