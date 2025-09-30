"""
Breach Record Book
==================

This module provides a simple in‑memory breach record book for Privacy
Guardian.  Organisations subject to PIPEDA/CPPA must maintain records
of privacy breaches for 24 months.  The ``BreachRecordBook`` class
allows you to add breach events, list them, filter them by age, and
export the log to Excel or PDF.  Records are intentionally kept in
memory only; if persistence across sessions is desired, callers must
serialise and restore the list of events themselves.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any

import pandas as pd
from dateutil.relativedelta import relativedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils.dataframe import dataframe_to_rows


@dataclass
class BreachEvent:
    """Represents a single privacy breach incident."""
    date: date
    description: str
    containment: str
    harm: str
    reported: bool = False


class BreachRecordBook:
    """In‑memory log of breach events for the past 24 months."""

    def __init__(self) -> None:
        self.records: List[BreachEvent] = []

    def add_record(self, event: BreachEvent) -> None:
        """Add a breach event to the log."""
        self.records.append(event)

    def get_recent_records(self, months: int = 24) -> List[BreachEvent]:
        """Return events from the last ``months`` months (default 24)."""
        cutoff = datetime.now().date() - relativedelta(months=months)
        return [r for r in self.records if r.date >= cutoff]

    def to_dataframe(self, include_all: bool = True) -> pd.DataFrame:
        """Convert the log to a pandas DataFrame.

        Args:
            include_all: If ``True``, include all records.  If ``False``,
                include only records from the last 24 months.

        Returns:
            ``pandas.DataFrame`` with columns Date, Description,
            Containment Measures, Harm/Outcome and Reported.
        """
        records = self.records if include_all else self.get_recent_records()
        data = [
            {
                "Date": r.date.isoformat(),
                "Description": r.description,
                "Containment Measures": r.containment,
                "Harm/Outcome": r.harm,
                "Reported": "Yes" if r.reported else "No",
            }
            for r in records
        ]
        return pd.DataFrame(data)

    def to_excel(self, include_all: bool = True) -> bytes:
        """Export the log to an Excel file.

        Returns a bytes object containing the XLSX content.
        """
        df = self.to_dataframe(include_all=include_all)
        wb = Workbook()
        ws = wb.active
        ws.title = "Breach Record"
        # Write DataFrame to worksheet
        for row_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=1):
            ws.append(row)
        # Style header
        header_font = Font(bold=True)
        for cell in ws[1]:
            cell.font = header_font
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.getvalue()

    def to_pdf(self, include_all: bool = True) -> bytes:
        """Export the log to a PDF document."""
        df = self.to_dataframe(include_all=include_all)
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
        heading = ParagraphStyle(
            name="BreachHeading",
            parent=styles["Heading1"],
            alignment=TA_LEFT,
            fontSize=18,
            textColor=colors.HexColor("#2c3e50"),
            spaceAfter=12,
        )
        body = ParagraphStyle(
            name="BreachBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
        )
        story: List[Any] = []
        story.append(Paragraph("Breach Record Book", heading))
        story.append(Paragraph(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body))
        story.append(Spacer(1, 12))
        # Table data
        table_data = [df.columns.tolist()] + df.values.tolist()
        table = Table(table_data, colWidths=[1.5 * inch, 2.5 * inch, 2.5 * inch, 1.0 * inch, 0.8 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
                ]
            )
        )
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()