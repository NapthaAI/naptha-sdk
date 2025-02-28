import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from naptha_sdk.utils import get_logger
from dotenv import load_dotenv

logger = get_logger(__name__)

def create_secret(payload, user_id):
    """ Create encrypted secrets from payload. """
    records = []
    
    aes_key = check_and_generate_aes_secret()
    if not aes_key:
        raise ValueError("Failed to get or generate AES key")

    for key_name, value in payload.items():
        encrypted_value = encrypt_with_aes(value, aes_key)
        
        records.append({
            "user_id": f"<record>{user_id}",
            "secret_value": encrypted_value,
            "key_name": key_name
        })

    return records

def encrypt_with_server_public_key(data, public_key):
    """ Encrypt data using the server's public key. """
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
    """ Verify and reconstruct the RSA public key from the provided data. """
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

def check_and_generate_aes_secret():
    """ Check for existing AES secret or generate a new one. """
    env_file_path = os.path.join(os.path.dirname(__file__), '../.env')
    
    aes_secret = os.getenv("AES_SECRET")
    if aes_secret:
        try:
            return base64.b64decode(aes_secret)
        except Exception as e:
            logger.error(f"Invalid AES_SECRET format: {e}")
    
    logger.info("AES secret not found or invalid. Generating new AES secret...")
    aes_key = generate_aes_secret(env_file_path)
    
    load_dotenv(env_file_path, override=True)
    
    return aes_key

def generate_aes_secret(env_file_path):
    """ Generate a new AES secret key and save it to the .env file. """
    try:
        aes_key = os.urandom(32)
        encoded_key = base64.b64encode(aes_key).decode()
        
        if not os.path.exists(os.path.dirname(env_file_path)):
            os.makedirs(os.path.dirname(env_file_path))

        with open(env_file_path, "a+") as f:
            f.seek(0)
            content = f.read()
            if "AES_SECRET=" not in content:
                if content and not content.endswith('\n'):
                    f.write('\n')
                f.write(f"AES_SECRET={encoded_key}\n")
        
        logger.info("AES secret generated and saved to .env file.")
        return aes_key
    except Exception as e:
        logger.error(f"Failed to generate AES secret: {e}")
        raise

def encrypt_with_aes(data: str, aes_key: bytes) -> str:
    """ Encrypt data using AES-GCM."""
    try:
        aesgcm = AESGCM(aes_key)
        nonce = os.urandom(12)
        data_bytes = data.encode('utf-8')
        ciphertext = aesgcm.encrypt(nonce, data_bytes, None)
        encrypted_data = nonce + ciphertext
        
        return base64.b64encode(encrypted_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Encryption failed: {str(e)}")
        raise

def decrypt_with_aes(encrypted_data: str, aes_key: str) -> str:
    """ Decrypt data using AES-GCM."""
    try:
        aes_key = base64.b64decode(aes_key)
        encrypted_bytes = base64.b64decode(encrypted_data)
        nonce = encrypted_bytes[:12]
        ciphertext = encrypted_bytes[12:]
        
        aesgcm = AESGCM(aes_key)
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
        
        return decrypted_data.decode('utf-8')
    except Exception as e:
        logger.error(f"Decryption failed (possible tampering): {str(e)}")
        raise