import base64
import json
import os
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.encoding import Base64Encoder
from nacl.exceptions import CryptoError


def load_gm_private_key(private_key_b64: str) -> PrivateKey:
    """Load the GM's private key from a base64-encoded string."""
    return PrivateKey(base64.b64decode(private_key_b64))


def validate_public_key(public_key_b64: str) -> bool:
    """Validate a base64-encoded public key."""
    try:
        PublicKey(base64.b64decode(public_key_b64))
        return True
    except (ValueError, CryptoError):
        return False


def generate_ephemeral_keypair() -> tuple[str, str]:
    """Generate an ephemeral keypair for a match."""
    private_key = PrivateKey.generate()
    public_key = private_key.public_key
    return (
        base64.b64encode(bytes(private_key)).decode(),
        base64.b64encode(bytes(public_key)).decode()
    )


def encrypt_for_seat(public_key_b64: str, plaintext: dict) -> str:
    """Encrypt a payload for a seat using its public key."""
    if not validate_public_key(public_key_b64):
        raise ValueError("Invalid public key")
    box = SealedBox(PublicKey(base64.b64decode(public_key_b64)))
    encrypted = box.encrypt(json.dumps(plaintext).encode(), encoder=Base64Encoder)
    return encrypted.decode()


def decrypt_payload(private_key: PrivateKey, payload_b64: str) -> dict:
    """Decrypt a base64-encoded payload using the GM's private key."""
    box = SealedBox(private_key)
    decrypted = box.decrypt(base64.b64decode(payload_b64))
    return json.loads(decrypted.decode())


def encrypt_for_seat(public_key_b64: str, plaintext: dict) -> str:
    """Encrypt a payload for a seat using its public key."""
    box = SealedBox(PublicKey(base64.b64decode(public_key_b64)))
    encrypted = box.encrypt(json.dumps(plaintext).encode(), encoder=Base64Encoder)
    return encrypted.decode()


def generate_gm_keypair() -> tuple[str, str]:
    """Generate a new GM keypair (for setup only)."""
    private_key = PrivateKey.generate()
    public_key = private_key.public_key
    return (
        base64.b64encode(bytes(private_key)).decode(),
        base64.b64encode(bytes(public_key)).decode()
    )