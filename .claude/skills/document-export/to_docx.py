#!/usr/bin/env python3
"""Compabob document-export: build a .docx document from a JSON spec.

Standard library only. No python-docx. It hand-writes a minimal but valid Office
Open XML word-processing document that opens in Word, Pages, and LibreOffice.

  usage: python3 to_docx.py <spec.json> <output.docx>
         python3 to_docx.py -          <output.docx>   # spec read from stdin

Spec JSON:
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
    {"type": "table", "header": true, "rows": [["Col A","Col B"],["1","2"]]}
  ]
}

A paragraph may carry plain "text" (with optional "bold"/"italic" for the whole
paragraph) or a list of "runs" for mixed formatting. This writer covers titles,
headings 1-3, paragraphs, bold/italic runs, bullet and numbered lists, and
simple tables. It does not do images, footnotes, or page headers; extend it if
you need those.
"""
from __future__ import annotations

import json
import os
import sys
import zipfile

XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def esc(value: object) -> str:
    return (
        str(value).replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )


def run_xml(text: str, bold: bool = False, italic: bool = False) -> str:
    rpr = ""
    if bold or italic:
        rpr = "<w:rPr>" + ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "") + "</w:rPr>"
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def para(runs: str, style: str | None = None, num_id: int | None = None) -> str:
    inner = ""
    if style:
        inner += f'<w:pStyle w:val="{style}"/>'
    if num_id:
        inner += f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/></w:numPr>'
    ppr = f"<w:pPr>{inner}</w:pPr>" if inner else ""
    return f"<w:p>{ppr}{runs}</w:p>"


def table_xml(rows: list, header: bool) -> str:
    sides = ("top", "left", "bottom", "right", "insideH", "insideV")
    borders = "<w:tblBorders>" + "".join(
        f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
        for s in sides
    ) + "</w:tblBorders>"
    tbl_pr = f'<w:tblPr><w:tblW w:w="0" w:type="auto"/>{borders}</w:tblPr>'
    trs = []
    for r_index, row in enumerate(rows):
        bold = header and r_index == 0
        cells = "".join(
            '<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/></w:tcPr>'
            + para(run_xml("" if cell is None else cell, bold=bold))
            + "</w:tc>"
            for cell in row
        )
        trs.append(f"<w:tr>{cells}</w:tr>")
    return f"<w:tbl>{tbl_pr}" + "".join(trs) + "</w:tbl>"


def block_xml(block: dict) -> str:
    kind = (block.get("type") or "paragraph").lower()

    if kind == "heading":
        level = block.get("level", 1)
        level = level if level in (1, 2, 3) else 1
        return para(run_xml(block.get("text", "")), style=f"Heading{level}")

    if kind == "paragraph":
        runs = block.get("runs")
        if runs:
            joined = "".join(
                run_xml(r.get("text", ""), r.get("bold", False), r.get("italic", False))
                for r in runs
            )
            return para(joined)
        return para(run_xml(
            block.get("text", ""),
            block.get("bold", False),
            block.get("italic", False),
        ))

    if kind == "bullets":
        return "".join(
            para(run_xml(item), style="ListParagraph", num_id=1)
            for item in block.get("items", [])
        )

    if kind == "numbered":
        return "".join(
            para(run_xml(item), style="ListParagraph", num_id=2)
            for item in block.get("items", [])
        )

    if kind == "table":
        return table_xml(block.get("rows", []), bool(block.get("header", False))) + "<w:p/>"

    # Unknown block type: render its text as a plain paragraph so nothing is lost.
    return para(run_xml(block.get("text", "")))


SECT_PR = (
    '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
)

STYLES_XML = XML_DECL + (
    f'<w:styles xmlns:w="{W}">'
    '<w:docDefaults><w:rPrDefault><w:rPr>'
    '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/>'
    '</w:rPr></w:rPrDefault>'
    '<w:pPrDefault><w:pPr>'
    '<w:spacing w:after="120" w:line="276" w:lineRule="auto"/>'
    '</w:pPr></w:pPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
    '<w:name w:val="Normal"/></w:style>'
    '<w:style w:type="paragraph" w:styleId="Title">'
    '<w:name w:val="Title"/><w:basedOn w:val="Normal"/>'
    '<w:pPr><w:spacing w:after="240"/></w:pPr>'
    '<w:rPr><w:b/><w:sz w:val="56"/></w:rPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="Heading1">'
    '<w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
    '<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/>'
    '<w:outlineLvl w:val="0"/></w:pPr>'
    '<w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="Heading2">'
    '<w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>'
    '<w:pPr><w:keepNext/><w:spacing w:before="200" w:after="100"/>'
    '<w:outlineLvl w:val="1"/></w:pPr>'
    '<w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="Heading3">'
    '<w:name w:val="heading 3"/><w:basedOn w:val="Normal"/>'
    '<w:pPr><w:keepNext/><w:spacing w:before="160" w:after="80"/>'
    '<w:outlineLvl w:val="2"/></w:pPr>'
    '<w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="ListParagraph">'
    '<w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/>'
    '<w:pPr><w:ind w:left="720"/></w:pPr></w:style>'
    '</w:styles>'
)

NUMBERING_XML = XML_DECL + (
    f'<w:numbering xmlns:w="{W}">'
    '<w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0">'
    '<w:numFmt w:val="bullet"/><w:lvlText w:val="&#8226;"/>'
    '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>'
    '<w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0">'
    '<w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/>'
    '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>'
    '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
    '<w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num>'
    '</w:numbering>'
)

CONTENT_TYPES = XML_DECL + (
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    '<Override PartName="/word/numbering.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
    '</Types>'
)

PACKAGE_RELS = XML_DECL + (
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/></Relationships>'
)

DOCUMENT_RELS = XML_DECL + (
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
    'Target="styles.xml"/>'
    '<Relationship Id="rId2" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" '
    'Target="numbering.xml"/></Relationships>'
)


def build(spec: dict, output: str) -> None:
    parts = []
    title = spec.get("title")
    if title:
        parts.append(para(run_xml(title), style="Title"))
    for block in spec.get("blocks", []) or []:
        parts.append(block_xml(block))
    if not parts:
        parts.append(para(run_xml("")))

    document = XML_DECL + (
        f'<w:document xmlns:w="{W}"><w:body>'
        + "".join(parts) + SECT_PR
        + "</w:body></w:document>"
    )

    parent = os.path.dirname(os.path.abspath(output))
    os.makedirs(parent, exist_ok=True)

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", PACKAGE_RELS)
        zf.writestr("word/document.xml", document)
        zf.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS)
        zf.writestr("word/styles.xml", STYLES_XML)
        zf.writestr("word/numbering.xml", NUMBERING_XML)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: to_docx.py <spec.json|-> <output.docx>", file=sys.stderr)
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
        print(f"could not build document: {exc}", file=sys.stderr)
        return 1
    print(f"docx written: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
