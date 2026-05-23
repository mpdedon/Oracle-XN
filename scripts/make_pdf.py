"""
scripts/make_pdf.py
Convert solution_paper.md → solution_paper.pdf using Chrome headless.

Usage:
    python scripts/make_pdf.py
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "solution_paper.md"
PDF_PATH = ROOT / "solution_paper.pdf"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# ── minimal Markdown → HTML converter (no external deps) ───────────────────
def md_to_html(md: str) -> str:
    """
    Convert a Markdown document to HTML.
    Handles: headings, bold/italic, code blocks, inline code, tables,
    horizontal rules, blockquotes, unordered lists, ordered lists,
    math (KaTeX placeholders left as-is for Chrome).
    """
    lines = md.split("\n")
    html_lines: list[str] = []
    in_code = False
    in_table = False
    in_list = False
    in_ol = False
    in_blockquote = False

    def flush_list():
        nonlocal in_list, in_ol
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        if in_ol:
            html_lines.append("</ol>")
            in_ol = False

    def flush_blockquote():
        nonlocal in_blockquote
        if in_blockquote:
            html_lines.append("</blockquote>")
            in_blockquote = False

    def flush_table():
        nonlocal in_table
        if in_table:
            html_lines.append("</tbody></table>")
            in_table = False

    def inline(text: str) -> str:
        """Apply inline formatting."""
        # Escape HTML special chars first (except inside code spans)
        parts = re.split(r"(`[^`]+`)", text)
        result = []
        for i, part in enumerate(parts):
            if i % 2 == 1:  # code span
                inner = part[1:-1].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                result.append(f"<code>{inner}</code>")
            else:
                p = part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                # Bold + italic
                p = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", p)
                p = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p)
                p = re.sub(r"\*(.+?)\*", r"<em>\1</em>", p)
                p = re.sub(r"__(.+?)__", r"<strong>\1</strong>", p)
                p = re.sub(r"_(.+?)_", r"<em>\1</em>", p)
                # Links [text](url)
                p = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', p)
                result.append(p)
        return "".join(result)

    i = 0
    while i < len(lines):
        line = lines[i]

        # Fenced code blocks
        if line.startswith("```"):
            if not in_code:
                flush_list()
                flush_blockquote()
                flush_table()
                lang = line[3:].strip()
                html_lines.append(f'<pre><code class="language-{lang}">')
                in_code = True
            else:
                html_lines.append("</code></pre>")
                in_code = False
            i += 1
            continue

        if in_code:
            escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_lines.append(escaped)
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", line):
            flush_list(); flush_blockquote(); flush_table()
            html_lines.append("<hr>")
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            flush_list(); flush_blockquote(); flush_table()
            level = len(m.group(1))
            html_lines.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # Blockquote
        if line.startswith("> "):
            flush_list(); flush_table()
            if not in_blockquote:
                html_lines.append("<blockquote>")
                in_blockquote = True
            html_lines.append(f"<p>{inline(line[2:])}</p>")
            i += 1
            continue
        else:
            flush_blockquote()

        # Table (detect by pipe characters)
        if "|" in line and line.strip().startswith("|"):
            flush_list()
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # Check next line for separator
            if not in_table:
                # This is the header row
                html_lines.append('<table><thead><tr>')
                for c in cells:
                    html_lines.append(f"<th>{inline(c)}</th>")
                html_lines.append("</tr></thead><tbody>")
                in_table = True
                # Skip the separator row
                if i + 1 < len(lines) and re.match(r"^\|[-| :]+\|$", lines[i+1].strip()):
                    i += 2
                    continue
            else:
                # Skip separator rows
                if re.match(r"^[-| :]+$", line.strip().replace("|", "")):
                    i += 1
                    continue
                html_lines.append("<tr>")
                for c in cells:
                    html_lines.append(f"<td>{inline(c)}</td>")
                html_lines.append("</tr>")
            i += 1
            continue
        else:
            flush_table()

        # Unordered list
        m = re.match(r"^(\s*)[-*+]\s+(.*)", line)
        if m:
            flush_blockquote()
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{inline(m.group(2))}</li>")
            i += 1
            continue

        # Ordered list
        m = re.match(r"^(\s*)\d+\.\s+(.*)", line)
        if m:
            flush_blockquote()
            if not in_ol:
                html_lines.append("<ol>")
                in_ol = True
            html_lines.append(f"<li>{inline(m.group(2))}</li>")
            i += 1
            continue

        # Blank line
        if line.strip() == "":
            flush_list(); flush_ol = False
            html_lines.append("")
            i += 1
            continue

        # Paragraph
        flush_list()
        html_lines.append(f"<p>{inline(line)}</p>")
        i += 1

    flush_list(); flush_blockquote(); flush_table()
    if in_code:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    font-size: 11pt;
    line-height: 1.65;
    color: #1a1a2e;
    max-width: 780px;
    margin: 0 auto;
    padding: 32px 40px;
    background: #fff;
}

/* Cover-style title block */
h1:first-of-type {
    font-size: 22pt;
    font-weight: 700;
    color: #0f3460;
    border-bottom: 3px solid #16213e;
    padding-bottom: 10px;
    margin-bottom: 8px;
}

h1 { font-size: 18pt; font-weight: 700; color: #0f3460; margin: 24px 0 10px; }
h2 { font-size: 14pt; font-weight: 700; color: #16213e; margin: 20px 0 8px;
     border-bottom: 1px solid #dee2e6; padding-bottom: 4px; }
h3 { font-size: 12pt; font-weight: 600; color: #1d3557; margin: 16px 0 6px; }
h4 { font-size: 11pt; font-weight: 600; color: #457b9d; margin: 12px 0 4px; }

p { margin: 8px 0; }

a { color: #457b9d; text-decoration: none; }

strong { font-weight: 600; color: #0f3460; }
em     { color: #1d3557; }

code {
    font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
    font-size: 9pt;
    background: #f0f4f8;
    color: #c0392b;
    padding: 1px 5px;
    border-radius: 3px;
}

pre {
    background: #1a1a2e;
    color: #e0e0e0;
    padding: 14px 16px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 12px 0;
    font-size: 8.5pt;
    line-height: 1.5;
}
pre code {
    background: transparent;
    color: #e0e0e0;
    padding: 0;
    border-radius: 0;
}

blockquote {
    border-left: 4px solid #457b9d;
    background: #eef4fb;
    padding: 10px 16px;
    margin: 12px 0;
    border-radius: 0 4px 4px 0;
    font-size: 10.5pt;
    color: #333;
}
blockquote p { margin: 4px 0; }

table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 9.5pt;
}
thead { background: #0f3460; color: #fff; }
th { padding: 7px 10px; font-weight: 600; text-align: left; }
td { padding: 6px 10px; border-bottom: 1px solid #dee2e6; }
tr:nth-child(even) { background: #f8f9fa; }
tr:hover { background: #eef4fb; }

ul, ol { margin: 8px 0 8px 24px; }
li { margin: 3px 0; }

hr {
    border: none;
    border-top: 2px solid #dee2e6;
    margin: 20px 0;
}

@media print {
    body { padding: 20px 30px; }
    pre  { white-space: pre-wrap; word-break: break-all; }
    a    { color: #457b9d; }
    h2   { page-break-before: auto; }
    table, pre, blockquote { page-break-inside: avoid; }
}
"""


