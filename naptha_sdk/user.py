from ecdsa import SigningKey, SECP256k1
import os, re

def generate_keypair(private_key_filename=None):
    pkfile = private_key_filename if private_key_filename else 'private_key.pem'
    file_path = os.path.join(os.getcwd(), pkfile)
    
    # Check if private key file exists and is not empty
    if private_key_filename and os.path.isfile(file_path):
        with open(file_path, 'r') as file:
            private_key = file.read().strip()
            # Check if file is empty or contains only whitespace
            if not private_key:
                # Generate new key if file is empty
                private_key = SigningKey.generate(curve=SECP256k1).to_string().hex()
                with open(file_path, 'w') as f:
                    f.write(private_key)
    else:
        # Generate new private key
        private_key = SigningKey.generate(curve=SECP256k1).to_string().hex()
        # Save the private key to a file
        with open(file_path, 'w') as file:
            file.write(private_key)

    public_key = generate_public_key(private_key)
    return public_key, file_path

def get_public_key(private_key):
    # To ensure old users can still login
    if private_key and is_hex(private_key):
        private_key_hex = private_key
    elif private_key and os.path.isfile(private_key):
        with open(private_key) as file:
            content = file.read().strip()
            
            if content:
                private_key_hex = content
            else:
                return None
    else:
        return None

    return generate_public_key(private_key_hex)
    
def generate_public_key(private_key_hex):
    private_key = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
    public_key = private_key.get_verifying_key()

    return public_key.to_string().hex()

def is_hex(string):
    # Check if the string matches the pattern for a hexadecimal key
    return bool(re.match(r'^[0-9a-fA-F]{64}$', string))

def sign_consumer_id(consumer_id, private_key):
    if private_key and is_hex(private_key):
        private_key_hex = private_key
    elif private_key and os.path.isfile(private_key):
        with open(private_key) as file:
            content = file.read().strip()
            
            if content:
                private_key_hex = content
            else:
                return None
    else:
        return None
    
    private_key = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
    consumer_id_bytes = consumer_id.encode('utf-8')
    signature = private_key.sign(consumer_id_bytes)
    return signature.hex()