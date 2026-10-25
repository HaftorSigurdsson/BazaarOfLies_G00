import base64
import binascii
import json
import os
from typing import Dict, List, Optional, Tuple, Union

from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import Base64Encoder
from nacl.exceptions import BadSignatureError, CryptoError


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


def generate_ephemeral_keypair() -> Tuple[str, str]:
    """Generate an ephemeral keypair for a match."""
    private_key = PrivateKey.generate()
    public_key = private_key.public_key
    return (
        base64.b64encode(bytes(private_key)).decode(),
        base64.b64encode(bytes(public_key)).decode()
    )


def encrypt_for_seat(public_key_b64: str, plaintext: Dict[str, Union[str, int, List, Dict]]) -> str:
    """Encrypt a payload for a seat using its public key."""
    if not validate_public_key(public_key_b64):
        raise ValueError("Invalid public key")
    box = SealedBox(PublicKey(base64.b64decode(public_key_b64)))
    encrypted = box.encrypt(json.dumps(plaintext).encode(), encoder=Base64Encoder)
    return encrypted.decode()


def decrypt_payload(private_key: PrivateKey, payload_b64: str) -> Dict[str, Union[str, int, List, Dict]]:
    """Decrypt a base64-encoded payload using the GM's private key."""
    box = SealedBox(private_key)
    decrypted = box.decrypt(base64.b64decode(payload_b64))
    return json.loads(decrypted.decode())


def generate_gm_keypair() -> Tuple[str, str]:
    """Generate a new GM keypair (for setup only)."""
    private_key = PrivateKey.generate()
    public_key = private_key.public_key
    return (
        base64.b64encode(bytes(private_key)).decode(),
        base64.b64encode(bytes(public_key)).decode()
    )


# ------------------------------------------------------- signatures (v1.2) ---
# Public day votes are plaintext but SIGNED with a per-seat Ed25519 key so
# nobody can forge another merchant's ballot. Private signing keys live in
# the operator's vault (never in the repo); public keys are registered in
# setup/seats.json as "signing_public_key" by setup/make_signing_keys.py.


def canonical_json(payload: Dict[str, Union[str, int, List, Dict]]) -> str:
    """Deterministic serialization — both signer and verifier must build the
    exact same bytes before signing/verifying."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def generate_signing_keypair() -> Tuple[str, str]:
    """Generate a per-seat Ed25519 signing keypair (private, public), base64."""
    sk = SigningKey.generate()
    return (
        base64.b64encode(bytes(sk)).decode(),
        base64.b64encode(bytes(sk.verify_key)).decode()
    )


def sign_payload(signing_key_b64: str, payload: Dict[str, Union[str, int, List, Dict]]) -> str:
    """Detached Ed25519 signature over the canonical JSON of the payload."""
    sk = SigningKey(base64.b64decode(signing_key_b64))
    sig = sk.sign(canonical_json(payload).encode()).signature
    return base64.b64encode(sig).decode()


def verify_payload(public_key_b64: str, payload: Dict[str, Union[str, int, List, Dict]], sig_b64: str) -> bool:
    """Verify a detached signature over the canonical JSON of the payload."""
    try:
        vk = VerifyKey(base64.b64decode(public_key_b64))
        vk.verify(canonical_json(payload).encode(), base64.b64decode(sig_b64))
        return True
    except (BadSignatureError, binascii.Error, ValueError, TypeError):
        return False


# ------------------------------------------------ night chat channel ------
# The in-repo council channel: symmetric sealing on the dossier's shared
# night_channel_key. Fixed-size padding before sealing, so every ciphertext
# is byte-identical in length whatever the message — a snoop learns nothing
# from file sizes, and AEAD (SecretBox) means only key-holders can read.

CHAT_PAD_BYTES = 1024              # padded plaintext length for chat payloads


def seal_chat(shared_key_b64: str, payload: Dict[str, Union[str, int, List, Dict]]) -> str:
    """Seal a chat payload with the shared key, padded to a fixed size."""
    from nacl.secret import SecretBox
    key = base64.b64decode(shared_key_b64)
    box = SecretBox(key)
    text = json.dumps(payload, ensure_ascii=False)
    text = text[:CHAT_PAD_BYTES - 1].ljust(CHAT_PAD_BYTES - 1)
    ct = box.encrypt(text.encode())
    return base64.b64encode(ct).decode()


def open_chat(shared_key_b64: str, blob: str) -> Optional[Dict[str, Union[str, int, List, Dict]]]:
    """Open a sealed chat blob. Returns the payload dict, or None when the
    key does not authenticate (another channel's file / corrupt bytes)."""
    from nacl.secret import SecretBox
    try:
        key = base64.b64decode(shared_key_b64)
        box = SecretBox(key)
        text = box.decrypt(base64.b64decode(blob)).decode()
        return json.loads(text.strip() or "null")
    except Exception:
        return None
