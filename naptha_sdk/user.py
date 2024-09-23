from ecdsa import SigningKey, SECP256k1

def generate_keypair(private_key=None): 
    private_key = SigningKey.generate(curve=SECP256k1).to_string().hex()
    public_key = get_public_key(private_key)
    return public_key, private_key

def get_public_key(private_key_hex):
    private_key = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
    public_key = private_key.get_verifying_key()
    return public_key.to_string().hex()


if __name__ == "__main__":
    public_key, private_key = generate_keypair()
    print(f"Public Key: {public_key}")
    print(f"Private Key: {private_key}")
