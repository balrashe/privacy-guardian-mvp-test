"""
Machine Learning Risk Classification module for Privacy Guardian.

Enhances the rule-based risk assessment with ML models for improved accuracy
in identifying sensitive data patterns and data types.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Any, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')


class MLRiskClassifier:
    """Machine learning-based risk classifier for sensitive data detection."""
    
    def __init__(self):
        self.column_name_vectorizer = TfidfVectorizer(
            max_features=100, 
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.data_pattern_vectorizer = TfidfVectorizer(
            max_features=50,
            analyzer='char_wb',
            ngram_range=(2, 4)
        )
        self.column_classifier = RandomForestClassifier(
            n_estimators=50, 
            random_state=42, 
            max_depth=10
        )
        self.pattern_classifier = LogisticRegression(
            random_state=42, 
            max_iter=500
        )
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        
    def _generate_training_data(self) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Generate synthetic training data for the ML models."""
        
        # Column names with their risk levels
        column_names = [
            # High risk columns
            'ssn', 'social_security_number', 'social_insurance_number', 'sin',
            'credit_card_number', 'creditcard', 'cc_num', 'card_number',
            'passport_number', 'passport_id', 'drivers_license', 'license_number',
            'medical_record_number', 'mrn', 'patient_id', 'health_id',
            'bank_account', 'iban', 'routing_number', 'account_number',
            'insurance_policy', 'policy_number', 'diagnosis_code',
            
            # Medium risk columns  
            'email', 'email_address', 'phone_number', 'phone', 'mobile',
            'date_of_birth', 'dob', 'birth_date', 'birthdate',
            'address', 'street_address', 'home_address', 'mailing_address',
            'postal_code', 'zip_code', 'city', 'state', 'province',
            'ip_address', 'ip', 'location', 'latitude', 'longitude',
            'first_name', 'last_name', 'full_name', 'name',
            
            # Low risk columns
            'id', 'customer_id', 'order_id', 'product_id', 'item_id',
            'quantity', 'price', 'amount', 'total', 'subtotal',
            'category', 'type', 'status', 'description', 'notes',
            'created_date', 'updated_date', 'modified_date',
            'department', 'division', 'company', 'organization'
        ]
        
        column_labels = (
            ['High'] * 13 + 
            ['Medium'] * 15 + 
            ['Low'] * 15
        )
        
        # Data patterns with their risk levels
        data_patterns = [
            # High risk patterns
            '123-45-6789', '123456789', '4532-1234-5678-9012', '4532123456789012',
            'P1234567', 'DL12345678', 'MRN-123456', 'POL-987654321',
            '12345678901234567890', 'ACC-123456789',
            
            # Medium risk patterns
            'john.doe@example.com', 'user@domain.com', '+1-555-123-4567',
            '(555) 123-4567', '1990-01-01', '01/01/1990', '123 Main St',
            'M5H 2N2', '10001', '192.168.1.1', '40.7128,-74.0060',
            'John', 'Smith', 'John Smith',
            
            # Low risk patterns
            'CUST001', 'ORD-12345', 'PROD-001', 'IT001',
            '100', '29.99', '1234.56', 'Electronics', 'Active',
            '2023-01-01 10:00:00', 'Engineering', 'Acme Corp'
        ]
        
        pattern_labels = (
            ['High'] * 10 + 
            ['Medium'] * 13 + 
            ['Low'] * 11
        )
        
        return column_names, column_labels, data_patterns, pattern_labels
    
    def train(self) -> bool:
        """Train the ML models with synthetic training data."""
        try:
            column_names, column_labels, data_patterns, pattern_labels = self._generate_training_data()
            
            # Train column name classifier
            column_features = self.column_name_vectorizer.fit_transform(column_names)
            column_labels_encoded = self.label_encoder.fit_transform(column_labels)
            self.column_classifier.fit(column_features, column_labels_encoded)
            
            # Train data pattern classifier
            pattern_features = self.data_pattern_vectorizer.fit_transform(data_patterns)
            pattern_labels_encoded = self.label_encoder.transform(pattern_labels)
            self.pattern_classifier.fit(pattern_features, pattern_labels_encoded)
            
            self.is_trained = True
            return True
            
        except Exception as e:
            print(f"Training error: {e}")
            return False
    
    def predict_column_risk(self, column_name: str) -> Tuple[str, float]:
        """Predict risk level for a column name."""
        if not self.is_trained:
            self.train()
            
        try:
            # Vectorize column name
            features = self.column_name_vectorizer.transform([column_name.lower()])
            
            # Get prediction and probability
            prediction = self.column_classifier.predict(features)[0]
            probabilities = self.column_classifier.predict_proba(features)[0]
            confidence = max(probabilities)
            
            # Decode prediction
            risk_level = self.label_encoder.inverse_transform([prediction])[0]
            
            return risk_level, confidence
            
        except Exception:
            return "Low", 0.1
    
    def predict_data_risk(self, data_sample: List[str]) -> Tuple[str, float]:
        """Predict risk level based on data patterns."""
        if not self.is_trained:
            self.train()
            
        if not data_sample:
            return "Low", 0.1
            
        try:
            # Take sample of data for pattern analysis
            sample_text = ' '.join(str(x) for x in data_sample[:50])
            
            # Vectorize data patterns
            features = self.data_pattern_vectorizer.transform([sample_text])
            
            # Get prediction and probability
            prediction = self.pattern_classifier.predict(features)[0]
            probabilities = self.pattern_classifier.predict_proba(features)[0]
            confidence = max(probabilities)
            
            # Decode prediction
            risk_level = self.label_encoder.inverse_transform([prediction])[0]
            
            return risk_level, confidence
            
        except Exception:
            return "Low", 0.1
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance for column name classification."""
        if not self.is_trained:
            return {}
            
        try:
            feature_names = self.column_name_vectorizer.get_feature_names_out()
            importance_scores = self.column_classifier.feature_importances_
            
            # Get top 10 most important features
            top_indices = np.argsort(importance_scores)[-10:]
            top_features = {
                feature_names[i]: importance_scores[i] 
                for i in top_indices
            }
            
            return top_features
            
        except Exception:
            return {}


# Global classifier instance
_ml_classifier = MLRiskClassifier()


def classify_column_ml(column_name: str, data_series: pd.Series) -> Dict[str, Any]:
    """
    Classify a column using machine learning approach.
    
    Args:
        column_name: Name of the column
        data_series: Pandas Series containing the data
        
    Returns:
        Dictionary with classification results
    """
    # Get sample data for pattern analysis
    sample_data = data_series.dropna().astype(str).head(100).tolist()
    
    # Get ML predictions
    name_risk, name_confidence = _ml_classifier.predict_column_risk(column_name)
    data_risk, data_confidence = _ml_classifier.predict_data_risk(sample_data)
    
    # Combine predictions (take higher risk level)
    risk_hierarchy = {"Low": 0, "Medium": 1, "High": 2}
    
    if risk_hierarchy[name_risk] >= risk_hierarchy[data_risk]:
        final_risk = name_risk
        final_confidence = name_confidence
        primary_factor = "column_name"
    else:
        final_risk = data_risk
        final_confidence = data_confidence
        primary_factor = "data_pattern"
    
    return {
        "column": column_name,
        "ml_name_risk": name_risk,
        "ml_name_confidence": round(name_confidence, 3),
        "ml_data_risk": data_risk,
        "ml_data_confidence": round(data_confidence, 3),
        "ml_final_risk": final_risk,
        "ml_final_confidence": round(final_confidence, 3),
        "ml_primary_factor": primary_factor
    }


def classify_dataframe_ml(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Classify all columns in a DataFrame using ML approach.
    
    Args:
        df: Pandas DataFrame to classify
        
    Returns:
        List of classification results for each column
    """
    results = []
    for column in df.columns:
        result = classify_column_ml(column, df[column])
        results.append(result)
    
    return results


