"""
CSV validation module for Privacy Guardian.

Provides comprehensive validation and error handling for CSV file uploads
with detailed feedback on data quality issues and recommendations.
"""
from __future__ import annotations
import pandas as pd
import io
from typing import Dict, List, Any, Optional, Tuple
import re


class CSVValidationResult:
    """Container for CSV validation results."""
    
    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.row_count = 0
        self.column_count = 0
        self.file_size_mb = 0.0
        self.encoding = 'utf-8'
        self.delimiter = ','


def validate_csv_file(file_content: Any, filename: str = "") -> Tuple[Optional[pd.DataFrame], CSVValidationResult]:
    """
    Comprehensive CSV validation with detailed error reporting.
    
    Args:
        file_content: File content (file-like object or string path)
        filename: Original filename for context
        
    Returns:
        Tuple of (DataFrame if valid, ValidationResult)
    """
    import os
    
    result = CSVValidationResult()
    
    try:
        # Handle different input types
        if hasattr(file_content, 'read'):
            # File-like object
            content = file_content.read()
            if hasattr(file_content, 'seek'):
                file_content.seek(0)  # Reset for pandas
        elif isinstance(file_content, str) and os.path.exists(file_content):
            # File path exists on disk - read the actual file
            with open(file_content, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            # Assume string content
            content = file_content
            
        # Calculate file size
        if isinstance(content, bytes):
            result.file_size_mb = len(content) / (1024 * 1024)
            content_str = content.decode('utf-8', errors='replace')
        else:
            result.file_size_mb = len(str(content).encode('utf-8')) / (1024 * 1024)
            content_str = str(content)
            
        # Check file size limits (10MB max)
        if result.file_size_mb > 10:
            result.errors.append(f"File size ({result.file_size_mb:.1f}MB) exceeds maximum allowed size of 10MB")
            result.is_valid = False
            return None, result
            
        # Check if file appears to be CSV
        if filename and not filename.lower().endswith('.csv'):
            result.warnings.append(f"File extension '{filename.split('.')[-1]}' is not .csv")
            
        # Detect delimiter
        sample_lines = content_str.split('\n')[:5]
        sample_text = '\n'.join(sample_lines)
        
        comma_count = sample_text.count(',')
        semicolon_count = sample_text.count(';')
        tab_count = sample_text.count('\t')
        
        if semicolon_count > comma_count and semicolon_count > tab_count:
            result.delimiter = ';'
            result.info.append("Detected semicolon (;) as delimiter")
        elif tab_count > comma_count:
            result.delimiter = '\t'
            result.info.append("Detected tab as delimiter")
        else:
            result.delimiter = ','
            
        # Try to read CSV with pandas
        try:
            if hasattr(file_content, 'seek'):
                file_content.seek(0)
                df = pd.read_csv(file_content, delimiter=result.delimiter, encoding='utf-8')
            elif isinstance(file_content, str) and os.path.exists(file_content):
                # Read directly from file path
                df = pd.read_csv(file_content, delimiter=result.delimiter, encoding='utf-8')
            else:
                df = pd.read_csv(io.StringIO(content_str), delimiter=result.delimiter)
                
        except UnicodeDecodeError:
            # Try different encodings
            encodings = ['latin-1', 'cp1252', 'iso-8859-1']
            df = None
            for encoding in encodings:
                try:
                    if hasattr(file_content, 'seek'):
                        file_content.seek(0)
                        df = pd.read_csv(file_content, delimiter=result.delimiter, encoding=encoding)
                    elif isinstance(file_content, str) and os.path.exists(file_content):
                        df = pd.read_csv(file_content, delimiter=result.delimiter, encoding=encoding)
                    else:
                        df = pd.read_csv(io.StringIO(content_str), delimiter=result.delimiter, encoding=encoding)
                    result.encoding = encoding
                    result.warnings.append(f"File encoding detected as {encoding} (not UTF-8)")
                    break
                except:
                    continue
                    
            if df is None:
                result.errors.append("Unable to decode file with common encodings (UTF-8, Latin-1, CP1252)")
                result.is_valid = False
                return None, result
                
        # Basic DataFrame validation
        result.row_count = len(df)
        result.column_count = len(df.columns)
        
        # Check for minimum requirements
        if result.row_count == 0:
            result.errors.append("CSV file contains no data rows")
            result.is_valid = False
            
        if result.column_count == 0:
            result.errors.append("CSV file contains no columns")
            result.is_valid = False
            
        if result.column_count == 1 and result.delimiter == ',':
            # Might be wrong delimiter detection
            result.warnings.append("Only one column detected - delimiter might be incorrect")
            
        # Check for duplicate column names
        duplicate_cols = df.columns[df.columns.duplicated()].tolist()
        if duplicate_cols:
            result.warnings.append(f"Duplicate column names found: {duplicate_cols}")
            
        # Check for unnamed/empty column names
        unnamed_cols = [col for col in df.columns if str(col).startswith('Unnamed:') or str(col).strip() == '']
        if unnamed_cols:
            result.warnings.append(f"Unnamed or empty column names: {len(unnamed_cols)} columns")
            
        # Data quality checks
        _validate_data_quality(df, result)
        
        # Size warnings
        if result.row_count > 10000:
            result.warnings.append(f"Large dataset ({result.row_count:,} rows) - processing may be slow")
            
        if result.column_count > 50:
            result.warnings.append(f"Many columns ({result.column_count}) detected")
            
        result.info.append(f"Successfully loaded {result.row_count:,} rows and {result.column_count} columns")
        
        return df, result
        
    except pd.errors.EmptyDataError:
        result.errors.append("CSV file is empty or contains no data")
        result.is_valid = False
        
    except pd.errors.ParserError as e:
        result.errors.append(f"CSV parsing error: {str(e)}")
        result.is_valid = False
        
    except Exception as e:
        result.errors.append(f"Unexpected error reading CSV: {str(e)}")
        result.is_valid = False
        
    return None, result


def _validate_data_quality(df: pd.DataFrame, result: CSVValidationResult) -> None:
    """Validate data quality and add warnings/info to result."""
    
    # Check for completely empty rows
    empty_rows = df.isnull().all(axis=1).sum()
    if empty_rows > 0:
        result.warnings.append(f"{empty_rows} completely empty rows found")
        
    # Check for completely empty columns
    empty_cols = df.isnull().all(axis=0).sum()
    if empty_cols > 0:
        result.warnings.append(f"{empty_cols} completely empty columns found")
        
    # Check missing data percentage by column
    missing_data = []
    for col in df.columns:
        missing_pct = (df[col].isnull().sum() / len(df)) * 100
        if missing_pct > 50:
            missing_data.append(f"{col} ({missing_pct:.1f}% missing)")
            
    if missing_data:
        result.warnings.append(f"Columns with >50% missing data: {', '.join(missing_data)}")
        
    # Check for potential PII in column names (for privacy context)
    pii_patterns = [
        r'.*\b(ssn|social.?security|sin)\b.*',
        r'.*\b(credit.?card|cc.?num|card.?number)\b.*',
        r'.*\b(passport|license|licence)\b.*',
        r'.*\b(medical|health|diagnosis)\b.*'
    ]
    
    potential_pii_cols = []
    for col in df.columns:
        col_lower = str(col).lower()
        for pattern in pii_patterns:
            if re.match(pattern, col_lower):
                potential_pii_cols.append(col)
                break
                
    if potential_pii_cols:
        result.info.append(f"Potential sensitive data columns detected: {', '.join(potential_pii_cols)}")
        
    # Check for consistent data types within columns
    inconsistent_cols = []
    for col in df.select_dtypes(include=['object']).columns:
        if len(df[col].dropna()) > 0:
            # Check if column has mixed numeric/text content
            sample_values = df[col].dropna().astype(str).head(100)
            numeric_count = sum(1 for val in sample_values if val.replace('.', '').replace('-', '').isdigit())
            if 0.1 < (numeric_count / len(sample_values)) < 0.9:
                inconsistent_cols.append(col)
                
    if inconsistent_cols:
        result.warnings.append(f"Columns with mixed data types: {', '.join(inconsistent_cols)}")


def format_validation_messages(result: CSVValidationResult) -> str:
    """Format validation messages for display."""
    messages = []
    
    if result.errors:
        messages.append("❌ **Errors:**")
        for error in result.errors:
            messages.append(f"  • {error}")
            
    if result.warnings:
        messages.append("⚠️ **Warnings:**")
        for warning in result.warnings:
            messages.append(f"  • {warning}")
            
    if result.info:
        messages.append("ℹ️ **Information:**")
        for info in result.info:
            messages.append(f"  • {info}")
            
    return "\n".join(messages)