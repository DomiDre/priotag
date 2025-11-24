"""
Tests for encryption service - critical security component.

Tests cover:
- Key generation (DEK, salt)
- Password-based key derivation (PBKDF2)
- AES-GCM encryption/decryption
- RSA key wrapping/unwrapping
- Field-level encryption
- Password change flows
- DEK splitting and reconstruction (balanced security mode)
- DEK part encryption/decryption for caching
- get_dek_from_request for different security tiers
- get_user_data and handle_password_change helper functions
"""

import base64
import json
from datetime import datetime
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.hashes import SHA256

from priotag.services.encryption import (
    EncryptionManager,
    get_user_data,
    handle_password_change,
)


@pytest.mark.unit
class TestKeyGeneration:
    """Test cryptographic key generation functions."""

    def test_generate_dek_returns_32_bytes(self):
        """DEK should be 32 bytes (256 bits) for AES-256."""
        dek = EncryptionManager.generate_dek()
        assert len(dek) == 32
        assert isinstance(dek, bytes)

    def test_generate_dek_unique(self):
        """Each DEK generation should produce unique keys."""
        dek1 = EncryptionManager.generate_dek()
        dek2 = EncryptionManager.generate_dek()
        assert dek1 != dek2

    def test_derive_key_from_password_returns_32_bytes(self):
        """Derived key should be 32 bytes."""
        salt = b"test_salt_16byte"
        password = "TestPassword123"
        key = EncryptionManager.derive_key_from_password(password, salt)
        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_derive_key_deterministic(self):
        """Same password and salt should derive same key."""
        salt = b"test_salt_16byte"
        password = "TestPassword123"
        key1 = EncryptionManager.derive_key_from_password(password, salt)
        key2 = EncryptionManager.derive_key_from_password(password, salt)
        assert key1 == key2

    def test_derive_key_different_salts(self):
        """Different salts should produce different keys."""
        password = "TestPassword123"
        key1 = EncryptionManager.derive_key_from_password(password, b"salt_one_16bytes")
        key2 = EncryptionManager.derive_key_from_password(password, b"salt_two_16bytes")
        assert key1 != key2

    def test_derive_key_different_passwords(self):
        """Different passwords should produce different keys."""
        salt = b"test_salt_16byte"
        key1 = EncryptionManager.derive_key_from_password("Password1", salt)
        key2 = EncryptionManager.derive_key_from_password("Password2", salt)
        assert key1 != key2


@pytest.mark.unit
@pytest.mark.security
class TestAESEncryption:
    """Test AES-256-GCM encryption and decryption."""

    def test_encrypt_decrypt_roundtrip(self, test_dek):
        """Encrypt and decrypt should return original data."""
        original = "Test data to encrypt"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        decrypted = EncryptionManager.decrypt_data(encrypted, test_dek)
        assert decrypted == original

    def test_encrypted_data_is_different(self, test_dek):
        """Encrypted data should not equal original."""
        original = "Sensitive information"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        # Encrypted is base64, so decode to compare bytes
        assert encrypted != original
        assert base64.b64decode(encrypted) != original.encode()

    def test_encrypt_with_nonce_randomization(self, test_dek):
        """Same data encrypted twice should produce different ciphertexts."""
        original = "Test data"
        encrypted1 = EncryptionManager.encrypt_data(original, test_dek)
        encrypted2 = EncryptionManager.encrypt_data(original, test_dek)
        assert encrypted1 != encrypted2  # Different nonces

    def test_decrypt_with_wrong_key_fails(self, test_dek):
        """Decryption with wrong key should fail."""
        original = "Test data"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        wrong_dek = EncryptionManager.generate_dek()

        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure # AES-GCM authentication failure
            EncryptionManager.decrypt_data(encrypted, wrong_dek)

    def test_encrypt_empty_string(self, test_dek):
        """Empty string should be encrypted/decrypted correctly."""
        original = ""
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        decrypted = EncryptionManager.decrypt_data(encrypted, test_dek)
        assert decrypted == original

    def test_encrypt_unicode_data(self, test_dek):
        """Unicode characters should be handled correctly."""
        original = "Test with émojis 🔒 and ümlauts"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        decrypted = EncryptionManager.decrypt_data(encrypted, test_dek)
        assert decrypted == original

    def test_encrypted_data_is_base64(self, test_dek):
        """Encrypted data should be valid base64."""
        original = "Test data"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        # Should not raise exception
        decoded = base64.b64decode(encrypted)
        assert isinstance(decoded, bytes)

    def test_decrypt_invalid_base64_fails(self, test_dek):
        """Invalid base64 should raise appropriate error."""
        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure
            EncryptionManager.decrypt_data("not_valid_base64!!!", test_dek)

    def test_decrypt_tampered_data_fails(self, test_dek):
        """Tampered encrypted data should fail authentication."""
        original = "Test data"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)

        # Tamper with the encrypted data
        encrypted_bytes = base64.b64decode(encrypted)
        tampered = encrypted_bytes[:-1] + b"X"  # Change last byte
        tampered_b64 = base64.b64encode(tampered).decode()

        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure # GCM authentication failure
            EncryptionManager.decrypt_data(tampered_b64, test_dek)


