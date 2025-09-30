from __future__ import annotations
import re
from typing import Dict, List, Any
import pandas as pd

# Define risk levels and patterns
RISK_LEVELS = ["High", "Medium", "Low"]

# Common regex patterns
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[\d\s().-]{7,}$")
SIN_RE = re.compile(r"^\d{3}[-\s]?\d{3}[-\s]?\d{3}$")  # Canadian Social Insurance Number (simplified)
CREDIT_CARD_RE = re.compile(r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$")
DOB_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{2}/\d{2}/\d{4}$")
POSTAL_CA_RE = re.compile(r"^[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z](?:\s)?\d[ABCEGHJ-NPRSTV-Z]\d$", re.IGNORECASE)
IP_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
LATLON_RE = re.compile(r"^-?\d{1,3}\.\d+,\s*-?\d{1,3}\.\d+$")

# Heuristic keyword sets
HIGH_NAME_HINTS = {
    "sin", "social_insurance", "ssn", "credit", "card", "cc", "iban", "account", "routing",
    "medical", "health", "diagnosis", "mrn", "insurance_id", "passport", "driver", "license"
}
MEDIUM_NAME_HINTS = {
    "email", "phone", "mobile", "dob", "birth", "address", "postal", "zip", "city", "province",
    "state", "ip", "location", "lat", "lon", "geocode"
}

def _column_risk_by_name(col: str) -> str:
    col_l = col.lower()
    if any(h in col_l for h in HIGH_NAME_HINTS):
        return "High"
    if any(h in col_l for h in MEDIUM_NAME_HINTS):
        return "Medium"
    return "Low"

def _cell_risk_by_value(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):  # NaN
        return "Low"
    s = str(v).strip()
    if not s:
        return "Low"
    if any([EMAIL_RE.match(s), SIN_RE.match(s), CREDIT_CARD_RE.match(s)]):
        return "High"
    if any([PHONE_RE.match(s), DOB_RE.match(s), POSTAL_CA_RE.match(s), IP_RE.match(s), LATLON_RE.match(s)]):
        return "Medium"
    return "Low"

def classify_series(name: str, series: pd.Series, sample_size: int = 200) -> Dict[str, Any]:
    name_risk = _column_risk_by_name(name)
    # Sample values to avoid scanning entire columns for huge files
    sample = series.dropna().astype(str).head(sample_size).tolist()
    # Value-based risk: take the max risk observed
    val_risk_rank = 0  # Low=0, Medium=1, High=2
    for v in sample:
        r = _cell_risk_by_value(v)
        val_risk_rank = max(val_risk_rank, {"Low":0, "Medium":1, "High":2}[r])
        if val_risk_rank == 2:
            break
    value_risk = ["Low", "Medium", "High"][val_risk_rank]
    # Final risk = max(name_risk, value_risk)
    final_risk = ["Low", "Medium", "High"][max(
        {"Low":0, "Medium":1, "High":2}[name_risk],
        {"Low":0, "Medium":1, "High":2}[value_risk]
    )]
    return {
        "column": name,
        "name_hint_risk": name_risk,
        "value_sample_risk": value_risk,
        "final_risk": final_risk
    }

def classify_dataframe(df: pd.DataFrame):
    results = []
    for c in df.columns:
        results.append(classify_series(c, df[c]))
    return results

def summarize_risk_levels(results):
    summary = {"High": 0, "Medium": 0, "Low": 0}
    for r in results:
        summary[r["final_risk"]] += 1
    return summary
