"""
Test field-specific character validation
"""

import pytest
from django.core.exceptions import ValidationError
from common.validators import (
    validate_alphanumeric,
    validate_field_characters,
    validate_input,
)


class TestAlphanumericValidation:
    """Test alphanumeric validation"""
    
    def test_alphanumeric_with_spaces(self):
        assert validate_alphanumeric("John Doe", allow_spaces=True)
        assert validate_alphanumeric("User 123", allow_spaces=True)
    
    def test_alphanumeric_no_spaces(self):
        assert validate_alphanumeric("JohnDoe", allow_spaces=False)
        assert validate_alphanumeric("User123", allow_spaces=False)
    
    def test_reject_special_characters(self):
        assert not validate_alphanumeric("John()", allow_spaces=True)
        assert not validate_alphanumeric("scrip>", allow_spaces=True)
        assert not validate_alphanumeric("<script>", allow_spaces=True)
        assert not validate_alphanumeric("(xxs)", allow_spaces=True)


class TestFieldCharacterValidation:
    """Test field-specific character validation"""
    
    def test_first_name_accepts_alphanumeric(self):
        """First name should accept letters, numbers, spaces"""
        validate_field_characters("John Doe", "first_name")  # Should not raise
        validate_field_characters("Mohamed Ali", "first_name")  # Should not raise
    
    def test_first_name_rejects_special_chars(self):
        """First name should reject special characters"""
        with pytest.raises(ValidationError) as exc:
            validate_field_characters("(xxs)", "first_name")
        assert "can only contain letters, numbers, and spaces" in str(exc.value)
        
        with pytest.raises(ValidationError):
            validate_field_characters("scrip>", "first_name")
        
        with pytest.raises(ValidationError):
            validate_field_characters("John<script>", "first_name")
    
    def test_email_validation(self):
        """Email should match email pattern"""
        validate_field_characters("user@example.com", "email")  # Should not raise
        
        with pytest.raises(ValidationError):
            validate_field_characters("invalid-email", "email")
    
    def test_phone_validation(self):
        """Phone should accept numbers and + - ( ) space"""
        validate_field_characters("+1 234-567-8900", "phone_number")  # Should not raise
        validate_field_characters("0912345678", "phone_number")  # Should not raise
        
        with pytest.raises(ValidationError):
            validate_field_characters("phone<script>", "phone_number")


class TestIntegratedValidation:
    """Test that validate_input calls field validation first"""
    
    def test_first_name_full_validation(self):
        """Test that first_name is validated for characters before XSS"""
        # Valid input
        result = validate_input("John Doe", "first_name", strict_mode=True)
        assert result == "John Doe"
        
        # Invalid characters (should be caught by field validation)
        with pytest.raises(ValidationError) as exc:
            validate_input("(xxs)", "first_name", strict_mode=True)
        assert "can only contain" in str(exc.value)
        
        # Even partial XSS should be caught by field validation
        with pytest.raises(ValidationError):
            validate_input("scrip>", "first_name", strict_mode=True)
    
    def test_description_allows_more_characters(self):
        """Description field doesn't have strict character limits"""
        # Description can have some special characters, but not XSS
        result = validate_input("This is a description.", "description", strict_mode=True)
        assert result == "This is a description."
        
        # But XSS should still be blocked
        with pytest.raises(ValidationError):
            validate_input("<script>alert(1)</script>", "description", strict_mode=True)
