"""
QR Code Encryption/Decryption Utilities

Provides AES encryption for QR code data to secure offline sync payloads.
Used by both QR generation and offline sync endpoints.
"""
import os
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from django.conf import settings


def get_encryption_key():
    """Get the QR encryption key from settings."""
    key = getattr(settings, 'QR_ENCRYPTION_KEY', 'default-insecure-key-change-me')
    return hashlib.sha256(key.encode()).digest()


def encrypt_qr_data(data: str) -> str:
    """
    Encrypt data for QR code using AES-EAX.
    
    Args:
        data: JSON string to encrypt
        
    Returns:
        Base64 encoded encrypted data with nonce and tag
    """
    key = get_encryption_key()
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(data.encode('utf-8'))
    
    # Combine nonce + tag + ciphertext and encode to base64
    result = cipher.nonce + tag + ciphertext
    return base64.b64encode(result).decode('utf-8')


def decrypt_qr_data(encrypted_data: str) -> str:
    """
    Decrypt data from QR code.
    
    Args:
        encrypted_data: Base64 encoded encrypted data
        
    Returns:
        Decrypted JSON string
        
    Raises:
        ValueError: If decryption fails or data is tampered
    """
    key = get_encryption_key()
    
    try:
        # Decode from base64
        raw = base64.b64decode(encrypted_data)
        
        # Extract components (nonce: 16 bytes, tag: 16 bytes, rest: ciphertext)
        nonce = raw[:16]
        tag = raw[16:32]
        ciphertext = raw[32:]
        
        # Decrypt and verify
        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        
        return plaintext.decode('utf-8')
    except (ValueError, KeyError) as e:
        raise ValueError(f"Failed to decrypt QR data: {str(e)}")
