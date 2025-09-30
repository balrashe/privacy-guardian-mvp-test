"""
RROSH (Real Risk of Significant Harm) Decision Wizard
====================================================

This module implements a simple wizard to help organisations assess whether a
privacy breach must be reported under Canadian privacy laws, including
PIPEDA and the forthcoming CPPA.  It captures key factors – the
sensitivity of the exposed data, the probability the information will be
misused, and any mitigation measures in place – and produces a
recommendation along with a structured memo that can be exported to PDF.

The logic used here mirrors the high‑level approach recommended by the
Office of the Privacy Commissioner of Canada (OPC).  It is deliberately
conservative: if either the sensitivity of the data or the likelihood of
misuse is rated "High" then the breach is deemed reportable.  Medium
ratings on both factors also result in a reportable event.  This is a
demonstration implementation and should not be relied upon as legal advice.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


@dataclass
class RROSHInput:
    """Parameters supplied by the user when assessing a breach."""
    description: str
    sensitivity: str  # "Low", "Medium", "High"
    probability: str  # "Low", "Medium", "High"
    mitigation: str = ""


def generate_rrosh_decision(input_data: RROSHInput) -> Dict[str, Any]:
    """Assess the breach factors and return a decision memo.

    Args:
        input_data: A ``RROSHInput`` instance containing details about the
            breach.

    Returns:
        A dictionary containing the assessment date, the decision
        ("Report" or "No Report Required"), a plain‑language rationale,
        a recommendation, the factors considered, and a reference link
        to official OPC guidance.
    """
    # Assign numerical weights to qualitative inputs.
    weights = {"Low": 0, "Medium": 1, "High": 2}
    sens_weight = weights.get(input_data.sensitivity, 0)
    prob_weight = weights.get(input_data.probability, 0)

    # Decision rule: if either factor is high (>=2) OR both are medium (1 + 1), report.
    total = sens_weight + prob_weight
    if sens_weight >= 2 or prob_weight >= 2 or total >= 3:
        decision = "Report"
        recommendation = (
            "Under PIPEDA/CPPA you should notify affected individuals and report the breach to "
            "the Office of the Privacy Commissioner of Canada (OPC) without delay. Document all "
            "steps taken and your rationale for future audits."
        )
    else:
        decision = "No Report Required"
        recommendation = (
            "Based on the factors provided, this incident is unlikely to pose a real risk of significant "
            "harm. Maintain a record of this assessment and continue monitoring the situation."
        )

    rationale = (
        f"Sensitivity of data: {input_data.sensitivity}. "
        f"Probability of misuse or harm: {input_data.probability}. "
        f"Mitigation measures: {input_data.mitigation or 'None provided'}. "
        "The decision was determined by combining the relative sensitivity and probability ratings."
    )

    return {
        "assessment_date": datetime.now().isoformat(),
        "decision": decision,
        "rationale": rationale,
        "recommendation": recommendation,
        "factors": {
            "description": input_data.description,
            "sensitivity": input_data.sensitivity,
            "probability_of_misuse": input_data.probability,
            "mitigation": input_data.mitigation,
        },
        "reference": (
            "Office of the Privacy Commissioner (OPC) guidance on Real Risk of Significant Harm: "
            "https://www.priv.gc.ca/en/privacy-topics/privacy-breaches/respond-to-a-privacy-breach-at-your-business/real-risk-of-significant-harm/"
        ),
    }


def memo_to_pdf(memo: Dict[str, Any]) -> bytes:
    """Convert a RROSH decision memo into a PDF document.

    Args:
        memo: The dictionary returned by ``generate_rrosh_decision``.

    Returns:
        A bytes object containing the PDF representation of the memo.
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
    custom_heading = ParagraphStyle(
        name="RROSHHeading",
        parent=styles["Heading1"],
        alignment=TA_LEFT,
        fontSize=18,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=12,
    )
    custom_body = ParagraphStyle(
        name="RROSHBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
    )

    story: list = []
    story.append(Paragraph("Real Risk of Significant Harm Assessment", custom_heading))
    story.append(Paragraph(f"Assessment Date: {memo['assessment_date']}", custom_body))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Decision: <b>{memo['decision']}</b>", custom_body))
    story.append(Spacer(1, 12))

    # Factors table
    factors_data = [
        ["Description", memo["factors"].get("description", "")],
        ["Sensitivity", memo["factors"].get("sensitivity", "")],
        ["Probability of Misuse", memo["factors"].get("probability_of_misuse", "")],
        ["Mitigation", memo["factors"].get("mitigation", "") or "None"],
    ]
    table = Table(
        [["Factor", "Detail"]] + factors_data,
        colWidths=[2.0 * inch, 4.0 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Rationale:", styles["Heading3"]))
    story.append(Paragraph(memo["rationale"], custom_body))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommendation:", styles["Heading3"]))
    story.append(Paragraph(memo["recommendation"], custom_body))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Reference:", styles["Heading3"]))
    story.append(Paragraph(memo["reference"], custom_body))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()