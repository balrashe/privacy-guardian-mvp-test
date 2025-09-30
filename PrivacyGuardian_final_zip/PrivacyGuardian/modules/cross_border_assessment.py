"""
Cross‑Border Transfer Assessment
===============================

This module implements a rudimentary Transfer Impact Assessment (TIA)
for cross‑border transfers of personal information, including a
Quebec Law 25 perspective.  It collects information about the
destination jurisdiction, the categories of data being transferred,
the lawful basis for the transfer and any mitigation measures, then
provides a qualitative risk rating and a text summary.  The output
should assist organisations in documenting their considerations when
transferring personal information outside of Canada.

The risk model used here is deliberately simple: countries with
comprehensive privacy laws similar to those in Canada (e.g., EU
member states, the United Kingdom) are considered lower risk,
transfers to the United States are medium risk owing to sectoral
laws, and transfers to other jurisdictions are high risk by default.
This is provided for demonstration purposes only and does not
constitute legal advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any


@dataclass
class CrossBorderInput:
    """Information required for a cross‑border transfer assessment."""
    destination_country: str
    data_categories: List[str]
    lawful_basis: str  # consent, contractual necessity, etc.
    mitigation_measures: str = ""


def _risk_level_for_country(country: str) -> str:
    """Classify the risk level based on the destination country."""
    country_lc = country.lower()
    eu_countries = {
        "austria", "belgium", "bulgaria", "croatia", "cyprus", "czech republic",
        "denmark", "estonia", "finland", "france", "germany", "greece", "hungary",
        "ireland", "italy", "latvia", "lithuania", "luxembourg", "malta", "netherlands",
        "poland", "portugal", "romania", "slovakia", "slovenia", "spain", "sweden"
    }
    if country_lc in eu_countries or country_lc in {"united kingdom", "uk", "european union"}:
        return "Low"
    if country_lc in {"united states", "usa", "u.s.", "u.s.a."}:
        return "Medium"
    if country_lc in {"canada", "quebec"}:
        return "Low"
    # Default to high risk for other jurisdictions
    return "High"


def assess_cross_border_transfer(cb_input: CrossBorderInput) -> Dict[str, Any]:
    """Return a qualitative assessment of a cross‑border transfer.

    Args:
        cb_input: Input details about the transfer.

    Returns:
        A dictionary containing the assessment date, risk level, a summary
        narrative and recommended considerations under Quebec Law 25.
    """
    risk_level = _risk_level_for_country(cb_input.destination_country)
    narrative_lines: List[str] = []
    narrative_lines.append(
        f"You have indicated a transfer of personal information to {cb_input.destination_country}. "
        f"The data categories involved are: {', '.join(cb_input.data_categories) or 'not specified'}."
    )
    narrative_lines.append(
        f"Lawful basis for transfer: {cb_input.lawful_basis}. "
        f"Mitigation measures: {cb_input.mitigation_measures or 'None provided'}."
    )
    narrative_lines.append(
        f"Based on our simplified jurisdiction model, the risk associated with transfers to this country is considered <b>{risk_level}</b>."
    )
    # Quebec Law 25 context
    narrative_lines.append(
        "Under Quebec’s Law 25, organisations must perform a transfer impact assessment (TIA) "
        "that considers the sensitivity of the information, the purposes and benefits of the transfer, "
        "the legal regime applicable in the destination country and the safeguards in place to protect the information."
    )
    narrative_lines.append(
        "This tool provides a high‑level indication only. You should document the specific legal provisions of "
        f"{cb_input.destination_country} and evaluate whether they offer protections equivalent to those in Quebec/Canada."
    )
    recommendations = []
    if risk_level == "High":
        recommendations.append(
            "Conduct a detailed TIA including consultation with legal counsel and consider additional contractual or technical safeguards (e.g. encryption, data localisation)."
        )
    elif risk_level == "Medium":
        recommendations.append(
            "Review relevant laws and enforcement practices in the destination country and implement appropriate contractual clauses (e.g. SCCs)."
        )
    else:
        recommendations.append(
            "Ensure that data processing agreements are in place and that ongoing monitoring of the legal landscape is performed."
        )

    return {
        "assessment_date": datetime.now().isoformat(),
        "risk_level": risk_level,
        "narrative": "\n".join(narrative_lines),
        "recommendations": recommendations,
    }