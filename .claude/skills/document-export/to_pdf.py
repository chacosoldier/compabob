#!/usr/bin/env python3
"""Compabob document-export: convert a self-contained HTML file to PDF.

Standard library only. It shells out to whatever HTML-to-PDF engine is on the
machine, trying them in order of rendering fidelity:

  1. headless Chrome / Chromium / Edge / Brave   (best CSS support)
  2. weasyprint                                  (good modern CSS)
  3. wkhtmltopdf                                 (older engine, widely packaged)

If none is found it prints an install hint and exits non-zero.

  usage: python3 to_pdf.py <input.html> [output.pdf]

The input must be a self-contained HTML file (inline CSS, no external assets),
which is exactly what the visual-explainer skill produces. For markdown or
plain text, wrap it in HTML first (see SKILL.md).
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_chrome() -> str | None:
    for name in (
        "google-chrome", "google-chrome-stable", "chromium",
        "chromium-browser", "microsoft-edge", "brave-browser",
    ):
        found = shutil.which(name)
        if found:
            return found
    for path in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ):
        if os.path.isfile(path):
            return path
    # Playwright-managed Chromium (compabob's integrations module installs this).
    for base in (
        Path.home() / "Library" / "Caches" / "ms-playwright",
        Path.home() / ".cache" / "ms-playwright",
    ):
        for pattern in (
            "chromium-*/chrome-*/Chromium.app/Contents/MacOS/Chromium",
            "chromium-*/chrome-linux/chrome",
            "chromium_headless_shell-*/chrome-*/headless_shell",
        ):
            hits = sorted(glob.glob(str(base / pattern)))
            if hits:
                return hits[-1]
    return None


def via_chrome(chrome: str, html_path: str, pdf_path: str) -> bool:
    url = Path(html_path).resolve().as_uri()
    out = os.path.abspath(pdf_path)
    base = [chrome, "--headless", "--disable-gpu", "--no-sandbox"]
    # Newer Chrome accepts --no-pdf-header-footer; older ignores or rejects it,
    # so fall back to a plain run.
    for extra in (["--no-pdf-header-footer"], []):
        try:
            result = subprocess.run(
                base + extra + [f"--print-to-pdf={out}", url],
                capture_output=True, text=True, timeout=120,
            )
        except (subprocess.TimeoutExpired, OSError):
            return False
        if result.returncode == 0 and os.path.isfile(out):
            return True
    return False


def via_tool(tool: str, args: list[str]) -> bool:
    binary = shutil.which(tool)
    if not binary:
        return False
    try:
        result = subprocess.run(
            [binary, *args], capture_output=True, text=True, timeout=120,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: to_pdf.py <input.html> [output.pdf]", file=sys.stderr)
        return 2

    html_path = sys.argv[1]
    if not os.path.isfile(html_path):
        print(f"input not found: {html_path}", file=sys.stderr)
        return 2
    if not html_path.lower().endswith((".html", ".htm")):
        print(
            "input must be an .html file. For markdown or plain text, wrap it "
            "in HTML first (see SKILL.md).",
            file=sys.stderr,
        )
        return 2

    pdf_path = (
        sys.argv[2] if len(sys.argv) > 2
        else os.path.splitext(html_path)[0] + ".pdf"
    )
    parent = os.path.dirname(os.path.abspath(pdf_path))
    os.makedirs(parent, exist_ok=True)

    in_abs = os.path.abspath(html_path)
    out_abs = os.path.abspath(pdf_path)

    chrome = find_chrome()
    if chrome and via_chrome(chrome, html_path, pdf_path):
        print(f"PDF written via Chrome: {pdf_path}")
        return 0
    if via_tool("weasyprint", [in_abs, out_abs]) and os.path.isfile(out_abs):
        print(f"PDF written via weasyprint: {pdf_path}")
        return 0
    if via_tool("wkhtmltopdf", ["--quiet", in_abs, out_abs]) and os.path.isfile(out_abs):
        print(f"PDF written via wkhtmltopdf: {pdf_path}")
        return 0

    print(
        "No HTML-to-PDF engine found. Install one of these, then retry:\n"
        "  - Google Chrome   https://www.google.com/chrome/  (best fidelity, nothing else to do)\n"
        "  - weasyprint      macOS: brew install weasyprint    Linux: pipx install weasyprint\n"
        "  - wkhtmltopdf     macOS: brew install wkhtmltopdf   Linux: sudo apt install wkhtmltopdf",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