def get_ml_model_info() -> Dict[str, Any]:
    """Get information about the ML models."""
    return {
        "is_trained": _ml_classifier.is_trained,
        "feature_importance": _ml_classifier.get_feature_importance(),
        "models": {
            "column_classifier": "Random Forest (50 estimators)",
            "pattern_classifier": "Logistic Regression",
            "vectorizers": {
                "column_name": "TF-IDF (1-2 grams, 100 features)",
                "data_pattern": "TF-IDF (2-4 char grams, 50 features)"
            }
        }
    }


def hybrid_classify_series(name: str, series: pd.Series) -> Dict[str, Any]:
    """
    Hybrid classification combining rule-based and ML approaches.
    
    Args:
        name: Column name
        series: Pandas Series with data
        
    Returns:
        Combined classification results
    """
    from .risk_assessment import classify_series
    
    # Get rule-based classification
    rule_result = classify_series(name, series)
    
    # Get ML classification
    ml_result = classify_column_ml(name, series)
    
    # Combine results - take the higher risk assessment
    risk_hierarchy = {"Low": 0, "Medium": 1, "High": 2}
    
    rule_risk_score = risk_hierarchy[rule_result["final_risk"]]
    ml_risk_score = risk_hierarchy[ml_result["ml_final_risk"]]
    
    if ml_risk_score > rule_risk_score:
        final_risk = ml_result["ml_final_risk"]
        method = "ml_enhanced"
    elif rule_risk_score > ml_risk_score:
        final_risk = rule_result["final_risk"]
        method = "rule_based"
    else:
        final_risk = rule_result["final_risk"]
        method = "consensus"
    
    # Combine results
    combined_result = {
        **rule_result,
        **ml_result,
        "hybrid_final_risk": final_risk,
        "hybrid_method": method,
        "confidence_score": ml_result["ml_final_confidence"]
    }
    
    return combined_result


def classify_dataframe_hybrid(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Classify DataFrame using hybrid rule-based + ML approach.
    
    Args:
        df: Pandas DataFrame to classify
        
    Returns:
        List of hybrid classification results
    """
    results = []
    for column in df.columns:
        result = hybrid_classify_series(column, df[column])
        results.append(result)
    
    return results