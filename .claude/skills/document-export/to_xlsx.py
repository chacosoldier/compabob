#!/usr/bin/env python3
"""Compabob document-export: build a .xlsx workbook from a JSON spec.

Standard library only. No openpyxl, no pandas. It hand-writes a minimal but
valid Office Open XML spreadsheet that opens in Excel, Numbers, and LibreOffice.

  usage: python3 to_xlsx.py <spec.json> <output.xlsx>
         python3 to_xlsx.py -          <output.xlsx>   # spec read from stdin

Spec JSON:
{
  "sheets": [
    {
      "name": "Results",
      "header": true,                       # bold the first row (optional)
      "rows": [["Name", "Score"], ["Alice", 90], ["Bob", 85]],
      "widths": [24, 10]                    # column widths, chars (optional)
    }
  ]
}

Cell values may be strings, numbers (int/float), booleans, or null (an empty
cell). This writer covers values, a bold header row, and column widths. It does
not do formulas, charts, merged cells, or themes; extend it if you need those.
"""
from __future__ import annotations

import json
import os
import sys
import zipfile

XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def esc(value: object) -> str:
    return (
        str(value).replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )


def col_letter(index: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA."""
    letters = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def cell_xml(ref: str, value: object, bold: bool) -> str:
    style = ' s="1"' if bold else ""
    if value is None or value == "":
        return f'<c r="{ref}"{style}/>'
    if isinstance(value, bool):
        return f'<c r="{ref}"{style} t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"{style}><v>{value}</v></c>'
    return (
        f'<c r="{ref}"{style} t="inlineStr">'
        f'<is><t xml:space="preserve">{esc(value)}</t></is></c>'
    )


def sheet_xml(sheet: dict) -> str:
    rows = sheet.get("rows", []) or []
    header = bool(sheet.get("header", False))
    widths = sheet.get("widths") or []

    cols = ""
    col_parts = [
        f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
        for i, w in enumerate(widths, start=1) if w
    ]
    if col_parts:
        cols = "<cols>" + "".join(col_parts) + "</cols>"

    body = []
    for r_index, row in enumerate(rows, start=1):
        bold = header and r_index == 1
        cells = "".join(
            cell_xml(f"{col_letter(c_index)}{r_index}", value, bold)
            for c_index, value in enumerate(row, start=1)
        )
        body.append(f'<row r="{r_index}">{cells}</row>')

    return (
        XML_DECL
        + '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + cols
        + "<sheetData>" + "".join(body) + "</sheetData>"
        + "</worksheet>"
    )


STYLES_XML = XML_DECL + (
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="2">'
    '<font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font>'
    '</fonts>'
    '<fills count="2">'
    '<fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill>'
    '</fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="2">'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    '</cellXfs>'
    '</styleSheet>'
)

RELS_XML = XML_DECL + (
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="xl/workbook.xml"/>'
    '</Relationships>'
)


def build(spec: dict, output: str) -> None:
    sheets = spec.get("sheets") or []
    if not sheets:
        raise ValueError("spec needs at least one entry in 'sheets'.")

    count = len(sheets)
    content_types = [
        XML_DECL,
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for i in range(1, count + 1):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append("</Types>")

    sheet_tags = "".join(
        f'<sheet name="{esc(sheet.get("name") or f"Sheet{i}")}" '
        f'sheetId="{i}" r:id="rId{i}"/>'
        for i, sheet in enumerate(sheets, start=1)
    )
    workbook = XML_DECL + (
        '<workbook '
        'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheet_tags}</sheets></workbook>"
    )

    rel_tags = "".join(
        f'<Relationship Id="rId{i}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, count + 1)
    )
    rel_tags += (
        f'<Relationship Id="rId{count + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    workbook_rels = XML_DECL + (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + rel_tags + "</Relationships>"
    )

    parent = os.path.dirname(os.path.abspath(output))
    os.makedirs(parent, exist_ok=True)

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "".join(content_types))
        zf.writestr("_rels/.rels", RELS_XML)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/styles.xml", STYLES_XML)
        for i, sheet in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml(sheet))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: to_xlsx.py <spec.json|-> <output.xlsx>", file=sys.stderr)
        return 2
    spec_arg, output = sys.argv[1], sys.argv[2]
    try:
        raw = sys.stdin.read() if spec_arg == "-" else open(
            spec_arg, encoding="utf-8"
        ).read()
        spec = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"could not read spec: {exc}", file=sys.stderr)
        return 2
    try:
        build(spec, output)
    except (ValueError, TypeError, KeyError) as exc:
        print(f"could not build workbook: {exc}", file=sys.stderr)
        return 1
    print(f"xlsx written: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
