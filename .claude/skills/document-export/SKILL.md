---
name: document-export
description: Create a PDF, Excel (.xlsx), or Word (.docx) file from content. Use for "/document-export", "make a PDF", "export to Excel", "put this in a spreadsheet", "save this as a Word doc", or when the user needs a shareable office document rather than a note or a raw HTML page.
---

# Document Export

Turn content into a real office file: a **PDF**, an **Excel workbook**, or a
**Word document**. The skill ships three helper scripts that do the file writing
deterministically; your job is to assemble the content and call the right one.

These scripts use the Python standard library only, so there is nothing to
install for Excel and Word. PDF needs a browser or a PDF tool on the machine
(the script finds it, or tells the user what to install).

Save every output to `reports/` as `YYYY-MM-DD-<slug>.<ext>`, then tell the user
the path.

## PDF

PDF is produced by rendering an HTML file. Two cases:

- **Rich, visual page** (architecture, dashboard, comparison): use the
  `visual-explainer` skill to build the HTML, then convert it.
- **Plain document** (a letter, a report, a write-up): wrap the content in this
  minimal template and save it as an `.html` file:

```html
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>TITLE</title>
<style>
  @page { margin: 2cm; }
  body { font: 11pt/1.55 -apple-system, "Segoe UI", Roboto, sans-serif;
         color: #1a1a1a; max-width: 46em; margin: 0 auto; }
  h1, h2, h3 { line-height: 1.25; }
  h1 { font-size: 1.8em; } h2 { font-size: 1.35em; margin-top: 1.6em; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; }
  code { background: #f4f4f4; padding: 1px 4px; border-radius: 3px; }
</style></head><body>
  <!-- CONTENT -->
</body></html>
```

Then convert:

```bash
python3 .claude/skills/document-export/to_pdf.py <input.html> reports/<YYYY-MM-DD>-<slug>.pdf
```

It tries headless Chrome first, then weasyprint, then wkhtmltopdf. If it reports
that no engine is found, relay its install hint to the user; do not try to work
around it.

## Excel (.xlsx)

Build a JSON spec, write it to a temporary file, and run the writer.

Spec shape:

```json
{
  "sheets": [
    {
      "name": "Results",
      "header": true,
      "rows": [["Name", "Score"], ["Alice", 90], ["Bob", 85]],
      "widths": [24, 10]
    }
  ]
}
```

- `header: true` bolds the first row. `widths` (column widths in characters) is
  optional. Multiple sheets are allowed.
- Cell values may be strings, numbers, booleans, or `null` (an empty cell).
  Keep numbers as numbers in the JSON so Excel treats them as numeric.

Run it:

```bash
python3 .claude/skills/document-export/to_xlsx.py /tmp/export-spec.json reports/<YYYY-MM-DD>-<slug>.xlsx
```

You can also pipe the spec on stdin by passing `-` instead of a file path.

## Word (.docx)

Build a JSON spec of blocks, then run the writer.

Spec shape:

```json
{
  "title": "Optional document title",
  "blocks": [
    {"type": "heading", "level": 2, "text": "A section"},
    {"type": "paragraph", "text": "A plain paragraph."},
    {"type": "paragraph", "runs": [
      {"text": "mixed ", "bold": true},
      {"text": "formatting", "italic": true}
    ]},
    {"type": "bullets",  "items": ["first point", "second point"]},
    {"type": "numbered", "items": ["step one", "step two"]},
    {"type": "table", "header": true, "rows": [["Col A", "Col B"], ["1", "2"]]}
  ]
}
```

- `heading` levels are 1 to 3. A `paragraph` carries plain `text` (with optional
  `bold` / `italic` for the whole paragraph) or a list of `runs` for mixed
  formatting. `table` rows are lists of cell strings; `header: true` bolds the
  first row.

Run it:

```bash
python3 .claude/skills/document-export/to_docx.py /tmp/export-spec.json reports/<YYYY-MM-DD>-<slug>.docx
```

## After exporting

- Delete any temporary spec file you created.
- Give the user the exact path of the file.
- If the user wants to share the file, that is an outward action: hand it over,
  do not send it anywhere yourself.

## Scope

These writers cover the structure that carries content: values, headings,
formatting, lists, simple tables, column widths. They do not do Excel formulas,
charts, or merged cells, or Word images, footnotes, or page headers. If a
request needs those, say so and either extend the script or, if the user has the
`openpyxl` or `python-docx` library available, write a one-off script with it
instead.
