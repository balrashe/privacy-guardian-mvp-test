"""
Session Management Module for Privacy Guardian

This module provides session management and progress tracking capabilities for both
Streamlit and Flask frontends. It includes:
- Session data persistence across modules
- Progress tracking with completion status
- Session export/import functionality
- Secure session handling with validation
- Session timeout and cleanup mechanisms
"""

from __future__ import annotations
import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import secrets


@dataclass
class ModuleProgress:
    """Progress tracking for individual modules"""
    completed: bool = False
    completion_date: Optional[str] = None
    completion_percentage: float = 0.0
    last_updated: Optional[str] = None
    
    def mark_completed(self):
        """Mark module as completed"""
        self.completed = True
        self.completion_date = datetime.now().isoformat()
        self.completion_percentage = 100.0
        self.last_updated = self.completion_date
    
    def update_progress(self, percentage: float):
        """Update progress percentage"""
        self.completion_percentage = min(100.0, max(0.0, percentage))
        self.last_updated = datetime.now().isoformat()
        if self.completion_percentage >= 100.0:
            self.mark_completed()


@dataclass
class RiskAssessmentData:
    """Data structure for Risk Assessment module"""
    dataset_name: Optional[str] = None
    classification_method: Optional[str] = None
    classification_results: Optional[List[Dict[str, Any]]] = None
    risk_summary: Optional[Dict[str, int]] = None
    total_rows: int = 0
    uploaded_file_hash: Optional[str] = None
    validation_result: Optional[Dict[str, Any]] = None


@dataclass
class PolicyGeneratorData:
    """Data structure for Policy Generator module"""
    company_name: str = ""
    contact_email: str = ""
    jurisdiction: str = "Canada (PIPEDA/CPPA/AIDA)"
    business_type: str = "general"
    template_style: str = "formal"
    include_ai: bool = True
    generated_policy: Optional[str] = None
    policy_date: Optional[str] = None


@dataclass
class ComplianceChecklistData:
    """Data structure for Compliance Checklist module"""
    responses: Optional[Dict[str, str]] = None
    score: int = 0
    max_score: int = 0
    percentage: float = 0.0
    recommendations: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.responses is None:
            self.responses = {}
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class SessionData:
    """Complete session data structure"""
    session_id: str
    created_at: str
    last_accessed: str
    user_agent: Optional[str] = None
    
    # Module data
    risk_assessment: RiskAssessmentData = None
    policy_generator: PolicyGeneratorData = None
    compliance_checklist: ComplianceChecklistData = None

    # Additional module data for new features
    # Breach Record Book to maintain breach log for 24 months
    breach_record_book: Any = None  # type: ignore
    # Processing Inventory to maintain processing activities
    processing_inventory: Any = None  # type: ignore
    
    # Progress tracking
    progress: Dict[str, ModuleProgress] = None
    
    # Session metadata
    frontend_type: str = "streamlit"  # "streamlit" or "flask"
    session_timeout_hours: int = 24
    
    def __post_init__(self):
        if self.risk_assessment is None:
            self.risk_assessment = RiskAssessmentData()
        if self.policy_generator is None:
            self.policy_generator = PolicyGeneratorData()
        if self.compliance_checklist is None:
            self.compliance_checklist = ComplianceChecklistData()
        if self.progress is None:
            # Initialize progress for all available modules. New modules are added here
            self.progress = {
                "risk_assessment": ModuleProgress(),
                "policy_generator": ModuleProgress(),
                "compliance_checklist": ModuleProgress(),
                # New modules introduced after the MVP
                "enhanced_risk_scoring": ModuleProgress(),
                "rrosh_decision": ModuleProgress(),
                "breach_record_book": ModuleProgress(),
                "dsar_factory": ModuleProgress(),
                "cross_border_assessment": ModuleProgress(),
                "quebec_pack": ModuleProgress(),
                "processing_inventory": ModuleProgress(),
            }

        # Lazy import new module classes to avoid circular dependencies
        try:
            from modules.breach_record import BreachRecordBook  # type: ignore
            if self.breach_record_book is None:
                self.breach_record_book = BreachRecordBook()
        except Exception:
            # If module import fails, leave attribute as None
            pass
        try:
            from modules.processing_inventory import ProcessingInventory  # type: ignore
            if self.processing_inventory is None:
                self.processing_inventory = ProcessingInventory()
        except Exception:
            pass
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        last_access = datetime.fromisoformat(self.last_accessed)
        expiry_time = last_access + timedelta(hours=self.session_timeout_hours)
        return datetime.now() > expiry_time
    
    def update_last_accessed(self):
        """Update last accessed timestamp"""
        self.last_accessed = datetime.now().isoformat()
    
    def get_overall_progress(self) -> float:
        """Calculate overall progress across all modules"""
        if not self.progress:
            return 0.0
        
        total_progress = sum(module.completion_percentage for module in self.progress.values())
        return total_progress / len(self.progress)
    
    def get_completed_modules(self) -> List[str]:
        """Get list of completed module names"""
        return [name for name, module in self.progress.items() if module.completed]


