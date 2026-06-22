# Exports (user-facing CSV / PDF)

Confirmed against **version_code 252**. Mapped classes: `CsvExportModule`,
`CsvExportTask`, `CsvExportView`, `PdfExportModule`, `PdfExportRenderer`,
`PdfExportView`, `PdfExportSettingsView`.

This is the user's "export my data" feature, **distinct** from the Google-Drive
`.daylio` backup (see [backups](backups.md)).

## Entry point

`ExportEntriesActivity` (kept name) is the hub. It hosts two MVP-style share
tiles plus two asset toggles (photos / voice memos — out of scope here):

- **CSV tile** → view `zf.b` → module interface `z8`, impl `CsvExportModule`
- **PDF tile** → view `sg.a` (abstract; concrete `zf.c` in the activity, screen
  `"export_pdf"`) → module interface `a9`, impl `PdfExportModule` → renderer
  `PdfExportRenderer`

Both share the finished file via `Intent.ACTION_SEND` + a FileProvider URI
(authority `<pkg>.fileprovider`). Files: `filesDir/export/daylio_export_<yyyy_MM_dd>.{csv,pdf}`.

## CSV — schema (the load-bearing detail)

`CsvExportTask` (the inner AsyncTask of the CSV module) writes a fixed header
then one row per entry, in this exact column order:

```
full_date,date,weekday,time,mood,activities,scales,note_title,note
```

- `full_date` — `yyyy-MM-dd` (`SimpleDateFormat`, `Locale.US`)
- `date` — localized date, commas replaced with `.`
- `weekday` — localized `EEEE`, commas replaced with `.`
- `time` — localized time-of-day
- `mood` — localized mood name
- `activities` — quoted, `tag1 | tag2 | …`
- `scales` — quoted, `scaleName:<nbsp>value | …`
- `note_title` / `note` — quoted; newlines collapsed to spaces; `"` escaped to
  `""` (RFC-4180-ish)

Rows are joined with `System.getProperty("line.separator")`. `CsvExportModule`
writes a **UTF-8 BOM** (`EF BB BF`) then the body via a UTF-8 `PrintWriter`.

**Quirk:** the CSV share intent sets MIME **`text/html`**, not `text/csv` — and
no `text/csv` string exists anywhere in the app. Don't anchor future work on
`text/csv`. Analytics event: `csv_export_generated`.

## PDF — layout

`PdfExportRenderer` (an AsyncTask) renders into `android.graphics.pdf.PdfDocument`.
Page geometry ≈ **496 × 702 dp** portrait, 35 dp margins, density forced to 3.0
during render. It inflates `pdf_export_*` layouts (header, per-day-entry header
with mood/tags/scales mini-rows, note title, note body, photo assets, an optional
count-summary grid), measures each `View`, draws it on the page `Canvas`, and
starts a new page when the running height overflows.

Options (period, newest/oldest order, color vs grayscale via a desaturating
`ColorMatrixColorFilter`, photo size off/small/large, counts-summary toggle)
persist in `ad.c` prefs. Output file `daylio_export_<date>.pdf`; share via
`PdfExportView.onPdfReady(File)` → `ACTION_SEND`, SUBJECT `"Daylio PDF Export"`,
MIME `application/pdf`. Analytics: `pdf_export_generated`.

## Premium gating

- **CSV is free** — `CsvExportView` click → `CsvExportModule.startCsvExport()`
  directly, no gate.
- **PDF is premium-gated** — the generate button in `PdfExportView` /
  `PdfExportSettingsView` checks the premium flag (`ad.c.D`, see
  [premium](premium.md)); when false it launches a purchase screen
  (`of.b5.i(ctx, "export_pdf_settings")`) instead of generating. (A separate
  feature flag that gates *showing* the PDF tile is `@Deprecated` and hard-returns
  `true`, so the tile is always visible.)

## Out of scope / notes

- The photo / voice-memo **ZIP** export reachable from the same screen (presenter
  `net.daylio.modules.ui.q1`, MIME `application/zip`, `daylio_export_*.zip` built
  by `net.daylio.modules.business.t`) belongs to the assets/backup side and is
  not mapped here. (`daylio_export_` is a shared filename prefix, which is why CSV
  and PDF are anchored on their extensions/strings, not the prefix.)
- `ExportEntriesActivity` / `ExportPdfSettingsActivity` keep their names but their
  self-name strings recur across unrelated files, so the outer classes aren't
  cleanly anchorable — they're already readable landmarks anyway.
- "`...View`" in the logical names is Daylio's **MVP-layer** terminology — these
  are presenters, not Android `View` subclasses.
