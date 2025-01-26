import base64
from cryptography.hazmat.primitives import padding, serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

def load_public_key(public_key_str):
    public_key = serialization.load_pem_public_key(
        public_key_str.encode('utf-8'),
        backend=default_backend()
    )

    return public_key

def create_secret(payload, user_id, public_key_str):
    records = []
    public_key = load_public_key(public_key_str)

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