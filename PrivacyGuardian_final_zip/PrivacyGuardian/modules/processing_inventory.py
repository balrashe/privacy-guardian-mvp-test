"""
RoPA‑style Processing Inventory
===============================

This module defines a simple structure for maintaining a record of
processing activities (akin to a Record of Processing Activities under
the GDPR) but mapped to Canadian privacy principles.  Each entry
captures the name of the processing activity, its purpose, the
categories of personal data involved, the recipients, retention
period, and safeguards.  Users can add activities and export the
inventory to a pandas DataFrame or an Excel workbook.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import List, Dict, Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils.dataframe import dataframe_to_rows


@dataclass
class ProcessingActivity:
    """Represents a single processing activity in the inventory."""
    activity_name: str
    purpose: str
    data_categories: str
    recipients: str
    retention: str
    safeguards: str
    pipeda_principles: str = ""


class ProcessingInventory:
    """In‑memory storage of processing activities."""

    def __init__(self) -> None:
        self.activities: List[ProcessingActivity] = []

    def add_activity(self, activity: ProcessingActivity) -> None:
        """Add a processing activity to the inventory."""
        self.activities.append(activity)

    def to_dataframe(self) -> pd.DataFrame:
        """Return the inventory as a pandas DataFrame."""
        data = [
            {
                "Activity Name": a.activity_name,
                "Purpose": a.purpose,
                "Data Categories": a.data_categories,
                "Recipients": a.recipients,
                "Retention": a.retention,
                "Safeguards": a.safeguards,
                "PIPEDA Principles": a.pipeda_principles,
            }
            for a in self.activities
        ]
        return pd.DataFrame(data)

    def to_excel(self) -> bytes:
        """Export the inventory to an Excel file and return its bytes."""
        df = self.to_dataframe()
        wb = Workbook()
        ws = wb.active
        ws.title = "Processing Inventory"
        for row in dataframe_to_rows(df, index=False, header=True):
            ws.append(row)
        # Bold header
        for cell in ws[1]:
            cell.font = Font(bold=True)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.getvalue()