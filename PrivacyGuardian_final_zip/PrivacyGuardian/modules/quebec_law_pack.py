"""
Quebec Law 25 Pack
===================

The Quebec Law 25 pack provides helpers to generate bilingual privacy
policies and supporting artefacts that are aligned with the
requirements of Bill 64 (now Law 25) in Quebec.  It builds on the
existing policy generator to produce both English and French language
versions, adds a bilingual privacy officer contact block, and offers
a simple EFVP/PIA worksheet template for evaluating factors that may
impact privacy.

For the French translation, a naive approach is used: the English
policy text is prefaced with a note explaining that an official
translation should be reviewed by qualified counsel.  Automatic
translation services are not invoked to avoid external API calls.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Any

import pandas as pd

from modules.policy_generator import generate_policy


def generate_bilingual_policy(
    company_name: str,
    contact_email: str,
    business_type: str = "general",
    template_style: str = "formal",
    include_ai: bool = True,
    policy_date: date | None = None,
) -> Dict[str, str]:
    """Generate English and French versions of a privacy policy.

    Args:
        company_name: Name of the organisation.
        contact_email: Contact email for privacy matters.
        business_type: Business sector (see ``policy_generator``).
        template_style: Style for the policy (formal, modern, etc.).
        include_ai: Whether to include the AI/automated decision section.
        policy_date: Date of the policy (defaults to today).

    Returns:
        A dictionary with keys ``'english'`` and ``'french'`` containing
        the respective policy texts.
    """
    if policy_date is None:
        policy_date = date.today()
    # Generate English version
    english = generate_policy(
        company_name=company_name,
        jurisdiction="Canada (Quebec)",
        contact_email=contact_email,
        include_ai=include_ai,
        policy_date=policy_date,
        business_type=business_type,
        template_style=template_style,
    )
    # Compose French version as placeholder translation
    french_header = (
        "# Politique de confidentialité\n\n"
        "**Note :** Ceci est une traduction indicative de la politique de confidentialité. "
        "Veuillez consulter un conseiller juridique francophone pour valider l'exactitude de la traduction.\n\n"
    )
    french_body = english  # In a real implementation you would translate this text
    french = french_header + french_body
    return {"english": english, "french": french}


def generate_officer_block(officer_name: str, contact_email: str, contact_phone: str | None = None) -> Dict[str, str]:
    """Generate a bilingual privacy officer contact block."""
    english = (
        f"**Privacy Officer:** {officer_name}\n\n"
        f"**Contact Email:** {contact_email}\n\n"
        + (f"**Contact Phone:** {contact_phone}\n" if contact_phone else "")
    )
    french = (
        f"**Responsable de la protection des renseignements personnels :** {officer_name}\n\n"
        f"**Courriel de contact :** {contact_email}\n\n"
        + (f"**Téléphone :** {contact_phone}\n" if contact_phone else "")
    )
    return {"english": english, "french": french}


def generate_efvp_worksheet() -> pd.DataFrame:
    """Return a blank EFVP/PIA worksheet as a DataFrame.

    The worksheet includes columns commonly used in Privacy Impact
    Assessments (PIAs) and Law 25 evaluations: processing activity,
    purpose, legal basis, sensitivity, third parties, safeguards and
    notes.  Users can download this sheet and fill it in.
    """
    columns = [
        "Processing Activity",
        "Purpose of Processing",
        "Legal Basis",
        "Sensitivity Level",
        "Third Parties/Recipients",
        "Safeguards",
        "Retention/Deletion",
        "Notes",
    ]
    df = pd.DataFrame([{c: "" for c in columns}])
    return df