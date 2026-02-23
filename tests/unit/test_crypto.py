"""Unit tests for credential encryption service."""

import os
import pytest

from packages.security.crypto import (
    encrypt_credential,
    decrypt_credential,
    get_encryption_key,
    EncryptedData,
)


@pytest.fixture
def encryption_key():
    """Set up a test encryption key."""
    # 32 bytes (64 hex characters) for AES-256
    test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    os.environ["ENCRYPTION_KEY"] = test_key
    yield test_key
    # Cleanup
    if "ENCRYPTION_KEY" in os.environ:
        del os.environ["ENCRYPTION_KEY"]


class TestGetEncryptionKey:
    """Tests for get_encryption_key function."""

    def test_get_encryption_key_success(self, encryption_key):
        """Test retrieving encryption key from environment."""
        key = get_encryption_key()
        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_get_encryption_key_missing(self):
        """Test error when ENCRYPTION_KEY is not set."""
        if "ENCRYPTION_KEY" in os.environ:
            del os.environ["ENCRYPTION_KEY"]

        with pytest.raises(ValueError, match="ENCRYPTION_KEY environment variable is not set"):
            get_encryption_key()

    def test_get_encryption_key_invalid_hex(self):
        """Test error when ENCRYPTION_KEY is not valid hex."""
        os.environ["ENCRYPTION_KEY"] = "not_valid_hex_string"

        with pytest.raises(ValueError, match="ENCRYPTION_KEY must be a valid hex string"):
            get_encryption_key()

    def test_get_encryption_key_wrong_length(self):
        """Test error when ENCRYPTION_KEY is wrong length."""
        # 16 bytes instead of 32
        os.environ["ENCRYPTION_KEY"] = "0123456789abcdef0123456789abcdef"

        with pytest.raises(ValueError, match="ENCRYPTION_KEY must be 32 bytes"):
            get_encryption_key()


class TestEncryptCredential:
    """Tests for encrypt_credential function."""

    def test_encrypt_credential_success(self, encryption_key):
        """Test successful credential encryption."""
        plaintext = "my_secret_password"
        encrypted = encrypt_credential(plaintext)

        assert isinstance(encrypted, EncryptedData)
        assert isinstance(encrypted.encrypted_value, bytes)
        assert isinstance(encrypted.iv, bytes)
        assert len(encrypted.iv) == 16  # AES block size
        assert encrypted.encrypted_value != plaintext.encode("utf-8")

    def test_encrypt_credential_empty_string(self, encryption_key):
        """Test error when encrypting empty string."""
        with pytest.raises(ValueError, match="Cannot encrypt empty plaintext"):
            encrypt_credential("")

    def test_encrypt_credential_different_ivs(self, encryption_key):
        """Test that each encryption uses a different IV."""
        plaintext = "same_password"
        encrypted1 = encrypt_credential(plaintext)
        encrypted2 = encrypt_credential(plaintext)

        # Same plaintext should produce different ciphertext due to different IVs
        assert encrypted1.iv != encrypted2.iv
        assert encrypted1.encrypted_value != encrypted2.encrypted_value

    def test_encrypt_credential_unicode(self, encryption_key):
        """Test encrypting unicode characters."""
        plaintext = "pässwörd_with_émojis_🔐"
        encrypted = encrypt_credential(plaintext)

        assert isinstance(encrypted.encrypted_value, bytes)
        assert len(encrypted.encrypted_value) > 0


class TestDecryptCredential:
    """Tests for decrypt_credential function."""

    def test_decrypt_credential_success(self, encryption_key):
        """Test successful credential decryption."""
        plaintext = "my_secret_password"
        encrypted = encrypt_credential(plaintext)
        decrypted = decrypt_credential(encrypted)

        assert decrypted == plaintext

    def test_decrypt_credential_empty_encrypted_value(self, encryption_key):
        """Test error when decrypting empty encrypted value."""
        encrypted = EncryptedData(encrypted_value=b"", iv=os.urandom(16))

        with pytest.raises(ValueError, match="Cannot decrypt empty encrypted value"):
            decrypt_credential(encrypted)

    def test_decrypt_credential_missing_iv(self, encryption_key):
        """Test error when IV is missing."""
        encrypted = EncryptedData(encrypted_value=b"some_data", iv=b"")

        with pytest.raises(ValueError, match="Cannot decrypt without initialization vector"):
            decrypt_credential(encrypted)

    def test_decrypt_credential_invalid_iv_length(self, encryption_key):
        """Test error when IV has wrong length."""
        encrypted = EncryptedData(encrypted_value=b"some_data", iv=b"short")

        with pytest.raises(ValueError, match="IV must be 16 bytes"):
            decrypt_credential(encrypted)

    def test_decrypt_credential_unicode(self, encryption_key):
        """Test decrypting unicode characters."""
        plaintext = "pässwörd_with_émojis_🔐"
        encrypted = encrypt_credential(plaintext)
        decrypted = decrypt_credential(encrypted)

        assert decrypted == plaintext


class TestEncryptionRoundTrip:
    """Tests for encryption/decryption round-trip."""

    def test_round_trip_simple_password(self, encryption_key):
        """Test round-trip with simple password."""
        plaintext = "simple_password"
        encrypted = encrypt_credential(plaintext)
        decrypted = decrypt_credential(encrypted)

        assert decrypted == plaintext

    def test_round_trip_aws_api_key(self, encryption_key):
        """Test round-trip with AWS API key format."""
        plaintext = "AKIAIOSFODNN7EXAMPLE"
        encrypted = encrypt_credential(plaintext)
        decrypted = decrypt_credential(encrypted)

        assert decrypted == plaintext

    def test_round_trip_ssh_key(self, encryption_key):
        """Test round-trip with SSH key format."""
        plaintext = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... user@host"
        encrypted = encrypt_credential(plaintext)
        decrypted = decrypt_credential(encrypted)

        assert decrypted == plaintext

    def test_round_trip_long_credential(self, encryption_key):
        """Test round-trip with long credential."""
        plaintext = "a" * 1000  # Long credential
        encrypted = encrypt_credential(plaintext)
        decrypted = decrypt_credential(encrypted)

        assert decrypted == plaintext

    def test_round_trip_special_characters(self, encryption_key):
        """Test round-trip with special characters."""
        plaintext = "p@ssw0rd!#$%^&*()_+-=[]{}|;:',.<>?/~`"
        encrypted = encrypt_credential(plaintext)
        decrypted = decrypt_credential(encrypted)

        assert decrypted == plaintext
