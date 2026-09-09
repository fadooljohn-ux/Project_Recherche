from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/PILOT1_REFERENCE_DISCREPANCY_DOSSIER_v0.1.md"
OUTPUT = ROOT / "output/pdf/Pilot1_Published_Reference_Discrepancy_Dossier_v0.1.pdf"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2B6F9F")
PALE_BLUE = colors.HexColor("#EAF2F8")
PALE_GREEN = colors.HexColor("#EAF6EE")
PALE_AMBER = colors.HexColor("#FFF4DA")
INK = colors.HexColor("#1D2730")
MUTED = colors.HexColor("#5D6B78")
GRID = colors.HexColor("#B9C5CF")


def inline_markup(text: str) -> str:
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", escaped)
    return escaped


def page_decor(canvas, doc) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 0.32 * inch, width, 0.32 * inch, stroke=0, fill=1)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.65 * inch, 0.38 * inch, "PROJECT RECHERCHE • PILOT 1 CONTROLLED DOSSIER")
    canvas.drawRightString(width - 0.65 * inch, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()


def parse_table(lines: list[str], styles) -> Table:
    rows = []
    for line in lines:
        if re.match(r"^\|(?:\s*:?-+:?\s*\|)+$", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        style = styles["TableHeader"] if not rows else styles["TableCell"]
        rows.append([Paragraph(inline_markup(cell), style) for cell in cells])
    col_widths = [2.15 * inch, 1.02 * inch, 2.35 * inch, 0.82 * inch]
    table = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_BLUE]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "TitleCustom",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            "H1Custom",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=NAVY,
            spaceBefore=12,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            "BodyCustom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12.6,
            textColor=INK,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            "TableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.6,
            leading=9.4,
            textColor=INK,
        )
    )
    styles.add(
        ParagraphStyle(
            "TableHeader",
            parent=styles["TableCell"],
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            "Callout",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10.2,
            leading=14.2,
            textColor=NAVY,
            borderColor=BLUE,
            borderWidth=1,
            borderPadding=10,
            backColor=PALE_GREEN,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "Meta",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=MUTED,
            alignment=TA_CENTER,
        )
    )

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.4 * inch,
        title="Pilot 1 Published-Reference Discrepancy Dossier v0.1",
        author="Project Recherche",
        subject="Pulsar timing pilot benchmark discrepancy audit",
    )

    raw = SOURCE.read_text(encoding="utf-8").splitlines()
    story = [Spacer(1, 0.22 * inch)]
    title = raw[0].removeprefix("# ")
    story.extend(
        [
            Paragraph(inline_markup(title), styles["TitleCustom"]),
            Paragraph(
                "PSR J1744-1134 • NANOGrav 15-year wideband pilot • 2026-08-09",
                styles["Meta"],
            ),
            Spacer(1, 0.16 * inch),
            Table(
                [[Paragraph("CONTROLLED RESEARCH RECORD", styles["Meta"])]],
                colWidths=[5.2 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
                        ("BOX", (0, 0), (-1, -1), 0.8, BLUE),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
            Spacer(1, 0.26 * inch),
        ]
    )

    index = 1
    while index < len(raw):
        line = raw[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("## "):
            story.append(Paragraph(inline_markup(line[3:]), styles["H1Custom"]))
            index += 1
            continue
        if line.startswith("| "):
            table_lines = []
            while index < len(raw) and raw[index].strip().startswith("|"):
                table_lines.append(raw[index].strip())
                index += 1
            story.extend([parse_table(table_lines, styles), Spacer(1, 8)])
            continue
        if re.match(r"^\d+\. ", line):
            items = []
            while index < len(raw) and re.match(r"^\d+\. ", raw[index].strip()):
                item = re.sub(r"^\d+\. ", "", raw[index].strip())
                index += 1
                while index < len(raw):
                    continuation = raw[index].strip()
                    if not continuation or re.match(r"^\d+\. ", continuation) or continuation.startswith("## "):
                        break
                    item += " " + continuation
                    index += 1
                items.append(ListItem(Paragraph(inline_markup(item), styles["BodyCustom"])))
            story.append(ListFlowable(items, bulletType="1", leftIndent=19, bulletFontSize=8))
            continue

        paragraph = line
        index += 1
        while index < len(raw):
            continuation = raw[index].strip()
            if not continuation or continuation.startswith(("## ", "| ")) or re.match(
                r"^\d+\. ", continuation
            ):
                break
            paragraph += " " + continuation
            index += 1
        style = styles["Callout"] if paragraph.startswith("**PASS WITH ADVISORY") else styles["BodyCustom"]
        story.append(Paragraph(inline_markup(paragraph), style))

    story.extend(
        [
            Spacer(1, 4),
            Paragraph("Control status", styles["H1Custom"]),
            Table(
                [
                    ["Mass conversion", "PASS"],
                    ["Covariance hard diagnostics", "PASS"],
                    ["Published numerical comparability", "NOT APPLICABLE"],
                    ["Lower-amplitude extension", "AUTHORIZED"],
                    ["Observed periodic search", "NOT AUTHORIZED"],
                    ["Initial v0.1", "NOT YET AUTHORIZED"],
                ],
                colWidths=[3.65 * inch, 2.15 * inch],
                style=TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
                        ("BACKGROUND", (0, 0), (0, -1), PALE_BLUE),
                        ("BACKGROUND", (1, 0), (1, 1), PALE_GREEN),
                        ("BACKGROUND", (1, 2), (1, 2), PALE_AMBER),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 7.6),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                    ]
                ),
            ),
        ]
    )
    doc.build(story, onFirstPage=page_decor, onLaterPages=page_decor)


if __name__ == "__main__":
    build()
