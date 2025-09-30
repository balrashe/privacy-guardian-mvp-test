from __future__ import annotations
from datetime import date
from typing import Dict, List, Optional, Any

# Business type specific customizations
BUSINESS_TYPES = {
    "ecommerce": {
        "name": "E-commerce/Retail",
        "specific_sections": ["payment_processing", "order_fulfillment", "marketing"],
        "data_types": ["payment information", "purchase history", "shipping addresses", "product preferences"]
    },
    "healthcare": {
        "name": "Healthcare/Medical",
        "specific_sections": ["medical_records"],
        "data_types": ["medical records", "health information", "treatment data", "insurance information"]
    },
    "financial": {
        "name": "Financial Services",
        "specific_sections": ["financial_data"],
        "data_types": ["financial information", "account details", "transaction history", "investment data"]
    },
    "technology": {
        "name": "Technology/Software",
        "specific_sections": ["user_analytics"],
        "data_types": ["usage analytics", "technical logs", "user interactions", "system data"]
    },
    "professional": {
        "name": "Professional Services",
        "specific_sections": ["client_data"],
        "data_types": ["client information", "project data", "consultation records", "professional communications"]
    },
    "general": {
        "name": "General Business",
        "specific_sections": ["business_operations"],
        "data_types": ["customer information", "business communications", "service records"]
    }
}

HEADER_TEMPLATES = {
    "formal": "# Privacy Policy\n**Last updated:** {policy_date}\n**Company:** {company_name}\n**Contact:** {contact_email}\n",
    "modern": "# 🔒 Privacy Policy\n*Effective Date: {policy_date}*\n\n**{company_name}** | Privacy Contact: {contact_email}\n",
    "minimal": "# Privacy Policy\n{policy_date} | {company_name} | {contact_email}\n",
    "detailed": "# Privacy Policy for {company_name}\n\n**Document Information:**\n- Last Updated: {policy_date}\n- Company: {company_name}\n- Privacy Officer Contact: {contact_email}\n- Document Version: 1.0\n"
}

INTRO_TEMPLATES = {
    "canada_formal": "This Privacy Policy explains how {company_name} (\"we\", \"us\", \"our\") collects, uses, discloses, and protects personal information in accordance with Canadian privacy laws, including the Personal Information Protection and Electronic Documents Act (PIPEDA), the forthcoming Consumer Privacy Protection Act (CPPA), and AI-related provisions in the Artificial Intelligence and Data Act (AIDA) where applicable.",
    "canada_friendly": "At {company_name}, we take your privacy seriously. This policy explains how we handle your personal information in compliance with Canadian privacy laws (PIPEDA, CPPA, and AIDA).",
    "gdpr_formal": "This Privacy Policy explains how {company_name} (\"we\", \"us\", \"our\") collects, uses, discloses, and protects personal data in accordance with the EU General Data Protection Regulation (GDPR) and other applicable data protection laws.",
    "gdpr_friendly": "Welcome to {company_name}! This privacy policy explains how we handle your personal data in compliance with GDPR and other European privacy laws."
}

COMMON_SECTIONS = """## Information We Collect
We may collect identifiers (e.g., name, contact details), commercial information (e.g., transactions), device/network data (e.g., IP), and other information provided directly by you.

## Purposes and Lawful Bases
We process information to provide services, operate our business, ensure security, comply with legal obligations, and improve products. Where required, we rely on consent or other lawful bases (e.g., performance of a contract, legitimate interests).

## Disclosure and Sharing
We may disclose information to service providers, legal authorities when required, and in connection with business transactions. We do not sell personal information.

## Your Rights
You have rights to access, correct, delete, and port your information, as well as to withdraw consent and object to processing. Contact us at {contact_email} to exercise these rights.

## Security and Retention
We implement reasonable safeguards and retain information only as long as necessary for stated purposes or legal requirements.

## Contact Information
For privacy questions or to exercise your rights, contact us at {contact_email}."""

