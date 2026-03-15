from __future__ import annotations

import html
import shutil
import re
import zipfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "output" / "ebook" / "autism_caregiving_ebook.md"
PDF_OUT = ROOT / "output" / "pdf" / "autism_caregiving_ebook.pdf"
EPUB_OUT = ROOT / "output" / "ebook" / "autism_caregiving_ebook.epub"
DOCS_DIR = ROOT / "docs"
DOCS_INDEX = DOCS_DIR / "index.html"
DOCS_PDF = DOCS_DIR / "autism_caregiving_ebook.pdf"
DOCS_EPUB = DOCS_DIR / "autism_caregiving_ebook.epub"

BULLET = "&#8226;"


def make_styles() -> StyleSheet1:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BookTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=24, leading=28, alignment=TA_CENTER, textColor=colors.HexColor("#16324F"), spaceAfter=10))
    styles.add(ParagraphStyle(name="BookSubtitle", parent=styles["Heading2"], fontName="Helvetica", fontSize=13, leading=16, alignment=TA_CENTER, textColor=colors.HexColor("#4A6572"), spaceAfter=18))
    styles.add(ParagraphStyle(name="Chapter", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=colors.HexColor("#16324F"), spaceBefore=10, spaceAfter=8))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#264653"), spaceBefore=8, spaceAfter=6))
    styles.add(ParagraphStyle(name="BodyBook", parent=styles["BodyText"], fontName="Times-Roman", fontSize=10.5, leading=15, alignment=TA_JUSTIFY, spaceAfter=8))
    styles.add(ParagraphStyle(name="BulletBook", parent=styles["BodyText"], fontName="Times-Roman", fontSize=10.5, leading=15, leftIndent=14, firstLineIndent=-10, spaceAfter=4))
    styles.add(ParagraphStyle(name="SourceHeading", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#2A4D69"), spaceBefore=6, spaceAfter=4))
    styles.add(ParagraphStyle(name="Reference", parent=styles["BodyText"], fontName="Times-Roman", fontSize=9.5, leading=13, leftIndent=10, firstLineIndent=-10, spaceAfter=4))
    return styles


def parse_markdown(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    lines = text.splitlines()
    buffer: list[str] = []
    kind = "p"

    def flush() -> None:
        nonlocal buffer, kind
        if buffer:
            blocks.append((kind, "\n".join(buffer).strip()))
            buffer = []
            kind = "p"

    for line in lines:
        if not line.strip():
            flush()
            continue
        if line.startswith("# "):
            flush()
            blocks.append(("h1", line[2:].strip()))
        elif line.startswith("## "):
            flush()
            blocks.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            flush()
            blocks.append(("h3", line[4:].strip()))
        elif line.startswith("#### "):
            flush()
            blocks.append(("h4", line[5:].strip()))
        elif line.startswith("- "):
            flush()
            blocks.append(("li", line[2:].strip()))
        elif re.match(r"^\d+\.\s", line):
            flush()
            blocks.append(("ref", re.sub(r"^\d+\.\s", "", line).strip()))
        else:
            buffer.append(line.strip())
    flush()
    return blocks


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def split_sections(blocks: list[tuple[str, str]]) -> list[dict[str, object]]:
    sections: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    for kind, content in blocks:
        if kind == "h1":
            continue
        if kind == "h2":
            if current:
                sections.append(current)
            current = {
                "title": content,
                "id": slugify(content),
                "blocks": [],
            }
            continue
        if current is None:
            continue
        current["blocks"].append((kind, content))

    if current:
        sections.append(current)
    return sections


def cover_page(styles: StyleSheet1) -> list:
    return [
        Spacer(1, 35 * mm),
        Paragraph("Autism Caregiving", styles["BookTitle"]),
        Paragraph("A Source-Based Ebook from 21 Provided Articles", styles["BookSubtitle"]),
        Spacer(1, 10 * mm),
        Table(
            [[Paragraph("This ebook synthesizes the PDF sources supplied by the user into a practical, research-based guide focused on caregiver experiences, burden, resilience, service access, and intervention.", styles["BodyBook"])]],
            colWidths=[160 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F6F8")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#B7C9D3")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]),
        ),
        Spacer(1, 12 * mm),
    ]


def build_pdf() -> None:
    styles = make_styles()
    blocks = parse_markdown(MANUSCRIPT.read_text(encoding="utf-8"))

    doc = SimpleDocTemplate(
        str(PDF_OUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title="Autism Caregiving",
        author="OpenAI Codex",
    )

    story = cover_page(styles)
    story.append(PageBreak())
    skipped_title = False

    for kind, content in blocks:
        if kind == "h1":
            if not skipped_title:
                skipped_title = True
                continue
            story.append(PageBreak())
            story.append(Paragraph(html.escape(content), styles["BookTitle"]))
            story.append(Spacer(1, 6))
        elif kind == "h2":
            text = html.escape(content)
            if text.startswith("Chapter ") or text in {"Source Notes", "References", "About This Ebook", "How to Read This Book", "Introduction"}:
                if story and not isinstance(story[-1], PageBreak):
                    story.append(PageBreak())
                story.append(Paragraph(text, styles["Chapter"]))
            else:
                story.append(Paragraph(text, styles["Section"]))
        elif kind in {"h3", "h4"}:
            style_name = "SourceHeading" if "SAC" in content else "Section"
            story.append(Paragraph(html.escape(content), styles[style_name]))
        elif kind == "li":
            story.append(Paragraph(f"• {html.escape(content)}", styles["BulletBook"]))
        elif kind == "ref":
            story.append(Paragraph(html.escape(content), styles["Reference"]))
        else:
            story.append(Paragraph(html.escape(content), styles["BodyBook"]))

    def draw_page(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#5B6C74"))
        canvas.drawString(doc.leftMargin, 10 * mm, "Autism Caregiving")
        canvas.drawRightString(A4[0] - doc.rightMargin, 10 * mm, str(canvas.getPageNumber()))
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)


def markdown_to_xhtml(text: str) -> str:
    blocks = parse_markdown(text)
    parts = []
    for kind, content in blocks:
        safe = html.escape(content)
        if kind == "h1":
            parts.append(f"<h1>{safe}</h1>")
        elif kind == "h2":
            parts.append(f"<h2>{safe}</h2>")
        elif kind == "h3":
            parts.append(f"<h3>{safe}</h3>")
        elif kind == "h4":
            parts.append(f"<h4>{safe}</h4>")
        elif kind == "li":
            parts.append(f"<p class='bullet'>• {safe}</p>")
        elif kind == "ref":
            parts.append(f"<p class='ref'>{safe}</p>")
        else:
            parts.append(f"<p>{safe}</p>")
    body = "\n".join(parts)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Autism Caregiving</title>
    <style>
      body {{ font-family: serif; line-height: 1.5; margin: 5%; }}
      h1, h2, h3 {{ color: #16324F; }}
      h1 {{ text-align: center; }}
      .bullet {{ margin-left: 1em; }}
      .ref {{ text-indent: -1em; margin-left: 1em; font-size: 0.95em; }}
    </style>
  </head>
  <body>
    {body}
  </body>
</html>
"""


def block_to_html(kind: str, content: str) -> str:
    safe = html.escape(content)
    if kind == "h1":
        return f"<h1>{safe}</h1>"
    if kind == "h2":
        return f"<h2>{safe}</h2>"
    if kind == "h3":
        return f"<h3>{safe}</h3>"
    if kind == "h4":
        return f"<h4>{safe}</h4>"
    if kind == "li":
        return f"<p class='bullet'>{BULLET} {safe}</p>"
    if kind == "ref":
        return f"<p class='ref'>{safe}</p>"
    return f"<p>{safe}</p>"


def build_site() -> None:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    blocks = parse_markdown(text)
    sections = split_sections(blocks)
    toc_items = "\n".join(
        f"<li><a href='#{section['id']}'>{html.escape(str(section['title']))}</a></li>"
        for section in sections
    )

    section_html = []
    for section in sections:
        body = "\n".join(block_to_html(kind, content) for kind, content in section["blocks"])
        section_html.append(
            f"""
            <section id="{section['id']}" class="section-card">
              <h2>{html.escape(str(section['title']))}</h2>
              {body}
            </section>
            """
        )

    site_html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Autism Caregiving</title>
    <meta name="description" content="A source-based ebook built from 21 research articles on autism caregiving." />
    <style>
      :root {{
        --ink: #14324a;
        --muted: #5d7382;
        --paper: #f7f3ea;
        --panel: #fffdf8;
        --accent: #d97a3a;
        --line: #d6cbbd;
        --shadow: 0 18px 50px rgba(20, 50, 74, 0.08);
      }}
      * {{ box-sizing: border-box; }}
      html {{ scroll-behavior: smooth; }}
      body {{
        margin: 0;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(217, 122, 58, 0.14), transparent 28%),
          linear-gradient(180deg, #f3ecdf 0%, var(--paper) 28%, #f8f5ef 100%);
        font-family: Georgia, "Times New Roman", serif;
        line-height: 1.65;
      }}
      a {{ color: var(--ink); }}
      .hero {{
        padding: 72px 20px 36px;
      }}
      .hero-inner {{
        max-width: 1120px;
        margin: 0 auto;
        display: grid;
        gap: 24px;
      }}
      .eyebrow {{
        display: inline-block;
        padding: 8px 12px;
        border: 1px solid rgba(20, 50, 74, 0.12);
        border-radius: 999px;
        color: var(--muted);
        background: rgba(255, 255, 255, 0.6);
        font-size: 13px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }}
      h1 {{
        margin: 10px 0 12px;
        font-size: clamp(2.5rem, 5vw, 4.8rem);
        line-height: 0.96;
        letter-spacing: -0.03em;
      }}
      .hero p {{
        max-width: 760px;
        margin: 0;
        color: var(--muted);
        font-size: 1.08rem;
      }}
      .hero-meta {{
        margin-top: 10px !important;
        font-size: 0.98rem !important;
      }}
      .actions {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 10px;
      }}
      .button {{
        display: inline-block;
        padding: 12px 18px;
        border-radius: 999px;
        text-decoration: none;
        border: 1px solid var(--ink);
        background: var(--ink);
        color: white;
        font-weight: 600;
      }}
      .button.secondary {{
        background: transparent;
        color: var(--ink);
      }}
      .highlights {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
      }}
      .highlight-card {{
        padding: 16px 18px;
        border-radius: 20px;
        background: rgba(255, 253, 248, 0.88);
        border: 1px solid var(--line);
        box-shadow: var(--shadow);
      }}
      .highlight-card strong {{
        display: block;
        font-size: 2rem;
        line-height: 1;
        margin-bottom: 6px;
      }}
      .highlight-card span {{
        color: var(--muted);
        font-size: 0.98rem;
      }}
      .layout {{
        max-width: 1120px;
        margin: 0 auto;
        padding: 12px 20px 60px;
        display: grid;
        grid-template-columns: 280px minmax(0, 1fr);
        gap: 28px;
      }}
      .toc, .content {{
        min-width: 0;
      }}
      .toc-card {{
        position: sticky;
        top: 20px;
        background: rgba(255, 253, 248, 0.88);
        backdrop-filter: blur(8px);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 20px;
        box-shadow: var(--shadow);
      }}
      .toc-card h2 {{
        margin: 0 0 12px;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }}
      .toc-card ul {{
        list-style: none;
        padding: 0;
        margin: 0;
      }}
      .toc-card li + li {{
        margin-top: 10px;
      }}
      .toc-card a {{
        text-decoration: none;
        color: var(--muted);
      }}
      .section-card {{
        background: rgba(255, 253, 248, 0.92);
        border: 1px solid var(--line);
        border-radius: 26px;
        padding: 28px;
        box-shadow: var(--shadow);
      }}
      .section-card + .section-card {{
        margin-top: 20px;
      }}
      .section-card h2 {{
        margin: 0 0 14px;
        font-size: clamp(1.5rem, 2.5vw, 2.2rem);
        line-height: 1.1;
      }}
      .section-card h3 {{
        margin-top: 24px;
        margin-bottom: 8px;
        font-size: 1.1rem;
      }}
      .section-card p {{
        margin: 0 0 14px;
      }}
      .bullet {{
        padding-left: 18px;
        text-indent: -14px;
      }}
      .ref {{
        padding-left: 18px;
        text-indent: -14px;
        font-size: 0.98rem;
      }}
      .footer {{
        max-width: 1120px;
        margin: 0 auto;
        padding: 0 20px 40px;
        color: var(--muted);
        font-size: 0.95rem;
      }}
      @media (max-width: 900px) {{
        .layout {{
          grid-template-columns: 1fr;
        }}
        .toc-card {{
          position: static;
        }}
        .highlights {{
          grid-template-columns: 1fr;
        }}
      }}
    </style>
  </head>
  <body>
    <header class="hero">
      <div class="hero-inner">
        <div class="eyebrow">Research Synthesis • Live GitHub Page</div>
        <div>
          <h1>Autism Caregiving</h1>
          <p>A polished web edition of the ebook, generated from Python and grounded in 21 research articles about caregiver burden, resilience, service access, and intervention.</p>
          <p class="hero-meta">Prepared for muszyolo as a public research project and downloadable as both PDF and EPUB.</p>
        </div>
        <div class="actions">
          <a class="button" href="autism_caregiving_ebook.pdf">Download PDF</a>
          <a class="button secondary" href="autism_caregiving_ebook.epub">Download EPUB</a>
        </div>
        <div class="highlights">
          <div class="highlight-card">
            <strong>21</strong>
            <span>source articles synthesized</span>
          </div>
          <div class="highlight-card">
            <strong>3</strong>
            <span>formats: web, PDF, EPUB</span>
          </div>
          <div class="highlight-card">
            <strong>1</strong>
            <span>live page for reading and sharing</span>
          </div>
        </div>
      </div>
    </header>
    <main class="layout">
      <aside class="toc">
        <div class="toc-card">
          <h2>Contents</h2>
          <ul>{toc_items}</ul>
        </div>
      </aside>
      <div class="content">
        {"".join(section_html)}
      </div>
    </main>
    <footer class="footer">
      Built from <code>scripts/build_ebook.py</code>. Commit the generated <code>docs/</code> folder and enable GitHub Pages to publish.
    </footer>
  </body>
</html>
"""

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_INDEX.write_text(site_html, encoding="utf-8")
    shutil.copy2(PDF_OUT, DOCS_PDF)
    shutil.copy2(EPUB_OUT, DOCS_EPUB)


def build_epub() -> None:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    xhtml = markdown_to_xhtml(text)
    container = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    content_opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Autism Caregiving</dc:title>
    <dc:creator>OpenAI Codex</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="bookid">autism-caregiving-ebook</dc:identifier>
  </metadata>
  <manifest>
    <item id="content" href="book.xhtml" media-type="application/xhtml+xml"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="content"/>
  </spine>
</package>
"""
    toc_ncx = """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head><meta name="dtb:uid" content="autism-caregiving-ebook"/></head>
  <docTitle><text>Autism Caregiving</text></docTitle>
  <navMap>
    <navPoint id="navpoint-1" playOrder="1">
      <navLabel><text>Autism Caregiving</text></navLabel>
      <content src="book.xhtml"/>
    </navPoint>
  </navMap>
</ncx>
"""
    with zipfile.ZipFile(EPUB_OUT, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container)
        zf.writestr("OEBPS/content.opf", content_opf)
        zf.writestr("OEBPS/toc.ncx", toc_ncx)
        zf.writestr("OEBPS/book.xhtml", xhtml)


if __name__ == "__main__":
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
    EPUB_OUT.parent.mkdir(parents=True, exist_ok=True)
    build_pdf()
    build_epub()
    build_site()
