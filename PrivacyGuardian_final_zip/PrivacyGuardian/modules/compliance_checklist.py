from __future__ import annotations

CHECKLIST = {
    "privacy_officer": {
        "question": "Have you designated a privacy officer / accountable lead?",
        "weight": 3,
        "recommendation": "Appoint a privacy officer with clear accountability and publish contact details."
    },
    "pmp": {
        "question": "Do you maintain a documented Privacy Management Program (PMP)?",
        "weight": 4,
        "recommendation": "Document your PMP (policies, roles, training, DPIAs/PIAs, incident response)."
    },
    "data_inventory": {
        "question": "Have you completed a current data inventory / mapping of systems and flows?",
        "weight": 3,
        "recommendation": "Conduct and maintain a data inventory with owners, purposes, and retention."
    },
    "consent": {
        "question": "Do you obtain appropriate consent or rely on valid lawful bases for processing?",
        "weight": 3,
        "recommendation": "Review consent mechanisms and lawful bases; align notices and records."
    },
    "dsar": {
        "question": "Can you fulfill data subject requests (access/correction/deletion/portability) within statutory timelines?",
        "weight": 3,
        "recommendation": "Establish DSAR procedures, contacts, identity verification, and timelines."
    },
    "security": {
        "question": "Do you implement technical and organizational safeguards appropriate to data sensitivity?",
        "weight": 4,
        "recommendation": "Adopt encryption, access controls, logging/monitoring, and secure SDLC practices."
    },
    "vendors": {
        "question": "Are vendor contracts in place with privacy/security terms and risk management?",
        "weight": 2,
        "recommendation": "Use DPAs, conduct vendor risk reviews, and track subprocessors."
    },
    "retention": {
        "question": "Do you have and enforce data retention and deletion schedules?",
        "weight": 2,
        "recommendation": "Define retention by purpose and legal obligations; implement secure deletion."
    },
    "incident": {
        "question": "Do you have an incident response plan with breach notification procedures?",
        "weight": 3,
        "recommendation": "Draft and test IR playbooks; define roles, timelines, and regulator/individual notices."
    },
    "ai_governance": {
        "question": "If you use AI systems, do you assess risks and document transparency/oversight measures?",
        "weight": 3,
        "recommendation": "Run AI risk assessments (impact, bias, explainability), log decisions, and enable human review."
    }
}

def score_responses(responses: dict) -> tuple[int, int, float]:
    score = 0
    max_score = sum(v["weight"] for v in CHECKLIST.values())
    for key, val in responses.items():
        if val.lower() == "yes":
            score += CHECKLIST[key]["weight"]
    pct = (score / max_score) * 100 if max_score else 0.0
    return score, max_score, pct

def recommendations_for_responses(responses: dict) -> list[str]:
    recs = []
    for key, val in responses.items():
        if val.lower() != "yes":
            recs.append(CHECKLIST[key]["recommendation"])
    return recs
