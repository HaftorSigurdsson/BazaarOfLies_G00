#!/usr/bin/env python3
"""Unit tests for gm/crypto.py."""

import base64
import tempfile
from pathlib import Path

import pytest

from gm.crypto import (
    decrypt_payload,
    encrypt_for_seat,
    generate_ephemeral_keypair,
    generate_gm_keypair,
    generate_signing_keypair,
    load_gm_private_key,
    open_chat,
    seal_chat,
    sign_payload,
    validate_public_key,
    verify_payload,
)


@pytest.fixture
def temp_key_file():
    """Fixture: temporary GM private key."""
    priv, pub = generate_gm_keypair()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
        f.write(priv)
        f.flush()
        yield f.name
        Path(f.name).unlink()


def test_generate_gm_keypair():
    """Test generate_gm_keypair()."""
    priv, pub = generate_gm_keypair()
    assert priv.startswith("-") is False
    assert pub.startswith("-") is False
    assert len(base64.b64decode(priv)) == 32
    assert len(base64.b64decode(pub)) == 32


def test_load_gm_private_key(temp_key_file):
    """Test load_gm_private_key()."""
    with open(temp_key_file, "r") as f:
        priv = f.read().strip()
    key = load_gm_private_key(priv)
    assert key is not None


def test_validate_public_key():
    """Test validate_public_key()."""
    _, pub = generate_gm_keypair()
    assert validate_public_key(pub) is True
    assert validate_public_key("invalid") is False


def test_encrypt_decrypt(temp_key_file):
    """Test encrypt_for_seat() and decrypt_payload()."""
    with open(temp_key_file, "r") as f:
        priv = f.read().strip()
    key = load_gm_private_key(priv)
    
    pub, _ = generate_ephemeral_keypair()
    plaintext = {"test": "data"}
    encrypted = encrypt_for_seat(pub, plaintext)
    decrypted = decrypt_payload(key, encrypted)
    assert decrypted == plaintext


def test_sign_verify():
    """Test sign_payload() and verify_payload()."""
    priv, pub = generate_signing_keypair()
    payload = {"test": "data"}
    signature = sign_payload(priv, payload)
    assert verify_payload(pub, payload, signature) is True
    assert verify_payload(pub, {"test": "wrong"}, signature) is False


def test_seal_open_chat():
    """Test seal_chat() and open_chat()."""
    key = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode()
    payload = {"test": "data"}
    sealed = seal_chat(key, payload)
    opened = open_chat(key, sealed)
    assert opened == payload
    assert open_chat(key, "invalid") is None