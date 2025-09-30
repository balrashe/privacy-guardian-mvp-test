"""
Flask-based frontend for Privacy Guardian.

This lightweight web application exposes the underlying risk assessment,
policy generation and compliance checklist modules through a simple
multi-page interface that is easy for non-technical users at SMBs to navigate.

To run the app locally, install the dependencies and execute:

    python frontend/app.py

The server will start on http://0.0.0.0:8000 by default.
"""

import io
import base64
import os
import sys
from datetime import date
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, make_response
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend for server
import matplotlib.pyplot as plt

# Make sure the parent directory (repository root) is in sys.path so that
# ``import modules`` works even when running this script from within the
# ``frontend`` directory. Without this adjustment Python would only search
# ``frontend/`` for modules.
PARENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Import our core modules. These reside in ``modules`` at the project root.
from modules.risk_assessment import classify_dataframe, summarize_risk_levels  # type: ignore
from modules.policy_generator import generate_policy, get_available_business_types, get_available_template_styles  # type: ignore
from modules.compliance_checklist import (
    CHECKLIST,
    score_responses,
    recommendations_for_responses,
)
from modules.csv_validator import validate_csv_file, format_validation_messages  # type: ignore
from modules.ml_risk_classifier import classify_dataframe_hybrid  # type: ignore
from modules.export_reports import export_risk_assessment_pdf, export_compliance_audit_pdf, export_combined_excel_report  # type: ignore
from modules.session_manager import get_session_manager, SessionData  # type: ignore
from modules.session_ui_helpers import get_progress_indicators_flask, update_module_progress, mark_module_completed  # type: ignore

# Import enhanced risk scoring functions
from modules.risk_scoring_enhancements import classify_dataframe_enhanced, calculate_risk_score, generate_recommendations  # type: ignore

# Import RROSH decision functions
from modules.rrosh_decision import RROSHInput, generate_rrosh_decision, memo_to_pdf  # type: ignore

# Import breach record book classes
from modules.breach_record import BreachRecordBook, BreachEvent  # type: ignore

# Import DSAR factory functions
from modules.dsar_factory import generate_dsar_summary, generate_dsar_letter, dsar_to_pdf  # type: ignore

# Import cross-border assessment functions
from modules.cross_border_assessment import CrossBorderInput, assess_cross_border_transfer  # type: ignore

# Import Quebec Law 25 pack functions
from modules.quebec_law_pack import generate_bilingual_policy, generate_officer_block, generate_efvp_worksheet  # type: ignore

# Import processing inventory classes
from modules.processing_inventory import ProcessingInventory, ProcessingActivity  # type: ignore

app = Flask(__name__)

# Session configuration
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Initialize session manager
session_manager = get_session_manager()


def get_or_create_session():
    """Get or create a session for the current user"""
    session_id = session.get('privacy_guardian_session_id')
    
    if session_id:
        # Try to retrieve existing session
        user_session = session_manager.get_session(session_id)
        if user_session:
            return user_session
    
    # Create new session
    user_agent = request.headers.get('User-Agent', 'Unknown')
    user_session = session_manager.create_session(frontend_type="flask", user_agent=user_agent)
    session['privacy_guardian_session_id'] = user_session.session_id
    session.permanent = True
    
    return user_session


def save_session_data(user_session):
    """Save session data to storage"""
    session_manager.save_session(user_session)


@app.route("/")
def home() -> str:
    """Landing page describing the application."""
    user_session = get_or_create_session()
    progress_data = get_progress_indicators_flask(user_session)
    return render_template("home.html", progress_data=progress_data, session_data=user_session)


@app.route("/session/export")
def export_session():
    """Export current session data as JSON"""
    user_session = get_or_create_session()
    export_data = session_manager.export_session(user_session)
    
    response = make_response(export_data)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename=privacy_guardian_session_{date.today().isoformat()}.json'
    return response