class SessionManager:
    """Session management class supporting both Streamlit and Flask"""
    
    def __init__(self, storage_dir: str = "sessions", max_sessions: int = 1000):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.max_sessions = max_sessions
        
        # Create .gitignore to prevent session files from being committed
        gitignore_path = self.storage_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("*\n!.gitignore\n")
    
    def _generate_session_id(self) -> str:
        """Generate a secure session ID"""
        return secrets.token_urlsafe(32)
    
    def _get_session_file_path(self, session_id: str) -> Path:
        """Get file path for session data"""
        return self.storage_dir / f"{session_id}.json"
    
    def _hash_data(self, data: str) -> str:
        """Create hash of data for integrity checking"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def create_session(self, frontend_type: str = "streamlit", user_agent: Optional[str] = None) -> SessionData:
        """Create a new session"""
        session_id = self._generate_session_id()
        now = datetime.now().isoformat()
        
        session = SessionData(
            session_id=session_id,
            created_at=now,
            last_accessed=now,
            user_agent=user_agent,
            frontend_type=frontend_type
        )
        
        self._save_session(session)
        self._cleanup_old_sessions()
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session by ID"""
        if not session_id:
            return None
            
        file_path = self._get_session_file_path(session_id)
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert dict data back to dataclass instances
            session_data = self._dict_to_session_data(data)
            
            # Check if session is expired
            if session_data.is_expired():
                self.delete_session(session_id)
                return None
            
            # Update last accessed time
            session_data.update_last_accessed()
            self._save_session(session_data)
            
            return session_data
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Delete corrupted session file
            file_path.unlink(missing_ok=True)
            return None
    
    def save_session(self, session: SessionData) -> bool:
        """Save session data"""
        session.update_last_accessed()
        return self._save_session(session)
    
    def _save_session(self, session: SessionData) -> bool:
        """Internal method to save session"""
        try:
            file_path = self._get_session_file_path(session.session_id)
            session_dict = self._session_data_to_dict(session)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_dict, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception:
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            file_path = self._get_session_file_path(session_id)
            file_path.unlink(missing_ok=True)
            return True
        except Exception:
            return False
    
    def export_session(self, session: SessionData) -> str:
        """Export session data as JSON string"""
        session_dict = self._session_data_to_dict(session)
        # Remove session-specific metadata for export
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "privacy_guardian_version": "1.0",
            "data": {
                "risk_assessment": session_dict.get("risk_assessment"),
                "policy_generator": session_dict.get("policy_generator"),
                "compliance_checklist": session_dict.get("compliance_checklist"),
                "progress": session_dict.get("progress")
            }
        }
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def import_session(self, json_data: str, frontend_type: str = "streamlit") -> Optional[SessionData]:
        """Import session data from JSON string"""
        try:
            import_data = json.loads(json_data)
            
            # Validate import data structure
            if "data" not in import_data:
                return None
            
            data = import_data["data"]
            
            # Create new session
            session = self.create_session(frontend_type=frontend_type)
            
            # Import data into new session
            if "risk_assessment" in data and data["risk_assessment"]:
                session.risk_assessment = self._dict_to_risk_assessment(data["risk_assessment"])
            
            if "policy_generator" in data and data["policy_generator"]:
                session.policy_generator = self._dict_to_policy_generator(data["policy_generator"])
            
            if "compliance_checklist" in data and data["compliance_checklist"]:
                session.compliance_checklist = self._dict_to_compliance_checklist(data["compliance_checklist"])
            
            if "progress" in data and data["progress"]:
                session.progress = {
                    name: self._dict_to_module_progress(progress_data)
                    for name, progress_data in data["progress"].items()
                }
            
            self.save_session(session)
            return session
            
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    def _cleanup_old_sessions(self):
        """Remove expired sessions and limit total sessions"""
        session_files = list(self.storage_dir.glob("*.json"))
        
        # Remove expired sessions
        for file_path in session_files[:]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                session_data = self._dict_to_session_data(data)
                if session_data.is_expired():
                    file_path.unlink()
                    session_files.remove(file_path)
            except Exception:
                # Remove corrupted files
                file_path.unlink(missing_ok=True)
                if file_path in session_files:
                    session_files.remove(file_path)
        
        # Limit total number of sessions
        if len(session_files) > self.max_sessions:
            # Sort by modification time and remove oldest
            session_files.sort(key=lambda p: p.stat().st_mtime)
            for file_path in session_files[:-self.max_sessions]:
                file_path.unlink(missing_ok=True)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about current sessions"""
        session_files = list(self.storage_dir.glob("*.json"))
        active_sessions = 0
        total_size = 0
        
        for file_path in session_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                session_data = self._dict_to_session_data(data)
                if not session_data.is_expired():
                    active_sessions += 1
                
                total_size += file_path.stat().st_size
            except Exception:
                continue
        
        return {
            "total_sessions": len(session_files),
            "active_sessions": active_sessions,
            "total_size_bytes": total_size,
            "storage_directory": str(self.storage_dir)
        }
    
    # Helper methods for data conversion
    def _session_data_to_dict(self, session: SessionData) -> Dict[str, Any]:
        """Convert SessionData to dictionary"""
        result = asdict(session)
        
        # Convert ModuleProgress objects to dicts
        if result.get("progress"):
            result["progress"] = {
                name: asdict(progress) for name, progress in result["progress"].items()
            }
        
        return result
    
    def _dict_to_session_data(self, data: Dict[str, Any]) -> SessionData:
        """Convert dictionary to SessionData"""
        # Handle progress data
        progress_data = data.get("progress", {})
        progress = {
            name: self._dict_to_module_progress(progress_dict)
            for name, progress_dict in progress_data.items()
        }
        
        return SessionData(
            session_id=data["session_id"],
            created_at=data["created_at"],
            last_accessed=data["last_accessed"],
            user_agent=data.get("user_agent"),
            risk_assessment=self._dict_to_risk_assessment(data.get("risk_assessment", {})),
            policy_generator=self._dict_to_policy_generator(data.get("policy_generator", {})),
            compliance_checklist=self._dict_to_compliance_checklist(data.get("compliance_checklist", {})),
            progress=progress,
            frontend_type=data.get("frontend_type", "streamlit"),
            session_timeout_hours=data.get("session_timeout_hours", 24)
        )
    
    def _dict_to_module_progress(self, data: Dict[str, Any]) -> ModuleProgress:
        """Convert dictionary to ModuleProgress"""
        return ModuleProgress(
            completed=data.get("completed", False),
            completion_date=data.get("completion_date"),
            completion_percentage=data.get("completion_percentage", 0.0),
            last_updated=data.get("last_updated")
        )
    
    def _dict_to_risk_assessment(self, data: Dict[str, Any]) -> RiskAssessmentData:
        """Convert dictionary to RiskAssessmentData"""
        return RiskAssessmentData(
            dataset_name=data.get("dataset_name"),
            classification_method=data.get("classification_method"),
            classification_results=data.get("classification_results"),
            risk_summary=data.get("risk_summary"),
            total_rows=data.get("total_rows", 0),
            uploaded_file_hash=data.get("uploaded_file_hash"),
            validation_result=data.get("validation_result")
        )
    
    def _dict_to_policy_generator(self, data: Dict[str, Any]) -> PolicyGeneratorData:
        """Convert dictionary to PolicyGeneratorData"""
        return PolicyGeneratorData(
            company_name=data.get("company_name", ""),
            contact_email=data.get("contact_email", ""),
            jurisdiction=data.get("jurisdiction", "Canada (PIPEDA/CPPA/AIDA)"),
            business_type=data.get("business_type", "general"),
            template_style=data.get("template_style", "formal"),
            include_ai=data.get("include_ai", True),
            generated_policy=data.get("generated_policy"),
            policy_date=data.get("policy_date")
        )
    
    def _dict_to_compliance_checklist(self, data: Dict[str, Any]) -> ComplianceChecklistData:
        """Convert dictionary to ComplianceChecklistData"""
        return ComplianceChecklistData(
            responses=data.get("responses", {}),
            score=data.get("score", 0),
            max_score=data.get("max_score", 0),
            percentage=data.get("percentage", 0.0),
            recommendations=data.get("recommendations", [])
        )


# Global session manager instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager