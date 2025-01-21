import os
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from naptha_sdk.user import get_private_key

def create_secret(payload, user_id):
    records = []

    for key_name, value in payload.items():
        # Encrypt the value using user's private key as AES secret key
        encrypted_value_aes = encrypt_with_aes(value, get_private_key(os.getenv("PRIVATE_KEY"))).hex()

        records.append({
            "user_id": f"<record>{user_id}",
            "secret_value": encrypted_value_aes,
            "key_name": key_name
        })

    return records

def encrypt_with_aes(data, private_key_hex):
    private_key_bytes = bytes.fromhex(private_key_hex)
    if len(private_key_bytes) != 32:
        raise ValueError("The private key must be 32 bytes long for AES-256 encryption.")

    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data.encode()) + padder.finalize()

    cipher = Cipher(algorithms.AES(private_key_bytes), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    return iv + encrypted_data

def decrypt_aes(encrypted_data):
    if not encrypted_data:
        raise ValueError("Encrypted data cannot be None or empty.")
    
    private_key_bytes = bytes.fromhex(get_private_key(os.getenv("PRIVATE_KEY")))
    if len(private_key_bytes) != 32:
        raise ValueError("The private key must be 32 bytes long for AES-256 decryption.")
    
    encrypted_data_bytes = bytes.fromhex(encrypted_data) if isinstance(encrypted_data, str) else encrypted_data

    iv = encrypted_data_bytes[:16]
    encrypted_message = encrypted_data_bytes[16:]

    cipher = Cipher(algorithms.AES(private_key_bytes), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(encrypted_message) + decryptor.finalize()

    # Unpad the decrypted data to retrieve the original message
    unpadder = padding.PKCS7(128).unpadder()
    original_data = unpadder.update(decrypted_data) + unpadder.finalize()

    return original_data.decode() 