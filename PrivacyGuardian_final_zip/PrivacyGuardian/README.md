# Privacy Guardian — MVP

AI-powered privacy compliance assistant for SMBs (Canada-first). Includes:
- Data Risk Assessment: classify columns in CSVs by sensitivity.
- Privacy Policy Generator: CPPA/AIDA/PIPEDA-aware template (optionally GDPR).
- Compliance Checklist: weighted scoring with actionable recommendations.

Privacy by design: Uploaded files are processed in memory only. The app does not write user data to disk or transmit it to external services.

## Quickstart (Streamlit)

```bash
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install streamlit pandas numpy python-dateutil pydantic altair
streamlit run app.py --server.port 5000
