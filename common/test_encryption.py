"""
Test script to verify encryption/decryption works correctly
Run this to test the encryption implementation before deploying
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from common.encryption import encrypt_json_response, decrypt_json_response

# Sample login response data
test_data = {
    "username": "test_user",
    "role": "admin",
    "id": "00000000-0000-0000-0000-000000000001",
    "first_name": "Test",
    "last_name": "User",
    "current_station": {
        "id": 1,
        "name": "Main Station"
    }
}

print("Testing Encryption/Decryption Implementation")
print("=" * 50)
print("\nOriginal Data:")
print(test_data)

# Encrypt
encrypted_data, encryption_key = encrypt_json_response(test_data)
print(f"\n✓ Encrypted successfully")
print(f"Encrypted data (base64): {encrypted_data[:50]}...")
print(f"Encryption key (base64): {encryption_key[:50]}...")

# Decrypt
try:
    decrypted_data = decrypt_json_response(encrypted_data, encryption_key)
    print(f"\n✓ Decrypted successfully")
    print("\nDecrypted Data:")
    print(decrypted_data)
    
    # Verify
    if decrypted_data == test_data:
        print("\n✅ SUCCESS: Encryption/Decryption working correctly!")
    else:
        print("\n❌ ERROR: Decrypted data doesn't match original")
        print("Differences found")
except Exception as e:
    print(f"\n❌ ERROR during decryption: {e}")
    import traceback
    traceback.print_exc()
