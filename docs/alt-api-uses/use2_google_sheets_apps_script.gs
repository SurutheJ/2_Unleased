/**
 * A5 Part 3.4 — Alternative use #2: pulling the public API into Google Sheets.
 *
 * Google Sheets has no built-in JSON importer (IMPORTDATA only understands
 * CSV/TSV), so this uses a few lines of Apps Script — Google Sheets' built-in
 * scripting language — to fetch the same public endpoint and write it as a
 * normal table of cells.
 *
 * How to run this:
 *   1. Open a blank Google Sheet.
 *   2. Extensions -> Apps Script.
 *   3. Delete the placeholder code and paste this file's contents.
 *   4. Click Run (the function importUnleasedListingsByStatus will execute).
 *   5. The first time, Google asks you to authorize the script to call
 *      an external URL and edit the sheet — click Allow.
 *   6. Switch back to the Sheet tab: a "Status" / "Total" table appears,
 *      pulled live from the production Unleased API.
 */
function importUnleasedListingsByStatus() {
  var url = 'https://parulmudaliar.pythonanywhere.com/listings/api/by-status/';
  var response = UrlFetchApp.fetch(url);
  var rows = JSON.parse(response.getContentText());  // [{status: "...", total: N}, ...]

  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  sheet.clear();
  sheet.appendRow(['Status', 'Total']);
  rows.forEach(function (row) {
    sheet.appendRow([row.status, row.total]);
  });
}
