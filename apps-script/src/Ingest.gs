/**
 * Gmail → CSV → Sheet ingest (same behavior as Python gam_ingestion.run).
 * Configure via Project Settings → Script properties (see README), or rely on defaults below.
 */

var META_KEYS_ = [
  'gmail_message_id',
  'gmail_internal_date_ms',
  'email_subject',
  'attachment_filename',
];

/**
 * Main entry: search Gmail, append matching CSV rows to the sheet, label processed messages.
 */
function ingestGmailReportToSheet() {
  var cfg = getIngestConfig_();
  Logger.log(
    'ingest: query=%s maxThreads=%s dryRun=%s',
    cfg.gmailQuery,
    cfg.maxThreads,
    cfg.dryRun
  );
  var label = getOrCreateLabel_(cfg.processedLabel);
  var threads = GmailApp.search(cfg.gmailQuery, 0, cfg.maxThreads);
  var processed = 0;
  var skipped = 0;

  for (var t = 0; t < threads.length; t++) {
    var thread = threads[t];
    if (threadHasLabel_(thread, cfg.processedLabel)) {
      skipped++;
      continue;
    }

    var msg = findMessageWithAttachment_(thread, cfg.attachmentRegex);
    if (!msg) {
      Logger.log('No matching CSV in thread; skip (no label).');
      skipped++;
      continue;
    }

    var att = msg.picked;
    var blob = att.copyBlob();
    var text = stripBom_(blob.getDataAsString('UTF-8'));
    var table = Utilities.parseCsv(text);
    if (!table || table.length === 0) {
      skipped++;
      continue;
    }

    var header = table[0].map(function (h) {
      return (h || '').toString().trim();
    });
    var dataRows = [];
    for (var r = 1; r < table.length; r++) {
      var row = table[r];
      if (!row || row.every(function (c) { return !(c && String(c).trim()); })) {
        continue;
      }
      var padded = row.slice();
      while (padded.length < header.length) {
        padded.push('');
      }
      dataRows.push(padded.slice(0, header.length));
    }

    if (header.length === 0) {
      skipped++;
      continue;
    }

    var meta = {
      gmail_message_id: msg.message.getId(),
      gmail_internal_date_ms: String(msg.message.getDate().getTime()),
      email_subject: msg.message.getSubject() || '',
      attachment_filename: att.getName() || '',
    };

    var ss = SpreadsheetApp.openById(cfg.spreadsheetId);
    var sheet = ss.getSheetByName(cfg.sheetTab);
    if (!sheet) {
      throw new Error('Missing tab: ' + cfg.sheetTab);
    }

    var existingHeader = getFirstRowValues_(sheet);
    var isEmpty = !existingHeader || existingHeader.length === 0 ||
      existingHeader.every(function (c) { return c === '' || c === null; });

    var built;
    try {
      built = buildSheetRows_(meta, header, dataRows, isEmpty ? null : existingHeader);
    } catch (e) {
      Logger.log('Column mismatch: %s', e.message);
      skipped++;
      continue;
    }

    var toWrite = built.rows;
    if (isEmpty && built.headerRow) {
      toWrite = [built.headerRow].concat(built.rows);
    }

    if (!cfg.dryRun && toWrite.length > 0) {
      appendRows_(sheet, toWrite);
      // GmailMessage.addLabel is not always available; GmailThread.addLabel labels the whole thread.
      thread.addLabel(label);
    } else if (cfg.dryRun) {
      Logger.log('DRY_RUN: would append %s rows', toWrite.length);
    }

    processed++;
    Logger.log('Ingested message %s rows=%s file=%s', meta.gmail_message_id, built.rows.length, meta.attachment_filename);
  }

  Logger.log('Done. processed=%s skipped=%s candidates=%s', processed, skipped, threads.length);
}

/**
 * Debug: logs the query from Script properties + how many threads match.
 * If count is 0, paste the same query into the Gmail web UI search box — if it finds mail there,
 * the Apps Script project may be running as a different Google account than the inbox you checked.
 */
