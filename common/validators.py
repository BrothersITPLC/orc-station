"""
Security Input Validators

Centralized validation utilities to detect and prevent:
- XSS (Cross-Site Scripting) attacks (including encoded and obfuscated variants)
- SQL Injection attacks
- Command Injection attacks
- Buffer overflow attempts

Used by InputValidationMiddleware to validate all incoming requests.
"""

import re
import html
import urllib.parse
from django.core.exceptions import ValidationError


def normalize_for_detection(value):
    """
    Normalize input by decoding all common encoding schemes.
    This prevents attackers from bypassing detection using encoding.
    
    Args:
        value (str): Input value to normalize
        
    Returns:
        str: Normalized value with all encodings decoded
    """
    if not isinstance(value, str):
        return value
    
    original = value
    iterations = 0
    max_iterations = 5  # Prevent infinite loops
    
    while iterations < max_iterations:
        # Decode HTML entities
        decoded = html.unescape(value)
        
        # Decode URL encoding
        try:
            decoded = urllib.parse.unquote(decoded)
            decoded = urllib.parse.unquote_plus(decoded)
        except Exception:
            pass
        
        # Decode Unicode escape sequences (\u003c -> <)
        try:
            decoded = decoded.encode('utf-8').decode('unicode_escape')
        except Exception:
            pass
        
        # If no change occurred, we're done
        if decoded == value:
            break
            
        value = decoded
        iterations += 1
    
    # Convert to lowercase for case-insensitive matching
    return value.lower()


# Enhanced XSS Detection Patterns
XSS_PATTERNS = [
    # Script tags (complete and partial)
    r'<\s*script[^>]*>',
    r'</\s*script\s*>',
    r'<\s*scrip[t]?',  # Partial: <scrip, <scri, <scr
    r'<\s*scri[p]?',
    r'<\s*scr[i]?',
    r'<\s*sc[r]?',
    
    # JavaScript protocol
    r'javascript\s*:',
    r'java\s*script\s*:',
    r'j\s*a\s*v\s*a\s*s\s*c\s*r\s*i\s*p\s*t',  # Spaced out
    
    # Event handlers (all variants)
    r'on\s*\w+\s*=',  # onclick, onerror, onload, etc.
    r'on[a-z]+\s*=',
    
    # Iframe tags
    r'<\s*iframe',
    r'<\s*ifram[e]?',
    r'<\s*ifra[m]?',
    
    # Object and Embed tags
    r'<\s*object',
    r'<\s*objec[t]?',
    r'<\s*embed',
    r'<\s*embe[d]?',
    
    # SVG with scripts
    r'<\s*svg',
    r'<\s*sv[g]?',
    
    # Image with event handlers
    r'<\s*img[^>]*on\w+',
    
    # Link with javascript
    r'<\s*link[^>]*href[^>]*javascript',
    r'<\s*a[^>]*href[^>]*javascript',
    
    # Data URIs
    r'data\s*:\s*text\s*/\s*html',
    r'data\s*:\s*image\s*/\s*svg',
    r'data\s*:\s*application\s*/\s*x',
    
    # VBScript
    r'vbscript\s*:',
    
    # Style injection
    r'<\s*style',
    r'<\s*styl[e]?',
    r'expression\s*\(',
    r'@import',
    r'-moz-binding',
    
    # Meta refresh
    r'<\s*meta[^>]*http-equiv',
    
    # Base tag
    r'<\s*base',
    
    # Form with action
    r'<\s*form[^>]*action',
    
    # Common XSS patterns
    r'alert\s*\(',
    r'confirm\s*\(',
    r'prompt\s*\(',
    r'eval\s*\(',
    r'settimeout',
    r'setinterval',
]

# SQL Injection Detection Patterns (enhanced)
SQL_PATTERNS = [
    r"('\s*(or|and)\s*'?\d+'?\s*[=<>]+\s*'?\d+'?)",  # OR 1=1, AND 1=1
    r"('\s*union\s+select)",
    r"('\s*union\s+all\s+select)",
    r'(--|#|\/\*|\*\/)',  # SQL comments
    r"('\s*drop\s+(table|database))",
    r"('\s*delete\s+from)",
    r"('\s*insert\s+into)",
    r"('\s*update\s+\w+\s+set)",
    r"('\s*(exec|execute))",
    r';\s*(drop|delete|update|insert|create|alter)',
    r'(0x[0-9a-fA-F]+)',  # Hex encoding
    r"('\s*(and|or)\s+\w+\s*[=<>])",
    r'xp_cmdshell',  # SQL Server command execution
    r'benchmark\s*\(',  # MySQL timing attack
    r'sleep\s*\(',  # Time-based SQL injection
    r'waitfor\s+delay',  # SQL Server timing
    r"('\s*having\s+)",
    r"('\s*group\s+by\s+)",
    r'into\s+(outfile|dumpfile)',  # File writing
]

