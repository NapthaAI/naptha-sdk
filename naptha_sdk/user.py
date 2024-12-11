from ecdsa import SigningKey, SECP256k1
import os

def generate_keypair(private_key_filename=None): 
    private_key = SigningKey.generate(curve=SECP256k1).to_string().hex()
    public_key = generate_public_key(private_key)
    pkfile = private_key_filename if private_key_filename else 'private_key.pem'

    # Save the private key to a file
    with open(os.path.join(os.getcwd(), pkfile), 'w') as file:
        file.write(private_key)

    return public_key, os.path.join(os.getcwd(), pkfile)

def get_public_key(private_key_filepath):
    if private_key_filepath and os.path.isfile(private_key_filepath):
        with open(private_key_filepath) as file:
            private_key_hex = file.readline()
            return generate_public_key(private_key_hex)
    else:
        return None
    
def generate_public_key(private_key_hex):
    private_key = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
    public_key = private_key.get_verifying_key()
    return public_key.to_string().hex()