def build_html(md_text: str) -> str:
    body = md_to_html(md_text)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ORACLE-X/N Solution Paper</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>"""


def make_pdf(md_path: Path, pdf_path: Path) -> None:
    print(f"Reading {md_path} ...")
    md_text = md_path.read_text(encoding="utf-8")

    html = build_html(md_text)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html)
        html_path = f.name

    print(f"Temporary HTML: {html_path}")
    print(f"Generating PDF → {pdf_path} ...")

    result = subprocess.run(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            f"--print-to-pdf={pdf_path}",
            "--print-to-pdf-no-header",
            "--no-pdf-header-footer",
            f"file:///{html_path.replace(chr(92), '/')}",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    os.unlink(html_path)

    if result.returncode != 0:
        print("Chrome stderr:", result.stderr[:1000])
        sys.exit(result.returncode)

    if pdf_path.exists():
        size_kb = pdf_path.stat().st_size // 1024
        print(f"✓ PDF created: {pdf_path}  ({size_kb} KB)")
    else:
        print("✗ PDF not found after Chrome run")
        sys.exit(1)


def main():
    # If a specific markdown file is passed as argument, convert just that one.
    # Otherwise convert all solution papers found in the project root.
    if len(sys.argv) > 1:
        md = Path(sys.argv[1])
        pdf = md.with_suffix(".pdf")
        make_pdf(md, pdf)
    else:
        papers = [
            (ROOT / "solution_paper_a.md", ROOT / "solution_paper_a.pdf"),
            (ROOT / "solution_paper_b.md", ROOT / "solution_paper_b.pdf"),
            (ROOT / "solution_paper.md",   ROOT / "solution_paper.pdf"),
        ]
        for md, pdf in papers:
            if md.exists():
                make_pdf(md, pdf)
            else:
                print(f"  (skipping {md.name} — not found)")


if __name__ == "__main__":
    main()