# Command Injection Detection Patterns
COMMAND_PATTERNS = [
    r'[;&|`$]',  # Shell metacharacters
    r'\$\(',  # Command substitution $()
    r'`[^`]*`',  # Backtick command substitution
    r'>\s*/dev/',  # File redirection to devices
    r'\.\./|\.\.',  # Path traversal
    r'%0a|%0d|%00',  # URL-encoded newlines and null bytes
    r'\n|\r',  # Actual newlines
    r'curl\s+',
    r'wget\s+',
    r'nc\s+',  # netcat
    r'bash\s+',
    r'sh\s+',
    r'/bin/',
    r'/etc/',
    r'passwd',
    r'shadow',
]

# Compile patterns for performance
XSS_REGEX = re.compile('|'.join(XSS_PATTERNS), re.IGNORECASE | re.DOTALL)
SQL_REGEX = re.compile('|'.join(SQL_PATTERNS), re.IGNORECASE)
COMMAND_REGEX = re.compile('|'.join(COMMAND_PATTERNS), re.IGNORECASE)


def contains_partial_tags(value):
    """
    Detect partial/incomplete HTML tags that might be attack fragments.
    
    Examples: <scrip, <scri, <ifram, etc.
    """
    if not isinstance(value, str):
        return False
    
    dangerous_partial_tags = [
        'scrip', 'scri', 'scr', 'sc',  # <script> fragments
        'ifram', 'ifra', 'ifr',  # <iframe> fragments
        'objec', 'obje', 'obj',  # <object> fragments
        'embe', 'emb',  # <embed> fragments
        'styl', 'sty',  # <style> fragments
    ]
    
    normalized = normalize_for_detection(value)
    
    for tag in dangerous_partial_tags:
        if f'<{tag}' in normalized or f'<{tag}>' in normalized:
            return True
    
    return False


def contains_xss(value):
    """
    Check if value contains XSS attack patterns (including encoded/obfuscated).
    
    Args:
        value (str): Input value to check
        
    Returns:
        bool: True if XSS pattern detected, False otherwise
    """
    if not isinstance(value, str):
        return False
    
    # Check original value
    if XSS_REGEX.search(value):
        return True
    
    # Check normalized (decoded) value
    normalized = normalize_for_detection(value)
    if XSS_REGEX.search(normalized):
        return True
    
    # Check for partial tags
    if contains_partial_tags(value):
        return True
    
    return False


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
    
    # Check original
    if SQL_REGEX.search(value):
        return True
    
    # Check normalized
    normalized = normalize_for_detection(value)
    if SQL_REGEX.search(normalized):
        return True
    
    return False


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
    
    # Check original
    if COMMAND_REGEX.search(value):
        return True
    
    # Check normalized
    normalized = normalize_for_detection(value)
    if COMMAND_REGEX.search(normalized):
        return True
    
    return False


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
    
    # Remove all HTML tags
    value = re.sub(r'<[^>]+>', '', value)
    
    # Remove script-like patterns
    value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
    value = re.sub(r'on\w+\s*=', '', value, flags=re.IGNORECASE)
    
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


def validate_alphanumeric(value, allow_spaces=True):
    """
    Validate that value contains only alphanumeric characters.
    
    Args:
        value (str): Value to validate
        allow_spaces (bool): Whether to allow spaces
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(value, str):
        return True
    
    if allow_spaces:
        pattern = r'^[a-zA-Z0-9\s]+$'
    else:
        pattern = r'^[a-zA-Z0-9]+$'
    
    return bool(re.match(pattern, value))


def validate_field_characters(value, field_name):
    """
    Validate field based on its type/name.
    Enforces character restrictions per field.
    
    Args:
        value (str): Value to validate
        field_name (str): Field name to determine validation rules
        
    Raises:
        ValidationError: If field contains invalid characters
    """
    if not isinstance(value, str) or not value:
        return
    
    # Name fields: only alphanumeric + spaces
    name_fields = ['first_name', 'last_name', 'name', 'username', 'full_name']
    if field_name in name_fields:
        if not validate_alphanumeric(value, allow_spaces=True):
            raise ValidationError(
                f"{field_name} can only contain letters, numbers, and spaces. "
                f"Special characters like ( ) < > are not allowed."
            )
    
    # Email: must match email pattern
    if field_name == 'email':
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise ValidationError(f"Invalid email format")
    
    # Phone: only numbers, spaces, +, -, ()
    if field_name in ['phone_number', 'phone']:
        phone_pattern = r'^[+\d\s\-()]+$'
        if not re.match(phone_pattern, value):
            raise ValidationError(
                f"Phone number can only contain numbers and these characters: + - ( ) space"
            )
    
    # Alphanumeric only fields (no special characters at all)
    alphanumeric_only = ['tin_number', 'license_number', 'plate_number', 'kebele']
    if field_name in alphanumeric_only:
        if not validate_alphanumeric(value, allow_spaces=False):
            raise ValidationError(
                f"{field_name} can only contain letters and numbers. No special characters allowed."
            )


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
    
    # First: Check field-specific character restrictions
    validate_field_characters(value, field_name)
    
    # Second: Check for security violations
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