# Business-specific sections
BUSINESS_SECTIONS = {
    "payment_processing": """## Payment Processing
We collect and process payment information including credit card details, billing addresses, and transaction history to facilitate purchases and refunds. Payment data is processed through secure, PCI-DSS compliant payment processors and is not stored on our servers beyond transaction completion.""",

    "medical_records": """## Medical Information
We collect and maintain medical records, health information, and treatment data in accordance with healthcare privacy regulations. All health information is handled with the highest level of security and confidentiality, and access is strictly limited to authorized healthcare professionals involved in your care.""",

    "financial_data": """## Financial Information
We collect and process financial information including account details, transaction history, and investment data to provide financial services. All financial data is handled in compliance with applicable financial privacy regulations and industry security standards.""",

    "user_analytics": """## Usage Analytics and Technical Data
We collect technical information about how you use our software and services, including usage patterns, feature interactions, system performance data, and error logs. This information helps us improve our products and provide better user experiences.""",

    "client_data": """## Client and Professional Information
We collect and maintain client information, project data, and professional communications necessary to provide our services. All client information is handled with strict confidentiality and professional standards.""",

    "marketing": """## Marketing and Communications
We may use your information to send you promotional materials, product updates, and marketing communications. You can opt out of marketing communications at any time through the unsubscribe links in our emails or by contacting us directly.""",

    "order_fulfillment": """## Order Processing and Fulfillment
We collect shipping addresses, delivery preferences, and order history to process and fulfill your purchases. This information is used to coordinate delivery, handle returns, and provide customer service regarding your orders.""",

    "business_operations": """## Business Operations
We collect and maintain operational data necessary to conduct our business activities, including customer service interactions, support requests, and general business communications to provide quality service and support."""
}

AI_SECTION = """## Automated Decision-Making / AI
Where our services involve automated processing or AI systems with material impact, we assess and document risks, monitor outputs, maintain human oversight, and provide meaningful information about the logic involved, in line with applicable laws (e.g., AIDA/GDPR Article 22). You may contact us to request more information or to contest decisions."""

def generate_policy(
    company_name: str, 
    jurisdiction: str, 
    contact_email: str, 
    include_ai: bool, 
    policy_date: date,
    business_type: str = "general",
    template_style: str = "formal",
    custom_sections: Optional[List[str]] = None
) -> str:
    """
    Generate a customized privacy policy.
    
    Args:
        company_name: Name of the company
        jurisdiction: Legal jurisdiction (Canada/EU)
        contact_email: Privacy contact email
        include_ai: Whether to include AI/automated decision-making section
        policy_date: Date of the policy
        business_type: Type of business (ecommerce, healthcare, etc.)
        template_style: Style of the template (formal, modern, minimal, detailed)
        custom_sections: Additional custom sections to include
        
    Returns:
        Generated privacy policy text
    """
    # Select header template
    header_template = HEADER_TEMPLATES.get(template_style, HEADER_TEMPLATES["formal"])
    header = header_template.format(
        policy_date=policy_date.isoformat(), 
        company_name=company_name, 
        contact_email=contact_email
    )
    
    # Select intro template based on jurisdiction and style
    if "Canada" in jurisdiction:
        intro_key = "canada_friendly" if template_style in ["modern", "minimal"] else "canada_formal"
    else:
        intro_key = "gdpr_friendly" if template_style in ["modern", "minimal"] else "gdpr_formal"
    
    intro = INTRO_TEMPLATES[intro_key].format(company_name=company_name)
    
    # Build main sections
    sections = [COMMON_SECTIONS.format(contact_email=contact_email)]
    
    # Add business-specific sections
    if business_type in BUSINESS_TYPES:
        business_info = BUSINESS_TYPES[business_type]
        for section_key in business_info["specific_sections"]:
            if section_key in BUSINESS_SECTIONS:
                sections.append(BUSINESS_SECTIONS[section_key])
                
        # Customize data collection section
        data_types = ", ".join(business_info["data_types"])
        data_section = f"""## Types of Information We Collect
As a {business_info["name"]} business, we may collect the following types of information: {data_types}, along with standard business information such as contact details, service usage data, and communications."""
        sections.insert(1, data_section)
    
    # Add custom sections if provided
    if custom_sections:
        sections.extend(custom_sections)
    
    # Add AI section if requested
    if include_ai:
        sections.append(AI_SECTION)
        
    # Combine all sections
    body = "\n\n".join(sections)
    
    return "\n\n".join([header, intro, body]).strip()


def get_available_business_types() -> Dict[str, str]:
    """Get available business types for policy customization."""
    return {key: value["name"] for key, value in BUSINESS_TYPES.items()}


def get_available_template_styles() -> List[str]:
    """Get available template styles."""
    return list(HEADER_TEMPLATES.keys())


def generate_policy_preview(business_type: str, template_style: str) -> str:
    """Generate a preview of policy customization options."""
    business_info = BUSINESS_TYPES.get(business_type, BUSINESS_TYPES["general"])
    
    preview = f"""**Business Type:** {business_info["name"]}
**Template Style:** {template_style.title()}
**Specific Sections:** {", ".join(business_info["specific_sections"])}
**Data Types Covered:** {", ".join(business_info["data_types"])}"""
    
    return preview