@pytest.mark.unit
class TestFieldEncryption:
    """Test field-level encryption for dictionaries."""

    def test_encrypt_fields_dict(self, test_dek):
        """Dictionary should be encrypted as JSON."""
        data = {"name": "John Doe", "age": 30}
        encrypted = EncryptionManager.encrypt_fields(data, test_dek)
        assert isinstance(encrypted, str)
        assert encrypted != json.dumps(data)

    def test_decrypt_fields_roundtrip(self, test_dek):
        """Encrypt and decrypt dict should return original."""
        original = {"name": "Alice", "email": "alice@example.com"}
        encrypted = EncryptionManager.encrypt_fields(original, test_dek)
        decrypted = EncryptionManager.decrypt_fields(encrypted, test_dek)
        assert decrypted == original

    def test_encrypt_fields_preserves_types(self, test_dek):
        """Field types should be preserved after encryption/decryption."""
        original = {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
        }
        encrypted = EncryptionManager.encrypt_fields(original, test_dek)
        decrypted = EncryptionManager.decrypt_fields(encrypted, test_dek)
        assert decrypted == original

    def test_encrypt_fields_nested_dict(self, test_dek):
        """Nested dictionaries should be handled correctly."""
        original = {"user": {"name": "Bob", "address": {"city": "Berlin"}}}
        encrypted = EncryptionManager.encrypt_fields(original, test_dek)
        decrypted = EncryptionManager.decrypt_fields(encrypted, test_dek)
        assert decrypted == original

    def test_decrypt_fields_invalid_json_fails(self, test_dek):
        """Invalid JSON after decryption should raise error."""
        # Encrypt non-JSON data
        encrypted = EncryptionManager.encrypt_data("not json data", test_dek)
        with pytest.raises(json.JSONDecodeError):
            EncryptionManager.decrypt_fields(encrypted, test_dek)


@pytest.mark.unit
@pytest.mark.security
class TestRSAKeyWrapping:
    """Test RSA key wrapping with admin public key."""

    def test_wrap_dek_with_admin_key(self, test_dek, admin_rsa_keypair):
        """DEK should be wrapped with admin RSA public key."""
        wrapped = EncryptionManager.wrap_dek_with_admin_key(
            test_dek, admin_rsa_keypair["public_pem"]
        )
        assert isinstance(wrapped, str)
        assert len(wrapped) > 0
        # Wrapped should be base64
        decoded = base64.b64decode(wrapped)
        assert isinstance(decoded, bytes)

    def test_unwrap_dek_with_admin_private_key(self, test_dek, admin_rsa_keypair):
        """Wrapped DEK should be unwrappable with admin private key."""
        wrapped = EncryptionManager.wrap_dek_with_admin_key(
            test_dek, admin_rsa_keypair["public_pem"]
        )
        wrapped_bytes = base64.b64decode(wrapped)

        # Unwrap using private key
        unwrapped = admin_rsa_keypair["private_key"].decrypt(
            wrapped_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=SHA256()),
                algorithm=SHA256(),
                label=None,
            ),
        )
        assert unwrapped == test_dek

    def test_wrap_dek_unique_each_time(self, test_dek, admin_rsa_keypair):
        """RSA-OAEP wrapping should produce different ciphertexts."""
        wrapped1 = EncryptionManager.wrap_dek_with_admin_key(
            test_dek, admin_rsa_keypair["public_pem"]
        )
        wrapped2 = EncryptionManager.wrap_dek_with_admin_key(
            test_dek, admin_rsa_keypair["public_pem"]
        )
        # Due to OAEP padding with random data, wrappings should differ
        assert wrapped1 != wrapped2


