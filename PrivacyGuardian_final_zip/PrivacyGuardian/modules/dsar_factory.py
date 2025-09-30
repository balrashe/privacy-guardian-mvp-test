"""
DSAR (Data Subject Access Request) Dossier Factory
===================================================

This module provides utilities to generate a DSAR dossier from a
dataset.  When an individual exercises their right to access or
correct their personal information, organisations must assemble a
complete record of the personal data they hold, the purposes for
which it is used, and any recipients of that data.  The helper
functions here leverage the existing risk assessment to produce a
summary and generate a response letter.  The resulting dossier can
optionally be exported as a PDF.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from modules.risk_assessment import classify_dataframe


@dataclass
class DSARSummary:
    """Container for DSAR summary details."""
    subject_name: str
    created_at: str
    categories: Dict[str, List[str]]
    classification_results: List[Dict[str, Any]]
    data_preview: pd.DataFrame | None = None


def generate_dsar_summary(df: pd.DataFrame, subject_name: str) -> DSARSummary:
    """Analyse a DataFrame and produce a summary for DSAR purposes.

    The function classifies each column using the existing risk
    assessment heuristics and groups them by risk level.  It also
    captures a small preview of the data (first 5 rows) for context.

    Args:
        df: The dataset containing the subject's data.
        subject_name: The name of the data subject making the request.

    Returns:
        A ``DSARSummary`` object containing grouped categories and the
        classification results.
    """
    results = classify_dataframe(df)
    categories: Dict[str, List[str]] = {"High": [], "Medium": [], "Low": []}
    for res in results:
        categories.get(res["final_risk"], categories["Low"]).append(res["column"])
    preview = df.head(5).copy()
    return DSARSummary(
        subject_name=subject_name,
        created_at=datetime.now().isoformat(),
        categories=categories,
        classification_results=results,
        data_preview=preview,
    )


def generate_dsar_letter(summary: DSARSummary, contact_email: str) -> str:
    """Generate a DSAR response letter in plain text.

    Args:
        summary: The summary produced by ``generate_dsar_summary``.
        contact_email: Contact email for further correspondence.

    Returns:
        A string containing the DSAR response letter.
    """
    letter = []
    letter.append(f"Date: {summary.created_at}\n")
    letter.append(f"Dear {summary.subject_name},\n")
    letter.append(
        "Thank you for your request to access and/or correct your personal information. "
        "We have compiled a summary of the personal data we currently hold about you, "
        "as required under Canadian privacy laws.\n"
    )
    # Summarise categories
    for level in ["High", "Medium", "Low"]:
        cols = summary.categories.get(level, [])
        if cols:
            letter.append(f"\n{level} sensitivity data:\n")
            for c in cols:
                letter.append(f"  • {c}\n")
    letter.append(
        "\nIf any of the above information is inaccurate or incomplete, please let us "
        "know and we will promptly correct it. We will respond to your request in a timely "
        "manner and may require additional information to verify your identity.\n"
    )
    letter.append(
        f"For questions or further information regarding your personal data, please contact us at {contact_email}.\n"
    )
    letter.append("\nSincerely,\nPrivacy Team")
    return "".join(letter)


def dsar_to_pdf(summary: DSARSummary, letter_text: str) -> bytes:
    """Generate a PDF dossier combining the summary and the letter.

    Args:
        summary: The summary from ``generate_dsar_summary``.
        letter_text: The letter produced by ``generate_dsar_letter``.

    Returns:
        Bytes representing the PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )
    styles = getSampleStyleSheet()
    heading = styles["Heading1"]
    heading.fontSize = 18
    heading.textColor = colors.HexColor("#2c3e50")
    body = ParagraphStyle(
        name="DSARBody",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
    )
    story: List[Any] = []
    story.append(Paragraph("DSAR Dossier", heading))
    story.append(Paragraph(f"Subject: {summary.subject_name}", body))
    story.append(Paragraph(f"Generated: {summary.created_at}", body))
    story.append(Spacer(1, 12))
    # Add letter text
    for para in letter_text.split("\n\n"):
        story.append(Paragraph(para.replace("\n", "<br/>"), body))
        story.append(Spacer(1, 6))
    story.append(Spacer(1, 12))
    # Add classification table
    table_data = [["Column", "Name Risk", "Value Risk", "Final Risk"]]
    for res in summary.classification_results:
        table_data.append([
            res.get("column", ""),
            res.get("name_hint_risk", ""),
            res.get("value_sample_risk", ""),
            res.get("final_risk", ""),
        ])
    table = Table(
        table_data,
        colWidths=[2.0 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()