@app.route("/session/import", methods=["POST"])
def import_session():
    """Import session data from JSON file"""
    if 'session_file' not in request.files:
        return redirect(url_for('home'))
    
    file = request.files['session_file']
    if file.filename == '':
        return redirect(url_for('home'))
    
    try:
        import_data = file.read().decode('utf-8')
        imported_session = session_manager.import_session(import_data, frontend_type="flask")
        
        if imported_session:
            session['privacy_guardian_session_id'] = imported_session.session_id
            session.permanent = True
            return redirect(url_for('home'))
        else:
            return render_template("home.html", error="Failed to import session. Please check the file format.")
    
    except Exception as e:
        return render_template("home.html", error=f"Error importing session: {str(e)}")


@app.route("/session/clear")
def clear_session():
    """Clear current session and start a new one"""
    session_id = session.get('privacy_guardian_session_id')
    if session_id:
        session_manager.delete_session(session_id)
    
    session.clear()
    return redirect(url_for('home'))


@app.route("/risk", methods=["GET", "POST"])
def risk():
    """
    Data risk assessment page. Provides a form for uploading a CSV or using the
    built-in sample, then displays classification results and a risk summary.
    """
    user_session = get_or_create_session()
    progress_data = get_progress_indicators_flask(user_session)
    
    if request.method == "POST":
        # Determine the source of the data frame with validation
        df = None
        validation_result = None
        
        if request.form.get("use_sample"):
            sample_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sample_customers.csv")
            df, validation_result = validate_csv_file(sample_path)
        else:
            uploaded_file = request.files.get("csv_file")
            if not uploaded_file or uploaded_file.filename == "":
                return render_template(
                    "risk.html", error="Please upload a CSV or select the sample."
                )
            df, validation_result = validate_csv_file(uploaded_file.stream, uploaded_file.filename)
            
        # Check validation results
        if validation_result and not validation_result.is_valid:
            validation_messages = format_validation_messages(validation_result)
            return render_template(
                "risk.html", 
                error="CSV validation failed",
                validation_messages=validation_messages
            )
            
        if df is None:
            return render_template(
                "risk.html", error="Failed to process CSV file."
            )
            
        # Classify columns based on user selection
        classification_method = request.form.get("classification_method", "hybrid")
        
        if classification_method == "hybrid":
            try:
                results = classify_dataframe_hybrid(df)
                # Calculate summary for hybrid results
                summary = {"High": 0, "Medium": 0, "Low": 0}
                for result in results:
                    risk_level = result.get("hybrid_final_risk", "Low")
                    summary[risk_level] += 1
            except Exception:
                # Fallback to rule-based if ML fails
                results = classify_dataframe(df)
                summary = summarize_risk_levels(results)
        else:
            # Use rule-based only
            results = classify_dataframe(df)
            summary = summarize_risk_levels(results)
        # Save results to session
        dataset_name = "Uploaded File" if not request.form.get("use_sample") else "Sample Dataset"
        method_name = "Hybrid (ML + Rules)" if classification_method == "hybrid" else "Rule-based Only"
        
        user_session.risk_assessment.dataset_name = dataset_name
        user_session.risk_assessment.classification_method = method_name
        user_session.risk_assessment.classification_results = results
        user_session.risk_assessment.risk_summary = summary
        user_session.risk_assessment.total_rows = len(df)
        
        # Mark module as completed
        mark_module_completed(user_session, "risk_assessment", session_manager)

        # Build a bar chart image for the summary
        fig, ax = plt.subplots()
        categories = list(summary.keys())
        counts = [summary[k] for k in categories]
        ax.bar(categories, counts)
        ax.set_title("Risk Summary")
        ax.set_xlabel("Risk Level")
        ax.set_ylabel("Count")
        # Save the plot to a PNG in memory
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        chart_data = base64.b64encode(buf.read()).decode("utf-8")
        # Convert classification results to an HTML table
        table_df = pd.DataFrame(results)
        table_html = table_df.to_html(
            classes="table table-striped",
            index=False,
            escape=True,  # Fix XSS vulnerability
            border=0,
        )
        return render_template(
            "risk.html",
            table_html=table_html,
            chart_data=chart_data,
            summary=summary,
            show_exports=True,
            results=results,
            df_rows=len(df) if df is not None else 0,
            classification_method=classification_method,
            dataset_name=dataset_name,
            progress_data=progress_data,
            session_saved=True
        )
    # GET request - check for existing data in session
    existing_data = user_session.risk_assessment
    has_existing_data = existing_data and existing_data.classification_results
    
    return render_template("risk.html", 
                         progress_data=progress_data, 
                         has_existing_data=has_existing_data,
                         existing_data=existing_data)


