"""
Enhanced Risk Scoring
=====================

This module extends the basic rule‑based risk classification with
additional checks and risk scoring.  It includes detection of
potential credit card numbers using the Luhn algorithm, identifies
Canadian Social Insurance Numbers (SIN) with a simple checksum, and
assigns numeric scores to columns.  The overall dataset score can be
used to benchmark risk across different datasets.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import pandas as pd

from modules.risk_assessment import RISK_LEVELS, _column_risk_by_name, _cell_risk_by_value


def luhn_checksum(number_str: str) -> bool:
    """Perform a Luhn checksum to validate potential credit card numbers.

    Args:
        number_str: The number as a string (digits only).

    Returns:
        True if the number passes the Luhn check, False otherwise.
    """
    digits = [int(ch) for ch in number_str if ch.isdigit()]
    if len(digits) < 12:  # Too short to be a card number
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, digit in enumerate(digits):
        if i % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def detect_sin(number_str: str) -> bool:
    """Detect a Canadian Social Insurance Number (SIN) using a checksum.

    A simplified Luhn‑like algorithm is used: multiply odd digits by 1
    and even digits by 2 (subtract 9 if the result is >9) and sum.
    Valid SINs have a checksum divisible by 10.
    """
    digits = [int(ch) for ch in number_str if ch.isdigit()]
    if len(digits) != 9:
        return False
    total = 0
    for idx, d in enumerate(digits[:-1]):  # Exclude checksum digit
        if (idx + 1) % 2 == 0:
            doubled = d * 2
            total += doubled if doubled < 10 else doubled - 9
        else:
            total += d
    check_digit = (10 - (total % 10)) % 10
    return check_digit == digits[-1]


def classify_series_enhanced(name: str, series: pd.Series, sample_size: int = 200) -> Dict[str, Any]:
    """Classify a series with additional checks for credit cards and SINs.

    This function derives the baseline risk from the column name using
    ``_column_risk_by_name`` and then scans a sample of values for
    strings that pass the Luhn check (credit card numbers) or the SIN
    check.  If such patterns are found the final risk is set to
    ``"High"`` regardless of the baseline risk.  Otherwise the final
    risk is the maximum of the name hint risk and the cell value risk.
    """
    # Determine baseline risk using existing name heuristics
    name_risk = _column_risk_by_name(name)
    # Collect sample of values
    sample = series.dropna().astype(str).head(sample_size).tolist()
    contains_card_or_sin = False
    for val in sample:
        s = "".join(ch for ch in val if ch.isdigit())
        # Check for potential credit card numbers (≥12 digits)
        if len(s) >= 12 and luhn_checksum(s):
            contains_card_or_sin = True
            break
        # Check for potential SIN
        if len(s) == 9 and detect_sin(s):
            contains_card_or_sin = True
            break
    if contains_card_or_sin:
        final_risk = "High"
    else:
        # Determine value-based risk (reuse risk_assessment logic)
        val_risk_rank = 0
        for v in sample:
            r = _cell_risk_by_value(v)
            val_risk_rank = max(val_risk_rank, {"Low": 0, "Medium": 1, "High": 2}[r])
            if val_risk_rank == 2:
                break
        # Map baseline risk to numeric
        base_rank = {"Low": 0, "Medium": 1, "High": 2}[name_risk]
        final_rank = max(base_rank, val_risk_rank)
        final_risk = ["Low", "Medium", "High"][final_rank]
    return {
        "column": name,
        "final_risk": final_risk,
        "contains_card_or_sin": contains_card_or_sin,
    }


def classify_dataframe_enhanced(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Classify all columns in a DataFrame with enhanced logic."""
    results: List[Dict[str, Any]] = []
    for col in df.columns:
        results.append(classify_series_enhanced(col, df[col]))
    return results


def calculate_risk_score(results: List[Dict[str, Any]]) -> Tuple[int, int, float]:
    """Calculate a numeric risk score for a dataset.

    Each column classified as High contributes 3 points, Medium 2 points
    and Low 1 point.  The total possible score is number_of_columns * 3.

    Args:
        results: List of classification results (e.g. from
            ``classify_dataframe_enhanced``).

    Returns:
        A tuple of (score, max_score, percentage).
    """
    risk_weights = {"Low": 1, "Medium": 2, "High": 3}
    score = sum(risk_weights.get(r.get("final_risk", "Low"), 1) for r in results)
    max_score = 3 * len(results) if results else 0
    pct = (score / max_score) * 100 if max_score > 0 else 0.0
    return score, max_score, pct


def generate_recommendations(results: List[Dict[str, Any]]) -> List[str]:
    """Provide actionable recommendations based on classification results."""
    recs: List[str] = []
    for r in results:
        if r.get("final_risk") == "High":
            col_name = r.get("column", "Unnamed")
            if r.get("contains_card_or_sin"):
                recs.append(
                    f"Column '{col_name}' appears to contain credit card numbers or SINs. Consider hashing or tokenising this data and limiting access."
                )
            else:
                recs.append(
                    f"Column '{col_name}' contains highly sensitive data. Ensure strong encryption, role‑based access control and audit logging."
                )
        elif r.get("final_risk") == "Medium":
            col_name = r.get("column", "Unnamed")
            recs.append(
                f"Column '{col_name}' contains moderately sensitive data. Review retention periods and apply appropriate pseudonymisation techniques."
            )
    if not recs:
        recs.append("Dataset appears low risk. Continue to monitor and apply basic safeguards.")
    return recs