function debugGmailIngestSearch() {
  var cfg = getIngestConfig_();
  Logger.log('--- debugGmailIngestSearch ---');
  Logger.log(
    'Apps Script runs as this Google account (must be the inbox that RECEIVES the report): %s',
    Session.getEffectiveUser().getEmail()
  );
  var active = Session.getActiveUser().getEmail();
  if (active) {
    Logger.log('Active user: %s', active);
  }

  Logger.log('Effective query: %s', cfg.gmailQuery);
  var threads = GmailApp.search(cfg.gmailQuery, 0, 20);
  Logger.log('Matching threads (max 20): %s', threads.length);
  for (var i = 0; i < threads.length; i++) {
    var msgs = threads[i].getMessages();
    var last = msgs[msgs.length - 1];
    Logger.log('  id=%s subject=%s', threads[i].getId(), last.getSubject());
  }
  // Phrase search (matches Gmail web UI when you type "PMC _ Mula Report"); subject: can miss matches.
  var fallback = '"PMC _ Mula Report" newer_than:180d';
  var alt = GmailApp.search(fallback, 0, 10);
  Logger.log('Fallback "%s" -> %s threads', fallback, alt.length);

  // Broad probes — if these are all 0, this mailbox has no such mail (wrong account or never received).
  var probes = [
    '"PMC _ Mula Report"',
    'in:anywhere newer_than:180d "PMC _ Mula Report"',
    'in:anywhere newer_than:180d subject:(Mula Inc Mail)',
    'in:anywhere newer_than:180d PMC Mula has:attachment',
    'in:anywhere newer_than:365d from:mula',
  ];
  for (var p = 0; p < probes.length; p++) {
    var q = probes[p];
    var sample = GmailApp.search(q, 0, 25);
    var n = sample.length;
    Logger.log('Probe (%s threads): %s', n, q);
    var show = Math.min(n, 3);
    for (var t = 0; t < show; t++) {
      var msgs = sample[t].getMessages();
      var subj = msgs[msgs.length - 1].getSubject();
      Logger.log('  sample subject: %s', subj);
    }
  }
}

/**
 * One-time helper: copy defaults into Script properties (edit values, then run once).
 */
function setupDefaultScriptProperties() {
  var p = PropertiesService.getScriptProperties();
  p.setProperties({
    GAM_SPREADSHEET_ID: '1TDZGpXNrQ7qoH9oePzx0KKSrBKY3iHYXIcG_5AN9VRE',
    GAM_SHEET_TAB: 'Data',
    // Quoted phrase matches Gmail UI search; subject:"..." often behaves differently in GmailApp.
    GAM_GMAIL_QUERY: '"PMC _ Mula Report" has:attachment newer_than:180d in:anywhere',
    GAM_ATTACHMENT_REGEX: 'PMC\\s+_\\s+Mula\\s+Report\\.csv',
    GAM_PROCESSED_LABEL: 'GAM/Ingested',
    GAM_DRY_RUN: 'false',
    GAM_MAX_THREADS: '50',
  }, true);
  Logger.log('Script properties set. Review in Project Settings → Script properties.');
}

function getIngestConfig_() {
  var p = PropertiesService.getScriptProperties();
  var gmailQuery = p.getProperty('GAM_GMAIL_QUERY') ||
    '"PMC _ Mula Report" has:attachment newer_than:180d in:anywhere';
  var maxThreads = parseInt(p.getProperty('GAM_MAX_THREADS') || '50', 10);
  if (isNaN(maxThreads) || maxThreads < 1) {
    maxThreads = 50;
  }
  var dryVal = (p.getProperty('GAM_DRY_RUN') || '').toLowerCase();
  return {
    spreadsheetId: p.getProperty('GAM_SPREADSHEET_ID') || SPREADSHEET_ID,
    sheetTab: p.getProperty('GAM_SHEET_TAB') || SHEET_TAB,
    gmailQuery: gmailQuery,
    attachmentRegex: (p.getProperty('GAM_ATTACHMENT_REGEX') || '').trim(),
    processedLabel: p.getProperty('GAM_PROCESSED_LABEL') || 'GAM/Ingested',
    dryRun: dryVal === '1' || dryVal === 'true' || dryVal === 'yes',
    maxThreads: maxThreads,
  };
}

function getOrCreateLabel_(name) {
  var label = GmailApp.getUserLabelByName(name);
  if (!label) {
    label = GmailApp.createLabel(name);
  }
  return label;
}

function threadHasLabel_(thread, labelName) {
  var labels = thread.getLabels();
  for (var i = 0; i < labels.length; i++) {
    if (labels[i].getName() === labelName) {
      return true;
    }
  }
  return false;
}

