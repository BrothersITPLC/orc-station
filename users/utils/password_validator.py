"""
Password validation utility for enforcing password strength requirements.

Password Requirements:
- Minimum 8 characters
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one number (0-9)
- Special characters are optional (recommended but not required)
"""

import re
from typing import Tuple, List


def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password strength against security requirements.
    
    Args:
        password: The password string to validate
        
    Returns:
        Tuple of (is_valid, error_messages)
        - is_valid: True if password meets all requirements, False otherwise
        - error_messages: List of requirement violations (empty if valid)
    
    Examples:
        >>> validate_password_strength("weak")
        (False, ['Password must be at least 8 characters long', ...])
        
        >>> validate_password_strength("SecurePass123")
        (True, [])
    """
    errors = []
    
    # Check minimum length (8 characters)
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter (A-Z)")
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter (a-z)")
    
    # Check for at least one number
    if not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one number (0-9)")
    
    # Note: Special characters are NOT required, but recommended
    # Users can use them if they want for extra security
    
    is_valid = len(errors) == 0
    return is_valid, errors


def get_password_requirements() -> List[str]:
    """
    Get a list of all password requirements for display to users.
    
    Returns:
        List of password requirement strings
    """
    return [
        "At least 8 characters long",
        "At least one uppercase letter (A-Z)",
        "At least one lowercase letter (a-z)",
        "At least one number (0-9)",
        "Special characters are optional but recommended for stronger security"
    ]