@app.route("/policy", methods=["GET", "POST"])
def policy():
    """
    Privacy policy generator page. Collects company information, business type,
    and template style, then produces a customized privacy policy.
    """
    user_session = get_or_create_session()
    progress_data = get_progress_indicators_flask(user_session)
    
    # Get customization options
    business_types = get_available_business_types()
    template_styles = get_available_template_styles()
    
    if request.method == "POST":
        company = request.form.get("company") or "Example Co."
        jurisdiction = request.form.get("jurisdiction") or "Canada"
        business_type = request.form.get("business_type") or "general"
        template_style = request.form.get("template_style") or "formal"
        include_ai = bool(request.form.get("include_ai"))
        contact_email = request.form.get("contact_email") or "privacy@example.com"
        
        # Map short jurisdiction identifiers to module values
        juris_map = {
            "Canada": "Canada (PIPEDA/CPPA/AIDA)",
            "EU": "European Union (GDPR)",
        }
        juris_string = juris_map.get(jurisdiction, jurisdiction)
        
        policy_text = generate_policy(
            company_name=company,
            jurisdiction=juris_string,
            contact_email=contact_email,
            include_ai=include_ai,
            policy_date=date.today(),
            business_type=business_type,
            template_style=template_style
        )
        
        # Save to session
        user_session.policy_generator.company_name = company
        user_session.policy_generator.contact_email = contact_email
        user_session.policy_generator.jurisdiction = juris_string
        user_session.policy_generator.business_type = business_type
        user_session.policy_generator.template_style = template_style
        user_session.policy_generator.include_ai = include_ai
        user_session.policy_generator.generated_policy = policy_text
        user_session.policy_generator.policy_date = date.today().isoformat()
        
        # Mark module as completed
        mark_module_completed(user_session, "policy_generator", session_manager)
        
        file_name = f"{company.replace(' ', '_')}_Privacy_Policy.txt"
        return render_template(
            "policy.html",
            policy=policy_text,
            file_name=file_name,
            company=company,
            jurisdiction=jurisdiction,
            business_type=business_type,
            template_style=template_style,
            include_ai=include_ai,
            contact_email=contact_email,
            business_types=business_types,
            template_styles=template_styles,
            progress_data=progress_data,
            session_saved=True
        )
    # GET request - check for existing policy data
    existing_policy = user_session.policy_generator
    has_existing_policy = existing_policy and existing_policy.generated_policy
    
    return render_template(
        "policy.html",
        business_types=business_types,
        template_styles=template_styles,
        progress_data=progress_data,
        has_existing_policy=has_existing_policy,
        existing_policy=existing_policy
    )


@app.route("/checklist", methods=["GET", "POST"])
def checklist():
    """
    Compliance checklist page. Presents a series of yes/no questions and
    calculates a weighted score along with recommendations for any gaps.
    """
    user_session = get_or_create_session()
    progress_data = get_progress_indicators_flask(user_session)
    
    if request.method == "POST":
        responses = {}
        for key in CHECKLIST.keys():
            responses[key] = request.form.get(key, "No")
        score, max_score, pct = score_responses(responses)
        recs = recommendations_for_responses(responses)
        
        # Save to session
        user_session.compliance_checklist.responses = responses
        user_session.compliance_checklist.score = score
        user_session.compliance_checklist.max_score = max_score
        user_session.compliance_checklist.percentage = pct
        user_session.compliance_checklist.recommendations = recs
        
        # Mark module as completed
        mark_module_completed(user_session, "compliance_checklist", session_manager)
        
        return render_template(
            "checklist.html",
            checklist=CHECKLIST,
            score=score,
            max_score=max_score,
            pct=round(pct),
            recommendations=recs,
            progress_data=progress_data,
            session_saved=True
        )
    
    # GET request - check for existing compliance data
    existing_compliance = user_session.compliance_checklist
    has_existing_compliance = existing_compliance and existing_compliance.responses
    
    return render_template("checklist.html", 
                         checklist=CHECKLIST, 
                         progress_data=progress_data,
                         has_existing_compliance=has_existing_compliance,
                         existing_compliance=existing_compliance)


