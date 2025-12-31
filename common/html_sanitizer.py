"""
HTML Sanitization Utility

Provides safe HTML sanitization for user-generated content.
Uses bleach library to whitelist safe tags and remove all scripts.
"""

try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False
    import re


# Whitelist of allowed HTML tags (very restrictive)
ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'a']

# Whitelist of allowed attributes
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
}

# Allowed protocols for links
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def sanitize_html(value, strip=True):
    """
    Sanitize HTML content by removing dangerous tags and attributes.
    
    Args:
        value (str): HTML content to sanitize
        strip (bool): If True, strip disallowed tags; if False, escape them
        
    Returns:
        str: Sanitized HTML
    """
    if not isinstance(value, str):
        return value
    
    if BLEACH_AVAILABLE:
        # Use bleach for comprehensive sanitization
        return bleach.clean(
            value,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=strip
        )
    else:
        # Fallback: simple regex-based sanitization
        # Remove all HTML tags
        return re.sub(r'<[^>]+>', '', value)


def sanitize_text(value):
    """
    Sanitize plain text by removing ALL HTML tags.
    
    Args:
        value (str): Text to sanitize
        
    Returns:
        str: Plain text with no HTML
    """
    if not isinstance(value, str):
        return value
    
    if BLEACH_AVAILABLE:
        # Remove all tags
        return bleach.clean(value, tags=[], strip=True)
    else:
        # Fallback: regex
        return re.sub(r'<[^>]+>', '', value)