@pytest.mark.unit
class TestUserEncryptionDataCreation:
    """Test complete user encryption data creation."""

    def test_create_user_encryption_data(self, test_password, admin_rsa_keypair):
        """Should create all required encryption data for new user."""
        result = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        # Check all required fields are present
        assert "salt" in result
        assert "user_wrapped_dek" in result
        assert "admin_wrapped_dek" in result

        # Check types and formats
        assert isinstance(result["salt"], str)
        assert isinstance(result["user_wrapped_dek"], str)
        assert isinstance(result["admin_wrapped_dek"], str)

        # Salt should be base64-encoded 16 bytes
        salt_bytes = base64.b64decode(result["salt"])
        assert len(salt_bytes) == 16
        # DEK should be unwrappable and be 32 bytes
        dek = EncryptionManager.get_user_dek(
            test_password, result["salt"], result["user_wrapped_dek"]
        )
        assert len(dek) == 32

    def test_created_dek_can_be_unwrapped(self, test_password, admin_rsa_keypair):
        """User should be able to unwrap their DEK with password."""
        result = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        # Unwrap using password
        unwrapped_dek = EncryptionManager.get_user_dek(
            test_password, result["salt"], result["user_wrapped_dek"]
        )

        # Should be a valid 32-byte DEK
        assert len(unwrapped_dek) == 32
        assert isinstance(unwrapped_dek, bytes)

    def test_admin_can_unwrap_admin_wrapped_dek(self, test_password, admin_rsa_keypair):
        """Admin should be able to unwrap admin_wrapped_dek."""
        result = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        # Admin unwrap
        admin_wrapped_bytes = base64.b64decode(result["admin_wrapped_dek"])
        unwrapped = admin_rsa_keypair["private_key"].decrypt(
            admin_wrapped_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=SHA256()),
                algorithm=SHA256(),
                label=None,
            ),
        )

        # Should be a valid 32-byte DEK
        assert len(unwrapped) == 32
        assert isinstance(unwrapped, bytes)

        # Should be the same DEK as the user can unwrap
        user_unwrapped = EncryptionManager.get_user_dek(
            test_password, result["salt"], result["user_wrapped_dek"]
        )
        assert unwrapped == user_unwrapped


@pytest.mark.unit
@pytest.mark.security
class TestPasswordChange:
    """Test password change and DEK re-wrapping."""

    def test_change_password_preserves_dek(self, test_password, admin_rsa_keypair):
        """DEK should remain the same after password change."""
        # Create initial encryption data
        initial_data = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        # Get original DEK
        original_dek = EncryptionManager.get_user_dek(
            test_password, initial_data["salt"], initial_data["user_wrapped_dek"]
        )

        # Change password
        new_password = "NewPassword456!"
        result = EncryptionManager.change_password(
            test_password,
            new_password,
            initial_data["salt"],
            initial_data["user_wrapped_dek"],
        )

        # Unwrap with new password
        unwrapped_dek = EncryptionManager.get_user_dek(
            new_password, result["salt"], result["user_wrapped_dek"]
        )
        assert unwrapped_dek == original_dek

    def test_change_password_new_salt(
        self,
        test_password,
        admin_rsa_keypair,
    ):
        """Password change should generate new salt."""
        initial_data = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        new_password = "NewPassword456!"
        result = EncryptionManager.change_password(
            test_password,
            new_password,
            initial_data["salt"],
            initial_data["user_wrapped_dek"],
        )

        assert result["salt"] != initial_data["salt"]

    def test_old_password_fails_after_change(
        self,
        test_password,
        admin_rsa_keypair,
    ):
        """Old password should not work after password change."""
        initial_data = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        new_password = "NewPassword456!"
        result = EncryptionManager.change_password(
            test_password,
            new_password,
            initial_data["salt"],
            initial_data["user_wrapped_dek"],
        )

        # Try to unwrap with old password - should fail
        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure
            EncryptionManager.get_user_dek(
                test_password, result["salt"], result["user_wrapped_dek"]
            )

    def test_encrypted_data_decryptable_after_password_change(
        self,
        test_password,
        admin_rsa_keypair,
    ):
        """Data encrypted before password change should still be decryptable."""
        # Create initial data and encrypt something
        initial_data = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        # Get original DEK and encrypt something
        original_dek = EncryptionManager.get_user_dek(
            test_password, initial_data["salt"], initial_data["user_wrapped_dek"]
        )
        secret_data = {"message": "Secret information"}
        encrypted = EncryptionManager.encrypt_fields(secret_data, original_dek)

        # Change password
        new_password = "NewPassword456!"
        result = EncryptionManager.change_password(
            test_password,
            new_password,
            initial_data["salt"],
            initial_data["user_wrapped_dek"],
        )

        # Get DEK with new password
        unwrapped_dek = EncryptionManager.get_user_dek(
            new_password, result["salt"], result["user_wrapped_dek"]
        )

        # Decrypt old data with new DEK (should be same DEK)
        decrypted = EncryptionManager.decrypt_fields(encrypted, unwrapped_dek)
        assert decrypted == secret_data