# -------------------------------------------------------------------------
# Enhanced Risk Scoring
# -------------------------------------------------------------------------
@app.route("/enhanced_risk", methods=["GET", "POST"])
def enhanced_risk() -> str:
    """
    Enhanced risk scoring page. Performs detailed scoring using Luhn and SIN
    checks and produces recommendations based on detected patterns.
    """
    user_session = get_or_create_session()
    progress_data = get_progress_indicators_flask(user_session)
    if request.method == "POST":
        df = None
        validation_result = None
        if request.form.get("use_sample"):
            sample_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sample_customers.csv")
            df, validation_result = validate_csv_file(sample_path)
        else:
            uploaded_file = request.files.get("csv_file")
            if not uploaded_file or uploaded_file.filename == "":
                return render_template(
                    "enhanced_risk.html",
                    error="Please upload a CSV or select the sample.",
                    progress_data=progress_data,
                )
            df, validation_result = validate_csv_file(uploaded_file.stream, uploaded_file.filename)
        if validation_result and not validation_result.is_valid:
            validation_messages = format_validation_messages(validation_result)
            return render_template(
                "enhanced_risk.html",
                error="CSV validation failed",
                validation_messages=validation_messages,
                progress_data=progress_data,
            )
        if df is None:
            return render_template(
                "enhanced_risk.html", error="Failed to process CSV file.", progress_data=progress_data
            )
        # Perform enhanced risk scoring
        results = classify_dataframe_enhanced(df)
        score, max_score, pct = calculate_risk_score(results)
        recs = generate_recommendations(results)
        # Convert results to table HTML
        table_df = pd.DataFrame(results)
        table_html = table_df.to_html(
            classes="table table-striped",
            index=False,
            escape=True,
            border=0,
        )
        # Save progress and mark module completed
        user_session.risk_assessment.dataset_name = user_session.risk_assessment.dataset_name or "Enhanced Dataset"
        user_session.risk_assessment.total_rows = len(df)
        mark_module_completed(user_session, "enhanced_risk_scoring", session_manager)
        return render_template(
            "enhanced_risk.html",
            table_html=table_html,
            score=score,
            max_score=max_score,
            pct=pct,
            recommendations=recs,
            progress_data=progress_data,
        )
    # GET request
    return render_template("enhanced_risk.html", progress_data=progress_data)


# -------------------------------------------------------------------------
# RROSH Decision Wizard
# -------------------------------------------------------------------------
@app.route("/rrosh", methods=["GET", "POST"])
def rrosh() -> str:
    """
    RROSH Decision Wizard page. Assess whether a breach results in real risk of
    significant harm and determine notification requirements.
    """
    user_session = get_or_create_session()
    progress_data = get_progress_indicators_flask(user_session)
    if request.method == "POST":
        description = request.form.get("description", "")
        sensitivity = request.form.get("sensitivity", "Medium")
        probability = request.form.get("probability", "Medium")
        mitigation = request.form.get("mitigation", "")
        # Build input and generate decision
        try:
            input_data = RROSHInput(
                description=description,
                sensitivity=sensitivity,
                probability=probability,
                mitigation=mitigation,
            )
            memo = generate_rrosh_decision(input_data)
            # Mark module as completed
            mark_module_completed(user_session, "rrosh_decision", session_manager)
            return render_template(
                "rrosh.html",
                memo=memo,
                progress_data=progress_data,
            )
        except Exception as e:
            return render_template(
                "rrosh.html",
                error=f"Error generating decision: {str(e)}",
                progress_data=progress_data,
            )
    # GET request
    return render_template("rrosh.html", progress_data=progress_data)


