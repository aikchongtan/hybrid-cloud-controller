"""Credential encryption service using AES-256."""

import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


@dataclass
class EncryptedData:
    """Container for encrypted data and initialization vector."""

    encrypted_value: bytes
    iv: bytes


def get_encryption_key() -> bytes:
    """
    Retrieve encryption key from environment variables.

    Returns:
        32-byte encryption key for AES-256

    Raises:
        ValueError: If ENCRYPTION_KEY environment variable is not set or invalid
    """
    key_hex = os.environ.get("ENCRYPTION_KEY")
    if not key_hex:
        raise ValueError(
            "ENCRYPTION_KEY environment variable is not set. "
            "Please set a 64-character hex string (32 bytes for AES-256)."
        )

    try:
        key = bytes.fromhex(key_hex)
    except ValueError as e:
        raise ValueError(
            f"ENCRYPTION_KEY must be a valid hex string: {e}"
        ) from e

    if len(key) != 32:
        raise ValueError(
            f"ENCRYPTION_KEY must be 32 bytes (64 hex characters) for AES-256, got {len(key)} bytes"
        )

    return key


def encrypt_credential(plaintext: str) -> EncryptedData:
    """
    Encrypt a credential using AES-256-CBC.

    Args:
        plaintext: The credential to encrypt

    Returns:
        EncryptedData containing encrypted value and initialization vector

    Raises:
        ValueError: If encryption key is invalid
    """
    if not plaintext:
        raise ValueError("Cannot encrypt empty plaintext")

    key = get_encryption_key()

    # Generate random IV (16 bytes for AES)
    iv = os.urandom(16)

    # Pad plaintext to block size (128 bits = 16 bytes for AES)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext.encode("utf-8")) + padder.finalize()

    # Encrypt using AES-256-CBC
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_value = encryptor.update(padded_data) + encryptor.finalize()

    return EncryptedData(encrypted_value=encrypted_value, iv=iv)


def decrypt_credential(encrypted_data: EncryptedData) -> str:
    """
    Decrypt a credential using AES-256-CBC.

    Args:
        encrypted_data: EncryptedData containing encrypted value and IV

    Returns:
        Decrypted plaintext credential

    Raises:
        ValueError: If decryption fails or data is invalid
    """
    if not encrypted_data.encrypted_value:
        raise ValueError("Cannot decrypt empty encrypted value")
    if not encrypted_data.iv:
        raise ValueError("Cannot decrypt without initialization vector")
    if len(encrypted_data.iv) != 16:
        raise ValueError(f"IV must be 16 bytes, got {len(encrypted_data.iv)} bytes")

    key = get_encryption_key()

    # Decrypt using AES-256-CBC
    cipher = Cipher(
        algorithms.AES(key), modes.CBC(encrypted_data.iv), backend=default_backend()
    )
    decryptor = cipher.decryptor()
    padded_plaintext = (
        decryptor.update(encrypted_data.encrypted_value) + decryptor.finalize()
    )

    # Unpad plaintext
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

    return plaintext.decode("utf-8")