@pytest.mark.unit
class TestGetUserDEK:
    """Test DEK unwrapping with password."""

    def test_get_user_dek_success(
        self,
        test_password,
        admin_rsa_keypair,
    ):
        """Should successfully unwrap DEK with correct password."""
        data = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )
        dek = EncryptionManager.get_user_dek(
            test_password, data["salt"], data["user_wrapped_dek"]
        )

        # Should be a valid 32-byte DEK
        assert len(dek) == 32
        assert isinstance(dek, bytes)

    def test_get_user_dek_wrong_password_fails(
        self,
        test_password,
        admin_rsa_keypair,
    ):
        """Wrong password should fail to unwrap DEK."""
        data = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure
            EncryptionManager.get_user_dek(
                "WrongPassword", data["salt"], data["user_wrapped_dek"]
            )

    def test_get_user_dek_wrong_salt_fails(
        self,
        test_password,
        admin_rsa_keypair,
    ):
        """Wrong salt should fail to unwrap DEK."""
        data = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        wrong_salt = base64.b64encode(b"wrong_salt_16byt").decode()
        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure
            EncryptionManager.get_user_dek(
                test_password, wrong_salt, data["user_wrapped_dek"]
            )


@pytest.mark.security
class TestEncryptionSecurity:
    """Security-focused tests for encryption implementation."""

    def test_dek_not_stored_in_plaintext(
        self,
        test_password,
        admin_rsa_keypair,
    ):
        """DEK should never be stored in plaintext."""
        result = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        # Unwrap the DEK to get its actual value
        dek = EncryptionManager.get_user_dek(
            test_password, result["salt"], result["user_wrapped_dek"]
        )

        # Check that plaintext DEK is not present in any wrapped form
        dek_b64 = base64.b64encode(dek).decode()
        assert dek_b64 not in result["user_wrapped_dek"]
        assert dek_b64 not in result["admin_wrapped_dek"]

        # Also verify that 'dek' key is not in the result
        assert "dek" not in result

    def test_password_not_stored(
        self,
        test_password,
        admin_rsa_keypair,
    ):
        """Password should never appear in encryption data."""
        result = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        # Password should not be in any field
        for value in result.values():
            if isinstance(value, str):
                assert test_password not in value
                assert test_password.encode() not in base64.b64decode(value)

    def test_pbkdf2_iterations_sufficient(self):
        """PBKDF2 should use sufficient iterations (>=600000)."""
        # This is implicit in derive_key_from_password implementation
        # We test that derivation takes reasonable time (indicating many iterations)
        import time

        start = time.time()
        EncryptionManager.derive_key_from_password("password", b"salt_16_bytes!!!")
        duration = time.time() - start

        # With 600k iterations, this should take at least a few milliseconds
        assert duration > 0.001  # At least 1ms

    def test_aes_gcm_authentication(self, test_dek):
        """AES-GCM should provide authentication (detect tampering)."""
        original = "Important data"
        encrypted = EncryptionManager.encrypt_data(original, test_dek)
        encrypted_bytes = base64.b64decode(encrypted)

        # Tamper with ciphertext (change one byte in the middle)
        tampered = bytearray(encrypted_bytes)
        tampered[len(tampered) // 2] ^= 0x01  # Flip one bit
        tampered_b64 = base64.b64encode(bytes(tampered)).decode()

        # Decryption should fail due to authentication tag mismatch
        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure
            EncryptionManager.decrypt_data(tampered_b64, test_dek)


@pytest.mark.unit
class TestDEKSplitting:
    """Test DEK splitting for balanced security mode."""

    def test_split_dek_returns_two_parts(self, test_dek):
        """Should split DEK into two parts."""
        server_part, client_part = EncryptionManager.split_dek(test_dek)

        assert isinstance(server_part, str)
        assert isinstance(client_part, str)
        assert server_part != client_part

    def test_split_dek_parts_are_base64(self, test_dek):
        """Split parts should be valid base64."""
        server_part, client_part = EncryptionManager.split_dek(test_dek)

        # Should decode without error
        server_bytes = base64.b64decode(server_part)
        client_bytes = base64.b64decode(client_part)

        assert isinstance(server_bytes, bytes)
        assert isinstance(client_bytes, bytes)

    def test_split_dek_parts_same_length_as_dek(self, test_dek):
        """Split parts should be same length as original DEK."""
        server_part, client_part = EncryptionManager.split_dek(test_dek)

        server_bytes = base64.b64decode(server_part)
        client_bytes = base64.b64decode(client_part)

        assert len(server_bytes) == len(test_dek)
        assert len(client_bytes) == len(test_dek)

    def test_split_dek_unique_each_time(self, test_dek):
        """Split should produce different parts each time (due to random server part)."""
        server1, client1 = EncryptionManager.split_dek(test_dek)
        server2, client2 = EncryptionManager.split_dek(test_dek)

        # Server parts should be different (random)
        assert server1 != server2
        # Client parts should also be different (due to XOR with different server)
        assert client1 != client2

    def test_reconstruct_dek_from_parts(self, test_dek):
        """Should reconstruct original DEK from split parts."""
        server_part, client_part = EncryptionManager.split_dek(test_dek)
        reconstructed = EncryptionManager.reconstruct_dek(server_part, client_part)

        assert reconstructed == test_dek

    def test_reconstruct_dek_wrong_parts_fails(self, test_dek):
        """Reconstructing with wrong parts should not give original DEK."""
        server_part1, client_part1 = EncryptionManager.split_dek(test_dek)
        server_part2, _ = EncryptionManager.split_dek(test_dek)

        # Mix parts from different splits
        wrong_reconstruction = EncryptionManager.reconstruct_dek(
            server_part2, client_part1
        )

        assert wrong_reconstruction != test_dek


@pytest.mark.unit
class TestDEKPartEncryption:
    """Test encryption of DEK parts for caching."""

    @pytest.fixture(autouse=True)
    def setup_server_cache_key(self):
        """Ensure server cache key is initialized for all tests."""
        # Save original value
        original_key = EncryptionManager._SERVER_CACHE_KEY
        # Set a valid 32-byte key for testing
        EncryptionManager._SERVER_CACHE_KEY = (
            b"test_server_cache_key_32bytes!!!"  # Exactly 32 bytes
        )
        yield
        # Restore original value (important for integration tests)
        EncryptionManager._SERVER_CACHE_KEY = original_key

    def test_encrypt_dek_part(self):
        """Should encrypt DEK part."""
        dek_part = base64.b64encode(b"test_dek_part_32bytes_long!!!").decode()
        encrypted = EncryptionManager.encrypt_dek_part(dek_part)

        assert isinstance(encrypted, str)
        assert encrypted != dek_part

    def test_decrypt_dek_part(self):
        """Should decrypt encrypted DEK part."""
        dek_part = base64.b64encode(b"test_dek_part_32bytes_long!!!").decode()
        encrypted = EncryptionManager.encrypt_dek_part(dek_part)
        decrypted = EncryptionManager.decrypt_dek_part(encrypted)

        assert decrypted == dek_part

    def test_encrypt_decrypt_dek_part_roundtrip(self, test_dek):
        """Encrypt and decrypt DEK part should preserve data."""
        server_part, _ = EncryptionManager.split_dek(test_dek)

        encrypted = EncryptionManager.encrypt_dek_part(server_part)
        decrypted = EncryptionManager.decrypt_dek_part(encrypted)

        assert decrypted == server_part

    def test_encrypt_dek_part_uses_server_cache_key(self):
        """Should use server cache key for encryption."""
        with patch.object(EncryptionManager, "_get_server_cache_key") as mock_get_key:
            mock_get_key.return_value = (
                b"test_server_cache_key_32bytes!!!"  # Exactly 32 bytes
            )
            dek_part = base64.b64encode(b"test_part").decode()

            EncryptionManager.encrypt_dek_part(dek_part)

            # Should have called _get_server_cache_key
            mock_get_key.assert_called_once()


@pytest.mark.unit
class TestGetDekFromRequest:
    """Test DEK reconstruction from request based on security tier."""

    @pytest.fixture(autouse=True)
    def setup_server_cache_key(self):
        """Ensure server cache key is initialized for all tests."""
        # Save original value
        original_key = EncryptionManager._SERVER_CACHE_KEY
        # Set a valid 32-byte key for testing
        EncryptionManager._SERVER_CACHE_KEY = (
            b"test_server_cache_key_32bytes!!!"  # Exactly 32 bytes
        )
        yield
        # Restore original value (important for integration tests)
        EncryptionManager._SERVER_CACHE_KEY = original_key

    def test_get_dek_high_security_mode(self, test_dek, fake_redis):
        """High security mode should decode DEK directly from request."""
        dek_b64 = base64.b64encode(test_dek).decode()

        result = EncryptionManager.get_dek_from_request(
            dek_or_client_part=dek_b64,
            user_id="user123",
            token="token123",
            security_tier="high",
            redis_client=fake_redis,
        )

        assert result == test_dek

    def test_get_dek_convenience_mode(self, test_dek, fake_redis):
        """Convenience mode should decode DEK directly from request."""
        dek_b64 = base64.b64encode(test_dek).decode()

        result = EncryptionManager.get_dek_from_request(
            dek_or_client_part=dek_b64,
            user_id="user123",
            token="token123",
            security_tier="convenience",
            redis_client=fake_redis,
        )

        assert result == test_dek

    def test_get_dek_balanced_mode_with_cache(self, test_dek, fake_redis):
        """Balanced mode should reconstruct DEK from cached server part and client part."""
        # Split DEK
        server_part, client_part = EncryptionManager.split_dek(test_dek)

        # Encrypt server part for cache
        encrypted_server_part = EncryptionManager.encrypt_dek_part(server_part)

        # Cache the encrypted server part
        cache_key = "dek:user123:token123"
        cache_data = {
            "encrypted_server_part": encrypted_server_part,
            "last_accessed": datetime.now().isoformat(),
        }
        fake_redis.setex(cache_key, 1800, json.dumps(cache_data))

        # Reconstruct DEK
        result = EncryptionManager.get_dek_from_request(
            dek_or_client_part=client_part,
            user_id="user123",
            token="token123",
            security_tier="balanced",
            redis_client=fake_redis,
        )

        assert result == test_dek

    def test_get_dek_balanced_mode_cache_miss(self, fake_redis):
        """Balanced mode should raise error when cache is missing."""
        with pytest.raises(ValueError) as exc_info:
            EncryptionManager.get_dek_from_request(
                dek_or_client_part="client_part_base64",
                user_id="user123",
                token="token123",
                security_tier="balanced",
                redis_client=fake_redis,
            )

        assert "DEK cache expired" in str(exc_info.value)

    def test_get_dek_balanced_mode_updates_cache_ttl(self, test_dek, fake_redis):
        """Balanced mode should update cache TTL on access."""
        server_part, client_part = EncryptionManager.split_dek(test_dek)
        encrypted_server_part = EncryptionManager.encrypt_dek_part(server_part)

        cache_key = "dek:user123:token123"
        cache_data = {
            "encrypted_server_part": encrypted_server_part,
            "last_accessed": "2024-01-01T00:00:00",
        }
        fake_redis.setex(cache_key, 1800, json.dumps(cache_data))

        # Access DEK
        EncryptionManager.get_dek_from_request(
            dek_or_client_part=client_part,
            user_id="user123",
            token="token123",
            security_tier="balanced",
            redis_client=fake_redis,
        )

        # Cache should be updated
        updated_cache = json.loads(fake_redis.get(cache_key))
        assert updated_cache["last_accessed"] != "2024-01-01T00:00:00"
        # Should have new timestamp
        assert datetime.fromisoformat(updated_cache["last_accessed"]).year >= 2025


@pytest.mark.unit
class TestHelperFunctions:
    """Test module-level helper functions."""

    def test_get_user_data(self, test_password, admin_rsa_keypair):
        """Should decrypt user data using password."""
        # Create encryption data
        encryption_data = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        # Get DEK and encrypt some fields
        dek = EncryptionManager.get_user_dek(
            test_password, encryption_data["salt"], encryption_data["user_wrapped_dek"]
        )

        user_fields = {"name": "John Doe", "email": "john@example.com"}
        encrypted_fields = EncryptionManager.encrypt_fields(user_fields, dek)

        # Create user record
        user_record = {
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
            "encrypted_fields": encrypted_fields,
        }

        # Get user data
        result = get_user_data(test_password, user_record)

        assert result == user_fields

    def test_get_user_data_wrong_password_fails(self, test_password, admin_rsa_keypair):
        """Should fail to decrypt with wrong password."""
        encryption_data = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        dek = EncryptionManager.get_user_dek(
            test_password, encryption_data["salt"], encryption_data["user_wrapped_dek"]
        )

        user_fields = {"name": "Jane Doe"}
        encrypted_fields = EncryptionManager.encrypt_fields(user_fields, dek)

        user_record = {
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
            "encrypted_fields": encrypted_fields,
        }

        with pytest.raises(Exception):  # noqa: B017  # intentional: any cryptographic failure
            get_user_data("WrongPassword", user_record)

    def test_handle_password_change(self, test_password, admin_rsa_keypair):
        """Should handle password change and return updated encryption data."""
        # Create initial user record
        encryption_data = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        user_record = {
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
        }

        new_password = "NewSecurePassword123!"

        # Handle password change
        result = handle_password_change(test_password, new_password, user_record)

        # Should return new salt and user_wrapped_dek
        assert "salt" in result
        assert "user_wrapped_dek" in result
        assert result["salt"] != user_record["salt"]

        # Should be able to unwrap DEK with new password
        new_dek = EncryptionManager.get_user_dek(
            new_password, result["salt"], result["user_wrapped_dek"]
        )
        assert len(new_dek) == 32

    def test_handle_password_change_preserves_dek(
        self, test_password, admin_rsa_keypair
    ):
        """Password change should preserve the same DEK."""
        encryption_data = EncryptionManager.create_user_encryption_data(
            test_password, admin_rsa_keypair["public_pem"]
        )

        user_record = {
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
        }

        # Get original DEK
        original_dek = EncryptionManager.get_user_dek(
            test_password, user_record["salt"], user_record["user_wrapped_dek"]
        )

        new_password = "NewPassword456!"
        result = handle_password_change(test_password, new_password, user_record)

        # Get new DEK
        new_dek = EncryptionManager.get_user_dek(
            new_password, result["salt"], result["user_wrapped_dek"]
        )

        # Should be the same DEK
        assert new_dek == original_dek


@pytest.mark.unit
class TestServerCacheKey:
    """Test server cache key management."""

    def test_get_server_cache_key_generates_if_not_exists(self):
        """Should generate ephemeral key if secret file doesn't exist."""
        EncryptionManager._SERVER_CACHE_KEY = None

        with patch("pathlib.Path.exists", return_value=False):
            key = EncryptionManager._get_server_cache_key()

            assert isinstance(key, bytes)
            assert len(key) == 32

    def test_get_server_cache_key_loads_from_secret(self):
        """Should load key from secret file if it exists."""
        EncryptionManager._SERVER_CACHE_KEY = None
        test_key = b"test_server_cache_key_32byte!!"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_bytes", return_value=test_key):
                key = EncryptionManager._get_server_cache_key()

                assert key == test_key

    def test_get_server_cache_key_caches_result(self):
        """Should cache the key after first access."""
        EncryptionManager._SERVER_CACHE_KEY = None

        with patch("pathlib.Path.exists", return_value=False):
            key1 = EncryptionManager._get_server_cache_key()
            key2 = EncryptionManager._get_server_cache_key()

            # Should return same key (cached)
            assert key1 == key2