@app.route("/rrosh_export", methods=["POST"])
def rrosh_export() -> str:
    """Export RROSH decision memo as PDF"""
    from flask import Response
    import json
    try:
        memo_json = request.form.get("memo_data", "{}")
        memo_data = json.loads(memo_json)
        pdf_data = memo_to_pdf(memo_data)
        filename = f"rrosh_decision_{date.today().isoformat()}.pdf"
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename={filename}'},
        )
    except Exception:
        return "Error generating PDF", 500


# -------------------------------------------------------------------------
# Breach Record Book
# -------------------------------------------------------------------------
@app.route("/breach", methods=["GET", "POST"])
def breach() -> str:
    """
    Breach record book page. Allows users to log privacy breaches and
    maintain a record for 24 months. Users can also export the log.
    """
    user_session = get_or_create_session()
    progress_data = get_progress_indicators_flask(user_session)
    # Ensure breach record book exists
    book = getattr(user_session, 'breach_record_book', None)
    if book is None:
        book = BreachRecordBook()
        user_session.breach_record_book = book
    if request.method == "POST":
        # Add a new breach record
        try:
            date_str = request.form.get("breach_date")
            if not date_str:
                raise ValueError("Date is required")
            breach_date = date.fromisoformat(date_str)
            description = request.form.get("description", "")
            containment = request.form.get("containment", "")
            harm = request.form.get("harm", "")
            reported = bool(request.form.get("reported"))
            event = BreachEvent(
                date=breach_date,
                description=description,
                containment=containment,
                harm=harm,
                reported=reported,
            )
            book.add_record(event)
            # Mark module as started/completed
            if len(book.records) > 0:
                mark_module_completed(user_session, "breach_record_book", session_manager)
        except Exception as e:
            return render_template(
                "breach.html",
                error=f"Failed to add breach record: {str(e)}",
                records=book.get_recent_records(),
                progress_data=progress_data,
            )
    # GET or after POST: show records
    records = book.get_recent_records()
    records_df = pd.DataFrame(book.to_dataframe(include_all=False)) if records else None
    return render_template(
        "breach.html",
        records=records_df,
        progress_data=progress_data,
    )


