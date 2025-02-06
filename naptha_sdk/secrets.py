import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

def create_secret(payload, user_id, public_key):
    records = []

    for key_name, value in payload.items():
        # Encrypt the value using server's public_key
        encrypted_value = encrypt_with_server_public_key(value, public_key)

        records.append({
            "user_id": f"<record>{user_id}",
            "secret_value": encrypted_value,
            "key_name": key_name
        })

    return records

def encrypt_with_server_public_key(data, public_key):
    encrypted_data = public_key.encrypt(
        data.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    base64_encrypted_data = base64.b64encode(encrypted_data).decode('utf-8')

    return base64_encrypted_data

def verify_and_reconstruct_rsa_key(data):
    # Check if the 'kty' is RSA and 'use' is enc
    if 'keys' not in data or len(data['keys']) == 0:
        raise ValueError("No keys found in the provided data.")
    
    key = data['keys'][0]
    
    if key.get('kty') != 'RSA' or key.get('use') != 'enc':
        raise ValueError("The key is not an RSA encryption key.")

    try:
        n = int.from_bytes(base64.urlsafe_b64decode(key['n'] + '=='), byteorder='big')
        e = int.from_bytes(base64.urlsafe_b64decode(key['e'] + '=='), byteorder='big')
    except Exception as e:
        raise ValueError(f"Error decoding base64 values: {e}")
    
    # Reconstruct the RSA public key
    public_key = rsa.RSAPublicNumbers(e, n).public_key(default_backend())
    
    return public_key