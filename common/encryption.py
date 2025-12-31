import base64
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import json


def generate_encryption_key():
    """Generate a random 32-byte (256-bit) AES key."""
    return secrets.token_bytes(32)


import uuid

class UUIDEncoder(json.JSONEncoder):
    """Custom encoder to handle UUID serialization."""
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)

def encrypt_json_response(data_dict):
    """
    Encrypt a dictionary to be sent as JSON response.
    
    Returns:
        tuple: (encrypted_base64_string, key_base64_string)
    """
    # Generate a random key and IV for this session
    key = generate_encryption_key()
    iv = secrets.token_bytes(16)  # AES block size
    
    # Convert dict to JSON string with custom encoder
    json_string = json.dumps(data_dict, cls=UUIDEncoder)
    
    # Pad the data to AES block size
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(json_string.encode('utf-8')) + padder.finalize()
    
    # Encrypt using AES-256-CBC
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    
    # Combine IV + encrypted data for transmission
    combined = iv + encrypted_data
    
    # Base64 encode for safe JSON transmission
    encrypted_b64 = base64.b64encode(combined).decode('utf-8')
    key_b64 = base64.b64encode(key).decode('utf-8')
    
    return encrypted_b64, key_b64


def decrypt_json_response(encrypted_b64, key_b64):
    """
    Decrypt an encrypted response (for testing purposes).
    
    Args:
        encrypted_b64: Base64 encoded (IV + encrypted data)
        key_b64: Base64 encoded key
    
    Returns:
        dict: Decrypted JSON object
    """
    # Decode from base64
    combined = base64.b64decode(encrypted_b64)
    key = base64.b64decode(key_b64)
    
    # Extract IV and encrypted data
    iv = combined[:16]
    encrypted_data = combined[16:]
    
    # Decrypt using AES-256-CBC
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
    
    # Unpad the data
    unpadder = padding.PKCS7(128).unpadder()
    json_string = unpadder.update(padded_data) + unpadder.finalize()
    
    # Parse JSON
    return json.loads(json_string.decode('utf-8'))