@app.route("/breach_export_pdf", methods=["POST"])
def breach_export_pdf():
    """Export breach log as PDF"""
    from flask import Response
    user_session = get_or_create_session()
    book = getattr(user_session, 'breach_record_book', None)
    if not book:
        return "No breach records", 400
    pdf_data = book.to_pdf(include_all=True)
    filename = f"breach_record_{date.today().isoformat()}.pdf"
    return Response(
        pdf_data,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


@app.route("/breach_export_excel", methods=["POST"])
def breach_export_excel():
    """Export breach log as Excel"""
    from flask import Response
    user_session = get_or_create_session()
    book = getattr(user_session, 'breach_record_book', None)
    if not book:
        return "No breach records", 400
    excel_data = book.to_excel(include_all=True)
    filename = f"breach_record_{date.today().isoformat()}.xlsx"
    return Response(
        excel_data,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


# -------------------------------------------------------------------------
# DSAR Dossier Factory
# -------------------------------------------------------------------------
@app.route("/dsar", methods=["GET", "POST"])
def dsar() -> str:
    """
    DSAR Dossier Factory page. Generates a Data Subject Access Request dossier
    summarising the personal data held about an individual.
    """
    user_session = get_or_create_session()
    progress_data = get_progress_indicators_flask(user_session)
    if request.method == "POST":
        subject_name = request.form.get("subject_name", "John Doe")
        contact_email = request.form.get("contact_email", "privacy@example.com")
        use_sample = bool(request.form.get("use_sample"))
        df = None
        validation_result = None
        if use_sample:
            sample_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sample_customers.csv")
            df, validation_result = validate_csv_file(sample_path)
        else:
            uploaded_file = request.files.get("csv_file")
            if not uploaded_file or uploaded_file.filename == "":
                return render_template(
                    "dsar.html",
                    error="Please upload a CSV or select the sample.",
                    subject_name=subject_name,
                    contact_email=contact_email,
                    progress_data=progress_data,
                )
            df, validation_result = validate_csv_file(uploaded_file.stream, uploaded_file.filename)
        if validation_result and not validation_result.is_valid:
            validation_messages = format_validation_messages(validation_result)
            return render_template(
                "dsar.html",
                error="CSV validation failed",
                validation_messages=validation_messages,
                subject_name=subject_name,
                contact_email=contact_email,
                progress_data=progress_data,
            )
        if df is None:
            return render_template(
                "dsar.html",
                error="Failed to process CSV file.",
                subject_name=subject_name,
                contact_email=contact_email,
                progress_data=progress_data,
            )
        # Generate DSAR summary and letter
        summary = generate_dsar_summary(df, subject_name)
        letter = generate_dsar_letter(summary, contact_email)
        table_df = pd.DataFrame(summary.classification_results)
        table_html = table_df.to_html(
            classes="table table-striped",
            index=False,
            escape=True,
            border=0,
        )
        # Mark module as completed
        mark_module_completed(user_session, "dsar_factory", session_manager)
        return render_template(
            "dsar.html",
            summary=summary,
            letter=letter,
            table_html=table_html,
            subject_name=subject_name,
            contact_email=contact_email,
            progress_data=progress_data,
        )
    # GET
    return render_template(
        "dsar.html",
        subject_name="John Doe",
        contact_email="privacy@example.com",
        progress_data=progress_data,
    )


@app.route("/dsar_export_pdf", methods=["POST"])
def dsar_export_pdf() -> str:
    """Export DSAR dossier as PDF"""
    from flask import Response
    import json
    try:
        summary_json = request.form.get("summary_data", "{}")
        letter = request.form.get("letter", "")
        summary_data = json.loads(summary_json)
        # Reconstruct summary object fields for PDF export
        pdf_data = dsar_to_pdf(summary_data, letter)
        filename = f"dsar_dossier_{date.today().isoformat()}.pdf"
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename={filename}'},
        )
    except Exception:
        return "Error generating DSAR PDF", 500


# -------------------------------------------------------------------------
# Cross-Border Transfer Assessment
# -------------------------------------------------------------------------
@app.route("/cross_border", methods=["GET", "POST"])
def cross_border() -> str:
    """
    Cross-border transfer assessment page. Evaluates risk associated with
    transferring personal information outside Canada and produces a TIA
    narrative.
    """
    user_session = get_or_create_session()
    progress_data = get_progress_indicators_flask(user_session)
    if request.method == "POST":
        dest = request.form.get("dest", "United States")
        categories_input = request.form.get("categories", "")
        lawful_basis = request.form.get("lawful_basis", "Consent")
        mitigation_measures = request.form.get("mitigation_measures", "")
        categories = [c.strip() for c in categories_input.split(',') if c.strip()]
        cb_input = CrossBorderInput(
            destination_country=dest,
            data_categories=categories,
            lawful_basis=lawful_basis,
            mitigation_measures=mitigation_measures,
        )
        assessment = assess_cross_border_transfer(cb_input)
        # Mark as completed
        mark_module_completed(user_session, "cross_border_assessment", session_manager)
        return render_template(
            "cross_border.html",
            dest=dest,
            categories=categories,
            lawful_basis=lawful_basis,
            mitigation_measures=mitigation_measures,
            assessment=assessment,
            progress_data=progress_data,
        )
    # GET
    return render_template(
        "cross_border.html",
        dest="United States",
        categories=[],
        lawful_basis="Consent",
        mitigation_measures="",
        progress_data=progress_data,
    )


# -------------------------------------------------------------------------
# Quebec Law 25 Pack
# -------------------------------------------------------------------------
@app.route("/quebec", methods=["GET", "POST"])
def quebec() -> str:
    """
    Quebec Law 25 pack page. Generates bilingual privacy policies, privacy
    officer contact block, and EFVP/PIA worksheet tailored to Quebec’s
    requirements.
    """
    user_session = get_or_create_session()
    progress_data = get_progress_indicators_flask(user_session)
    # Get options for business types and template styles
    business_types = get_available_business_types()
    template_styles = get_available_template_styles()
    if request.method == "POST":
        company_name = request.form.get("company_name", "Example Co.")
        contact_email = request.form.get("contact_email", "privacy@example.com")
        officer_name = request.form.get("officer_name", "Jane Doe")
        officer_phone = request.form.get("officer_phone", "")
        business_type = request.form.get("business_type", list(business_types.keys())[0])
        template_style = request.form.get("template_style", template_styles[0])
        include_ai = bool(request.form.get("include_ai"))
        try:
            policies = generate_bilingual_policy(
                company_name=company_name,
                contact_email=contact_email,
                business_type=business_type,
                template_style=template_style,
                include_ai=include_ai,
                policy_date=date.today(),
            )
            officer_block = generate_officer_block(
                officer_name,
                contact_email,
                officer_phone if officer_phone else None,
            )
            worksheet = generate_efvp_worksheet()
            # Convert worksheet to HTML table
            worksheet_html = worksheet.to_html(
                classes="table table-striped",
                index=False,
                border=0,
            )
            # Mark module as completed
            mark_module_completed(user_session, "quebec_pack", session_manager)
            return render_template(
                "quebec.html",
                company_name=company_name,
                contact_email=contact_email,
                officer_name=officer_name,
                officer_phone=officer_phone,
                business_type=business_type,
                template_style=template_style,
                include_ai=include_ai,
                policies=policies,
                officer_block=officer_block,
                worksheet_html=worksheet_html,
                business_types=business_types,
                template_styles=template_styles,
                progress_data=progress_data,
            )
        except Exception as e:
            return render_template(
                "quebec.html",
                error=f"Error generating pack: {str(e)}",
                business_types=business_types,
                template_styles=template_styles,
                progress_data=progress_data,
            )
    # GET
    return render_template(
        "quebec.html",
        business_types=business_types,
        template_styles=template_styles,
        company_name="Example Co.",
        contact_email="privacy@example.com",
        officer_name="Jane Doe",
        officer_phone="",
        include_ai=True,
        progress_data=progress_data,
    )


@app.route("/quebec_download_worksheet", methods=["POST"])
def quebec_download_worksheet() -> str:
    """Download EFVP/PIA worksheet as Excel"""
    from flask import Response
    import json
    try:
        # Data is not needed because we regenerate worksheet
        worksheet = generate_efvp_worksheet()
        buf = io.BytesIO()
        worksheet.to_excel(buf, index=False)
        buf.seek(0)
        filename = f"pii_worksheet_{date.today().isoformat()}.xlsx"
        return Response(
            buf.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename={filename}'},
        )
    except Exception:
        return "Error generating worksheet", 500


# -------------------------------------------------------------------------
# Processing Inventory
# -------------------------------------------------------------------------
@app.route("/inventory", methods=["GET", "POST"])
def inventory() -> str:
    """
    Processing inventory page. Allows users to maintain a record of
    processing activities and export the inventory to Excel.
    """
    user_session = get_or_create_session()
    progress_data = get_progress_indicators_flask(user_session)
    inventory_obj = getattr(user_session, 'processing_inventory', None)
    if inventory_obj is None:
        inventory_obj = ProcessingInventory()
        user_session.processing_inventory = inventory_obj
    if request.method == "POST":
        activity_name = request.form.get("activity_name", "")
        purpose = request.form.get("purpose", "")
        data_categories = request.form.get("data_categories", "")
        recipients = request.form.get("recipients", "")
        retention = request.form.get("retention", "")
        safeguards = request.form.get("safeguards", "")
        pipeda_principles = request.form.get("pipeda_principles", "")
        if activity_name:
            activity = ProcessingActivity(
                activity_name=activity_name,
                purpose=purpose,
                data_categories=data_categories,
                recipients=recipients,
                retention=retention,
                safeguards=safeguards,
                pipeda_principles=pipeda_principles,
            )
            inventory_obj.add_activity(activity)
            # Update progress
            mark_module_completed(user_session, "processing_inventory", session_manager)
    # Prepare table
    if inventory_obj.activities:
        df = inventory_obj.to_dataframe()
        table_html = df.to_html(
            classes="table table-striped",
            index=False,
            border=0,
        )
    else:
        table_html = None
    return render_template(
        "inventory.html",
        table_html=table_html,
        progress_data=progress_data,
    )


@app.route("/inventory_export_excel", methods=["POST"])
def inventory_export_excel() -> str:
    """Export processing inventory as Excel"""
    from flask import Response
    user_session = get_or_create_session()
    inventory_obj = getattr(user_session, 'processing_inventory', None)
    if not inventory_obj or not inventory_obj.activities:
        return "No inventory records", 400
    xlsx_data = inventory_obj.to_excel()
    filename = f"processing_inventory_{date.today().isoformat()}.xlsx"
    return Response(
        xlsx_data,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


@app.route("/export_risk_pdf", methods=["POST"])
def export_risk_pdf():
    """Export risk assessment report as PDF."""
    import json
    from flask import Response
    
    try:
        # Validate and parse input data with size limits
        results_json = request.form.get("results_data", "[]")
        if len(results_json) > 1024 * 1024:  # 1MB limit
            return "Export data too large", 400
            
        results_data = json.loads(results_json)
        summary_data = json.loads(request.form.get("summary_data", "{}"))
        dataset_name = request.form.get("dataset_name", "Unknown Dataset")
        df_rows = int(request.form.get("df_rows", "0"))
        classification_method = request.form.get("classification_method", "Rule-based")
        
        pdf_data = export_risk_assessment_pdf(
            classification_results=results_data,
            risk_summary=summary_data,
            dataset_name=dataset_name,
            total_rows=df_rows,
            method=classification_method
        )
        
        filename = f"risk_assessment_report_{date.today().isoformat()}.pdf"
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except json.JSONDecodeError:
        return "Invalid data format", 400
    except ValueError as e:
        return f"Invalid input: {str(e)}", 400
    except Exception as e:
        return f"Error generating PDF report. Please try again or contact support.", 500


@app.route("/export_risk_excel", methods=["POST"])
def export_risk_excel():
    """Export risk assessment report as Excel."""
    import json
    from flask import Response
    
    try:
        # Validate and parse input data with size limits
        results_json = request.form.get("results_data", "[]")
        if len(results_json) > 1024 * 1024:  # 1MB limit
            return "Export data too large", 400
            
        results_data = json.loads(results_json)
        summary_data = json.loads(request.form.get("summary_data", "{}"))
        dataset_name = request.form.get("dataset_name", "Unknown Dataset")
        df_rows = int(request.form.get("df_rows", "0"))
        classification_method = request.form.get("classification_method", "Rule-based")
        
        excel_data = export_combined_excel_report(
            classification_results=results_data,
            risk_summary=summary_data,
            dataset_name=dataset_name,
            total_rows=df_rows,
            method=classification_method
        )
        
        filename = f"risk_assessment_report_{date.today().isoformat()}.xlsx"
        return Response(
            excel_data,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except json.JSONDecodeError:
        return "Invalid data format", 400
    except ValueError as e:
        return f"Invalid input: {str(e)}", 400
    except Exception as e:
        return f"Error generating Excel report. Please try again or contact support.", 500


@app.route("/export_compliance_pdf", methods=["POST"])
def export_compliance_pdf():
    """Export compliance audit report as PDF."""
    import json
    from flask import Response
    
    try:
        # Validate input data
        responses_json = request.form.get("responses_data", "{}")
        if len(responses_json) > 100 * 1024:  # 100KB limit for compliance data
            return "Export data too large", 400
            
        responses_data = json.loads(responses_json)
        score = int(request.form.get("score", "0"))
        max_score = int(request.form.get("max_score", "0"))
        recommendations_data = json.loads(request.form.get("recommendations_data", "[]"))
        
        pdf_data = export_compliance_audit_pdf(
            responses=responses_data,
            checklist=CHECKLIST,
            score=score,
            max_score=max_score,
            recommendations=recommendations_data,
            organization="Your Organization"
        )
        
        filename = f"compliance_audit_report_{date.today().isoformat()}.pdf"
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except json.JSONDecodeError:
        return "Invalid data format", 400
    except ValueError as e:
        return f"Invalid input: {str(e)}", 400
    except Exception as e:
        return f"Error generating compliance report. Please try again or contact support.", 500


if __name__ == "__main__":
    # Run on port 8000 for backend interface, bind to all interfaces
    app.run(host="0.0.0.0", port=8000, debug=True)