/**
 * Newest message first; first attachment matching regex or .csv if regex empty.
 * @return {{message: GmailMessage, picked: GmailAttachment}|null}
 */
function findMessageWithAttachment_(thread, attachmentRegex) {
  var messages = thread.getMessages();
  var re = null;
  if (attachmentRegex) {
    try {
      re = new RegExp(attachmentRegex, 'i');
    } catch (e) {
      throw new Error('Invalid GAM_ATTACHMENT_REGEX: ' + e.message);
    }
  }
  for (var i = messages.length - 1; i >= 0; i--) {
    var message = messages[i];
    var attachments = message.getAttachments();
    for (var a = 0; a < attachments.length; a++) {
      var name = attachments[a].getName() || '';
      if (re) {
        if (re.test(name)) {
          return { message: message, picked: attachments[a] };
        }
      } else if (/\.csv$/i.test(name)) {
        return { message: message, picked: attachments[a] };
      }
    }
  }
  return null;
}

function stripBom_(s) {
  if (s && s.charCodeAt(0) === 0xfeff) {
    return s.substring(1);
  }
  return s;
}

function getFirstRowValues_(sheet) {
  if (sheet.getLastRow() < 1) {
    return null;
  }
  var lastCol = Math.max(sheet.getLastColumn(), 1);
  var row = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  return row.map(function (c) {
    return c === null || c === undefined ? '' : String(c);
  });
}

/**
 * @return {{headerRow: Array|null, rows: Array<Array>}}
 */
function buildSheetRows_(meta, csvHeader, dataRows, existingHeader) {
  var metaVals = META_KEYS_.map(function (k) {
    return meta[k];
  });
  if (!existingHeader) {
    var fullHeader = META_KEYS_.concat(csvHeader);
    var out = [];
    for (var i = 0; i < dataRows.length; i++) {
      out.push(metaVals.concat(dataRows[i]));
    }
    return { headerRow: fullHeader, rows: out };
  }
  var prefix = existingHeader.slice(0, META_KEYS_.length);
  for (var p = 0; p < META_KEYS_.length; p++) {
    if (prefix[p] !== META_KEYS_[p]) {
      throw new Error('Sheet header prefix must match ingest columns');
    }
  }
  var tail = existingHeader.slice(META_KEYS_.length);
  if (tail.length !== csvHeader.length) {
    throw new Error('CSV column count does not match sheet');
  }
  for (var c = 0; c < tail.length; c++) {
    if (tail[c] !== csvHeader[c]) {
      throw new Error('CSV columns do not match sheet header');
    }
  }
  var rows = [];
  for (var r = 0; r < dataRows.length; r++) {
    rows.push(metaVals.concat(dataRows[r]));
  }
  return { headerRow: null, rows: rows };
}

/**
 * Writes a rectangular matrix; pads columns using max width across all rows.
 * Coerces values to primitives so setValues never sees ragged rows or nested structures.
 */
function appendRows_(sheet, rows2d) {
  if (!rows2d || rows2d.length === 0) {
    return;
  }

  var matrix = [];
  var maxCols = 0;

  for (var i = 0; i < rows2d.length; i++) {
    var row = rows2d[i];
    var cells = [];

    if (!Array.isArray(row)) {
      var one = Utilities.parseCsv(String(row));
      row = one.length ? one[0] : [String(row)];
    }

    for (var c = 0; c < row.length; c++) {
      var v = row[c];
      if (v === null || v === undefined) {
        cells.push('');
      } else if (v instanceof Date) {
        cells.push(v);
      } else {
        cells.push(String(v));
      }
    }

    maxCols = Math.max(maxCols, cells.length);
    matrix.push(cells);
  }

  for (var j = 0; j < matrix.length; j++) {
    while (matrix[j].length < maxCols) {
      matrix[j].push('');
    }
  }

  var numRows = matrix.length;
  var numCols = maxCols;
  var startRow = sheet.getLastRow() + 1;

  // Sheet.getRange(row, column, numRows, numColumns) — 3rd arg is ROW COUNT, not last row index.
  Logger.log('appendRows_: startRow=%s numRows=%s numCols=%s', startRow, numRows, numCols);

  if (numCols < 1) {
    throw new Error('appendRows_: empty column count');
  }

  sheet.getRange(startRow, 1, numRows, numCols).setValues(matrix);
}
