"""
Security Input Validators

Centralized validation utilities to detect and prevent:
- XSS (Cross-Site Scripting) attacks
- SQL Injection attacks
- Command Injection attacks
- Buffer overflow attempts

Used by InputValidationMiddleware to validate all incoming requests.
"""

import re
import html
from django.core.exceptions import ValidationError


# XSS Detection Patterns
XSS_PATTERNS = [
    r'<script[^>]*>.*?</script>',      # Script tags
    r'javascript:',                     # JavaScript protocol
    r'on\w+\s*=',                       # Event handlers (onclick, onerror, etc.)
    r'<iframe',                         # Iframes
    r'<object',                         # Object tags
    r'<embed',                          # Embed tags
    r'<svg[^>]*>.*?</svg>',            # SVG with potential scripts
    r'<img[^>]+onerror',                # Image with onerror
    r'data:text/html',                  # Data URI with HTML
    r'vbscript:',                       # VBScript protocol
    r'<link[^>]+href[^>]*javascript:',  # Link with JavaScript
]

# SQL Injection Detection Patterns
SQL_PATTERNS = [
    r"('\s*(or|OR)\s*'?\d+'?\s*=\s*'?\d+'?)",      # OR 1=1
    r"('\s*(union|UNION)\s+(select|SELECT))",       # UNION SELECT
    r'(--|#|\/\*|\*\/)',                            # SQL comments
    r"('\s*(drop|DROP)\s+(table|TABLE|database|DATABASE))",  # DROP TABLE/DATABASE
    r"('\s*(delete|DELETE)\s+(from|FROM))",         # DELETE FROM
    r"('\s*(insert|INSERT)\s+(into|INTO))",         # INSERT INTO
    r"('\s*(update|UPDATE)\s+\w+\s+(set|SET))",     # UPDATE SET
    r"('\s*(exec|EXEC|execute|EXECUTE))",           # EXEC/EXECUTE
    r';\s*(drop|DROP|delete|DELETE|update|UPDATE)', # Statement chaining
    r'(0x[0-9a-fA-F]+)',                            # Hex encoding
    r"('\s*(and|AND|or|OR)\s+\d+\s*=\s*\d+)",      # AND/OR conditions
]

# Command Injection Detection Patterns
COMMAND_PATTERNS = [
    r'[;&|`]',                  # Shell metacharacters
    r'\$\(',                    # Command substitution $()
    r'`.*?`',                   # Backtick command substitution
    r'>\s*/dev/',               # File redirection to devices
    r'\.\./|\.\.\\',            # Path traversal
    r'%0a|%0d',                 # URL-encoded newlines (command injection)
]

# Compile patterns for performance
XSS_REGEX = re.compile('|'.join(XSS_PATTERNS), re.IGNORECASE | re.DOTALL)
SQL_REGEX = re.compile('|'.join(SQL_PATTERNS), re.IGNORECASE)
COMMAND_REGEX = re.compile('|'.join(COMMAND_PATTERNS), re.IGNORECASE)


def contains_xss(value):
    """
    Check if value contains XSS attack patterns.
    
    Args:
        value (str): Input value to check
        
    Returns:
        bool: True if XSS pattern detected, False otherwise
    """
    if not isinstance(value, str):
        return False
    
    return bool(XSS_REGEX.search(value))


def contains_sql_injection(value):
    """
    Check if value contains SQL injection patterns.
    
    Args:
        value (str): Input value to check
        
    Returns:
        bool: True if SQL injection pattern detected, False otherwise
    """
    if not isinstance(value, str):
        return False
    
    return bool(SQL_REGEX.search(value))


def contains_command_injection(value):
    """
    Check if value contains command injection patterns.
    
    Args:
        value (str): Input value to check
        
    Returns:
        bool: True if command injection pattern detected, False otherwise
    """
    if not isinstance(value, str):
        return False
    
    return bool(COMMAND_REGEX.search(value))


def sanitize_string(value, max_length=255):
    """
    Sanitize string input by removing dangerous content and limiting length.
    
    Args:
        value (str): Input value to sanitize
        max_length (int): Maximum allowed length
        
    Returns:
        str: Sanitized string
        
    Raises:
        ValidationError: If value exceeds max length
    """
    if not isinstance(value, str):
        return value
    
    # Remove HTML tags (basic sanitization)
    value = re.sub(r'<[^>]+>', '', value)
    
    # Trim whitespace
    value = value.strip()
    
    # Check length
    if len(value) > max_length:
        raise ValidationError(
            f"Input exceeds maximum length of {max_length} characters. Provided: {len(value)}"
        )
    
    # HTML encode special characters
    value = html.escape(value)
    
    return value


def validate_field_length(value, max_length, field_name="field"):
    """
    Validate that field does not exceed maximum length.
    
    Args:
        value: Input value
        max_length (int): Maximum allowed length
        field_name (str): Name of the field for error message
        
    Raises:
        ValidationError: If value exceeds max length
    """
    if isinstance(value, str) and len(value) > max_length:
        raise ValidationError(
            f"Field '{field_name}' exceeds maximum length of {max_length} characters. "
            f"Provided: {len(value)}"
        )


def get_violation_type(value):
    """
    Determine the type of security violation in the value.
    
    Args:
        value (str): Input value to check
        
    Returns:
        str: Violation type ('XSS', 'SQL_INJECTION', 'COMMAND_INJECTION', or None)
    """
    if contains_xss(value):
        return 'XSS'
    elif contains_sql_injection(value):
        return 'SQL_INJECTION'
    elif contains_command_injection(value):
        return 'COMMAND_INJECTION'
    return None


def validate_input(value, field_name="field", max_length=255, strict_mode=True):
    """
    Comprehensive validation of input value.
    
    Args:
        value: Input value to validate
        field_name (str): Name of the field
        max_length (int): Maximum allowed length
        strict_mode (bool): If True, raise exception on violation; if False, sanitize
        
    Returns:
        Sanitized value (if strict_mode=False)
        
    Raises:
        ValidationError: If validation fails and strict_mode=True
    """
    if not isinstance(value, str):
        return value
    
    # Check for security violations
    violation = get_violation_type(value)
    
    if violation and strict_mode:
        if violation == 'XSS':
            raise ValidationError(
                f"Potentially dangerous content detected in field '{field_name}' (XSS pattern found)"
            )
        elif violation == 'SQL_INJECTION':
            raise ValidationError(
                f"Suspicious SQL pattern detected in field '{field_name}'"
            )
        elif violation == 'COMMAND_INJECTION':
            raise ValidationError(
                f"Suspicious command pattern detected in field '{field_name}'"
            )
    
    # Validate length
    validate_field_length(value, max_length, field_name)
    
    # Sanitize if not in strict mode
    if not strict_mode:
        return sanitize_string(value, max_length)
    
    return value
