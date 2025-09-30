"""
UI Helper functions for session management and progress tracking

This module provides UI components and utilities for displaying progress,
session status, and handling session operations in both Streamlit and Flask frontends.
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime
import streamlit as st
from modules.session_manager import SessionData, ModuleProgress

def display_progress_bar_streamlit(session: SessionData) -> None:
    """Display progress bars for all modules in Streamlit"""
    st.subheader("📊 Progress Tracking")
    
    # Overall progress
    overall_progress = session.get_overall_progress()
    st.metric("Overall Progress", f"{overall_progress:.1f}%")
    st.progress(overall_progress / 100.0)
    
    # Module-specific progress
    col1, col2, col3 = st.columns(3)
    
    modules = [
        ("risk_assessment", "🔍 Risk Assessment", col1),
        ("policy_generator", "📄 Policy Generator", col2), 
        ("compliance_checklist", "✅ Compliance Checklist", col3)
    ]
    
    for module_key, module_name, col in modules:
        with col:
            progress = session.progress.get(module_key)
            if progress:
                status_icon = "✅" if progress.completed else "🔄"
                st.markdown(f"**{status_icon} {module_name.split(' ', 1)[1]}**")
                st.progress(progress.completion_percentage / 100.0)
                st.caption(f"{progress.completion_percentage:.1f}%")
                
                if progress.completed and progress.completion_date:
                    completion_date = datetime.fromisoformat(progress.completion_date)
                    st.caption(f"Completed: {completion_date.strftime('%Y-%m-%d %H:%M')}")
            else:
                st.markdown(f"**⭕ {module_name.split(' ', 1)[1]}**")
                st.progress(0.0)
                st.caption("Not started")


def display_session_info_streamlit(session: SessionData) -> None:
    """Display session information in Streamlit sidebar"""
    with st.sidebar:
        st.markdown("---")
        st.subheader("🔐 Session Info")
        
        # Session ID (truncated for display)
        session_id_short = session.session_id[:8] + "..."
        st.caption(f"Session: {session_id_short}")
        
        # Session created time
        created = datetime.fromisoformat(session.created_at)
        st.caption(f"Created: {created.strftime('%Y-%m-%d %H:%M')}")
        
        # Last accessed time
        last_accessed = datetime.fromisoformat(session.last_accessed)
        st.caption(f"Last Active: {last_accessed.strftime('%Y-%m-%d %H:%M')}")
        
        # Progress summary
        completed_modules = session.get_completed_modules()
        total_modules = len(session.progress)
        st.caption(f"Modules Complete: {len(completed_modules)}/{total_modules}")
        
        # Session actions
        if st.button("📤 Export Session", help="Export your progress to a file"):
            return "export"
        
        if st.button("🗑️ Clear Session", help="Start over with a new session"):
            return "clear"
    
    return None


def create_session_export_streamlit(session: SessionData, session_manager) -> None:
    """Handle session export in Streamlit"""
    try:
        export_data = session_manager.export_session(session)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"privacy_guardian_session_{timestamp}.json"
        
        st.download_button(
            label="💾 Download Session Data",
            data=export_data,
            file_name=filename,
            mime="application/json",
            help="Save your session to restore it later"
        )
        
        st.success("Session exported successfully! Save the file to restore your progress later.")
        
    except Exception as e:
        st.error(f"Failed to export session: {str(e)}")


def handle_session_import_streamlit(session_manager, uploaded_file) -> Optional[SessionData]:
    """Handle session import in Streamlit"""
    if uploaded_file is not None:
        try:
            # Read the uploaded file
            import_data = uploaded_file.read().decode('utf-8')
            
            # Import session
            imported_session = session_manager.import_session(import_data, frontend_type="streamlit")
            
            if imported_session:
                st.success("Session imported successfully! Your progress has been restored.")
                return imported_session
            else:
                st.error("Failed to import session. Please check the file format.")
                return None
                
        except Exception as e:
            st.error(f"Error importing session: {str(e)}")
            return None
    
    return None


def get_progress_indicators_flask(session: SessionData) -> Dict[str, Dict[str, any]]:
    """Get progress data formatted for Flask templates"""
    progress_data = {}
    
    for module_key, progress in session.progress.items():
        # Friendly names for module keys
        module_names = {
            "risk_assessment": "Risk Assessment",
            "policy_generator": "Policy Generator",
            "compliance_checklist": "Compliance Checklist",
            "enhanced_risk_scoring": "Enhanced Risk Scoring",
            "rrosh_decision": "RROSH Decision Wizard",
            "breach_record_book": "Breach Record Book",
            "dsar_factory": "DSAR Dossier Factory",
            "cross_border_assessment": "Cross‑Border Transfer",
            "quebec_pack": "Quebec Law 25 Pack",
            "processing_inventory": "Processing Inventory",
        }
        progress_data[module_key] = {
            "name": module_names.get(module_key, module_key.replace("_", " ").title()),
            "completed": progress.completed,
            "percentage": progress.completion_percentage,
            "status_icon": "✅" if progress.completed else ("🔄" if progress.completion_percentage > 0 else "⭕"),
            "completion_date": progress.completion_date,
            "last_updated": progress.last_updated
        }
    
    # Add overall progress
    progress_data["overall"] = {
        "percentage": session.get_overall_progress(),
        "completed_count": len(session.get_completed_modules()),
        "total_count": len(session.progress)
    }
    
    return progress_data


def update_module_progress(session: SessionData, module_name: str, percentage: float, session_manager) -> None:
    """Update progress for a specific module"""
    if module_name in session.progress:
        session.progress[module_name].update_progress(percentage)
        session_manager.save_session(session)


def mark_module_completed(session: SessionData, module_name: str, session_manager) -> None:
    """Mark a module as completed"""
    if module_name in session.progress:
        session.progress[module_name].mark_completed()
        session_manager.save_session(session)


def validate_session_data(session: SessionData) -> List[str]:
    """Validate session data and return list of issues"""
    issues = []
    
    # Validate basic session structure
    if not session.session_id:
        issues.append("Missing session ID")
    
    if not session.created_at:
        issues.append("Missing creation timestamp")
    
    # Validate module data
    if session.risk_assessment:
        ra = session.risk_assessment
        if ra.classification_results and not isinstance(ra.classification_results, list):
            issues.append("Invalid risk assessment results format")
    
    if session.policy_generator:
        pg = session.policy_generator
        if pg.company_name and len(pg.company_name) > 200:
            issues.append("Company name too long")
        if pg.contact_email and "@" not in pg.contact_email:
            issues.append("Invalid email format")
    
    if session.compliance_checklist:
        cc = session.compliance_checklist
        if cc.responses and not isinstance(cc.responses, dict):
            issues.append("Invalid compliance responses format")
    
    return issues


def get_session_summary(session: SessionData) -> Dict[str, any]:
    """Get a summary of session data for display"""
    return {
        "session_id": session.session_id[:8] + "...",
        "created_at": session.created_at,
        "last_accessed": session.last_accessed,
        "frontend_type": session.frontend_type,
        "overall_progress": session.get_overall_progress(),
        "completed_modules": session.get_completed_modules(),
        "total_modules": len(session.progress),
        "has_risk_data": bool(session.risk_assessment and session.risk_assessment.classification_results),
        "has_policy_data": bool(session.policy_generator and session.policy_generator.generated_policy),
        "has_compliance_data": bool(session.compliance_checklist and session.compliance_checklist.responses),
        "expires_in_hours": session.session_timeout_hours
    }


def format_session_for_display(session: SessionData) -> Dict[str, str]:
    """Format session data for human-readable display"""
    created = datetime.fromisoformat(session.created_at)
    last_accessed = datetime.fromisoformat(session.last_accessed)
    
    formatted = {
        "Session ID": session.session_id[:16] + "...",
        "Created": created.strftime("%Y-%m-%d at %H:%M"),
        "Last Active": last_accessed.strftime("%Y-%m-%d at %H:%M"),
        "Frontend": session.frontend_type.title(),
        "Overall Progress": f"{session.get_overall_progress():.1f}%",
        "Completed Modules": f"{len(session.get_completed_modules())}/{len(session.progress)}"
    }
    
    # Add module-specific info
    if session.risk_assessment and session.risk_assessment.dataset_name:
        formatted["Risk Assessment Dataset"] = session.risk_assessment.dataset_name
    
    if session.policy_generator and session.policy_generator.company_name:
        formatted["Policy Company"] = session.policy_generator.company_name
    
    if session.compliance_checklist and session.compliance_checklist.score > 0:
        formatted["Compliance Score"] = f"{session.compliance_checklist.score}/{session.compliance_checklist.max_score}"
    
    return formatted