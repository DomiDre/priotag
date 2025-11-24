"""Field-level encryption system allowing for password changes by using data encryption keys"""

import base64
import datetime
import json
import os
from pathlib import Path
from typing import Any, Literal

import redis
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionManager:
    """Manages field-level encryption for sensitive user data."""

    KDF_ITERATIONS = 600000
    KEY_SIZE = 32

    # Server-side key for encrypting cached DEK parts (balanced mode)
    # In production, this should be loaded from a secure location
    _SERVER_CACHE_KEY: bytes | None = None

    @classmethod
    def _get_server_cache_key(cls) -> bytes:
        """Get or generate server-side key for encrypting cached DEK parts."""
        if cls._SERVER_CACHE_KEY is None:
            # Try to load from environment or secrets
            cache_key_path = Path("/run/secrets/server_cache_key")
            if cache_key_path.exists():
                cls._SERVER_CACHE_KEY = cache_key_path.read_bytes().strip()
            else:
                # Fallback: generate ephemeral key (lost on restart - acceptable for cache)
                cls._SERVER_CACHE_KEY = AESGCM.generate_key(bit_length=256)
        return cls._SERVER_CACHE_KEY

    @staticmethod
    def generate_dek() -> bytes:
        """Generate a new Data Encryption Key (DEK) for a user."""
        return AESGCM.generate_key(bit_length=256)

    @staticmethod
    def derive_key_from_password(password: str, salt: bytes) -> bytes:
        """
        Derive an encryption key from a password using PBKDF2.

        Args:
            password: User's password
            salt: Unique salt for this user (store in PocketBase)

        Returns:
            32-byte encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=EncryptionManager.KEY_SIZE,
            salt=salt,
            iterations=EncryptionManager.KDF_ITERATIONS,
            backend=default_backend(),
        )
        return kdf.derive(password.encode())

    @staticmethod
    def encrypt_data(data: str, key: bytes) -> str:
        """
        Encrypt data using AES-GCM.

        Args:
            data: Plaintext string to encrypt
            key: 32-byte encryption key

        Returns:
            Base64-encoded: nonce + ciphertext + tag
        """
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 96 bits for GCM
        ciphertext = aesgcm.encrypt(nonce, data.encode(), None)

        # Combine nonce + ciphertext and encode
        encrypted = nonce + ciphertext
        return base64.b64encode(encrypted).decode()

    @staticmethod
    def decrypt_data(encrypted_data: str, key: bytes) -> str:
        """
        Decrypt data using AES-GCM.

        Args:
            encrypted_data: Base64-encoded encrypted data
            key: 32-byte decryption key

        Returns:
            Decrypted plaintext string
        """
        encrypted = base64.b64decode(encrypted_data)
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode()

    @staticmethod
    def _load_admin_public_key(admin_public_key_pem: bytes) -> RSAPublicKey:
        """
        Load admin's RSA public key from PEM bytes.

        Args:
            admin_public_key_pem: Institution's admin public key in PEM format

        Returns:
            RSA public key object
        """
        public_key = serialization.load_pem_public_key(
            admin_public_key_pem, backend=default_backend()
        )
        # Type check and cast
        if not isinstance(public_key, RSAPublicKey):
            raise TypeError(f"Expected RSA public key, got {type(public_key)}")

        return public_key

    @staticmethod
    def wrap_dek_with_admin_key(dek: bytes, admin_public_key_pem: bytes) -> str:
        """
        Wrap DEK with admin's PUBLIC key.
        Server can do this, but CANNOT unwrap!

        Args:
            dek: Data encryption key to wrap
            admin_public_key_pem: Institution's admin public key in PEM format

        Returns:
            Base64-encoded wrapped DEK
        """
        public_key = EncryptionManager._load_admin_public_key(admin_public_key_pem)

        encrypted_dek = public_key.encrypt(
            dek,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        return base64.b64encode(encrypted_dek).decode()

    @classmethod
    def create_user_encryption_data(
        cls, password: str, admin_public_key_pem: bytes
    ) -> dict[str, str]:
        """
        Create encryption data for a new user.

        Args:
            password: User's password
            admin_public_key_pem: Institution's admin public key in PEM format

        Returns:
            Dictionary with keys to store in PocketBase:
            - salt: Base64-encoded salt for password KDF
            - user_wrapped_dek: DEK encrypted with user's password-derived key
            - admin_wrapped_dek: DEK encrypted with institution's admin key
        """
        # Generate salt and DEK
        salt = os.urandom(16)
        dek = cls.generate_dek()

        # Derive key from password
        password_key = cls.derive_key_from_password(password, salt)

        # Encrypt DEK with password-derived key
        user_wrapped_dek = cls.encrypt_data(
            base64.b64encode(dek).decode(), password_key
        )

        # Encrypt DEK with institution's admin public key for external decryption
        admin_wrapped_dek = cls.wrap_dek_with_admin_key(dek, admin_public_key_pem)

        return {
            "salt": base64.b64encode(salt).decode(),
            "user_wrapped_dek": user_wrapped_dek,
            "admin_wrapped_dek": admin_wrapped_dek,
        }

    @classmethod
    def get_user_dek(cls, password: str, salt: str, user_wrapped_dek: str) -> bytes:
        """
        Retrieve user's DEK using their password.

        Args:
            password: User's password
            salt: Base64-encoded salt from PocketBase
            user_wrapped_dek: Encrypted DEK from PocketBase

        Returns:
            Decrypted DEK (32 bytes)
        """
        salt_bytes = base64.b64decode(salt)
        password_key = cls.derive_key_from_password(password, salt_bytes)
        dek_b64 = cls.decrypt_data(user_wrapped_dek, password_key)
        return base64.b64decode(dek_b64)

    @classmethod
    def encrypt_fields(cls, fields: dict[str, Any], dek: bytes) -> str:
        """
        Encrypt multiple fields into a single JSON string.

        Args:
            fields: Dictionary of field_name -> value to encrypt
            dek: Data Encryption Key

        Returns:
            Base64-encoded encrypted JSON
        """
        json_data = json.dumps(fields)
        return cls.encrypt_data(json_data, dek)

    @classmethod
    def decrypt_fields(cls, encrypted_json: str, dek: bytes) -> dict[str, Any]:
        """
        Decrypt fields from encrypted JSON string.

        Args:
            encrypted_json: Base64-encoded encrypted JSON
            dek: Data Encryption Key

        Returns:
            Dictionary of decrypted fields
        """
        json_data = cls.decrypt_data(encrypted_json, dek)
        return json.loads(json_data)

    @classmethod
    def change_password(
        cls, old_password: str, new_password: str, salt: str, user_wrapped_dek: str
    ) -> dict[str, str]:
        """
        Handle password change by re-wrapping the DEK.

        Args:
            old_password: User's current password
            new_password: User's new password
            salt: Base64-encoded salt from PocketBase
            user_wrapped_dek: Current encrypted DEK

        Returns:
            Dictionary with updated encryption data:
            - salt: New salt
            - user_wrapped_dek: DEK re-encrypted with new password
        """
        # Decrypt DEK with old password
        dek = cls.get_user_dek(old_password, salt, user_wrapped_dek)

        # Generate new salt and derive new key
        new_salt = os.urandom(16)
        new_password_key = cls.derive_key_from_password(new_password, new_salt)

        # Re-encrypt DEK with new password-derived key
        new_user_wrapped_dek = cls.encrypt_data(
            base64.b64encode(dek).decode(), new_password_key
        )

        return {
            "salt": base64.b64encode(new_salt).decode(),
            "user_wrapped_dek": new_user_wrapped_dek,
            # Note: admin_wrapped_dek stays the same!
        }

    @staticmethod
    def split_dek(dek: bytes) -> tuple[str, str]:
        """Split DEK into two parts using XOR for balanced security mode.

        Args:
            dek: Raw DEK bytes (32 bytes)

        Returns:
            tuple: (server_part_b64, client_part_b64) - both base64 encoded
        """
        # Generate random server part (same length as DEK)
        server_part_bytes = os.urandom(len(dek))

        # XOR to create client part
        client_part_bytes = bytes(
            a ^ b for a, b in zip(dek, server_part_bytes, strict=False)
        )

        return (
            base64.b64encode(server_part_bytes).decode("utf-8"),
            base64.b64encode(client_part_bytes).decode("utf-8"),
        )

    @classmethod
    def encrypt_dek_part(cls, dek_part: str) -> str:
        """Encrypt a DEK part before caching using server-side key.

        Args:
            dek_part: Base64-encoded DEK part

        Returns:
            Base64-encoded encrypted DEK part
        """
        server_key = cls._get_server_cache_key()
        return cls.encrypt_data(dek_part, server_key)

    @classmethod
    def decrypt_dek_part(cls, encrypted_dek_part: str) -> str:
        """Decrypt a cached DEK part using server-side key.

        Args:
            encrypted_dek_part: Base64-encoded encrypted DEK part

        Returns:
            Base64-encoded DEK part
        """
        server_key = cls._get_server_cache_key()
        return cls.decrypt_data(encrypted_dek_part, server_key)

    @staticmethod
    def reconstruct_dek(server_part: str, client_part: str) -> bytes:
        """Reconstruct DEK from split parts (balanced mode).

        Args:
            server_part: Base64 encoded server part
            client_part: Base64 encoded client part

        Returns:
            Reconstructed DEK as raw bytes (32 bytes)
        """
        server_bytes = base64.b64decode(server_part)
        client_bytes = base64.b64decode(client_part)

        # XOR to reconstruct original DEK
        dek_bytes = bytes(
            a ^ b for a, b in zip(server_bytes, client_bytes, strict=False)
        )

        return dek_bytes

    @classmethod
    def get_dek_from_request(
        cls,
        dek_or_client_part: str,
        user_id: str,
        token: str,
        security_tier: Literal["high", "balanced", "convenience"],
        redis_client: redis.Redis,
    ) -> bytes:
        """Reconstruct DEK from request data based on security tier.

        Args:
            dek_or_client_part: Either full DEK (base64) or client key part (base64)
            user_id: User ID for cache lookup
            token: Session token for cache lookup
            security_tier: User's security tier
            redis_client: Redis client for cache access

        Returns:
            Reconstructed DEK as bytes

        Raises:
            ValueError: If DEK cannot be reconstructed
        """
        if security_tier == "balanced":
            # Need to reconstruct from split parts
            dek_cache_key = f"dek:{user_id}:{token}"
            cached_data = redis_client.get(dek_cache_key)

            if not cached_data:
                raise ValueError(
                    "DEK cache expired or not found. Please re-authenticate."
                )

            cache_info = json.loads(str(cached_data))
            encrypted_server_part = cache_info["encrypted_server_part"]

            # Decrypt server part
            server_part = cls.decrypt_dek_part(encrypted_server_part)

            # Reconstruct DEK from both parts
            dek = cls.reconstruct_dek(server_part, dek_or_client_part)

            # Update last accessed time and refresh TTL
            cache_info["last_accessed"] = datetime.datetime.now().isoformat()
            redis_client.setex(dek_cache_key, 1800, json.dumps(cache_info))

            return dek
        else:
            # High or convenience mode: full DEK provided
            return base64.b64decode(dek_or_client_part)


def get_user_data(password: str, user_record: dict[str, Any]) -> dict[str, Any]:
    """
    Retrieve and decrypt user data.

    This would be called when a user logs in or accesses their data.
    """
    # Get DEK using user's password
    dek = EncryptionManager.get_user_dek(
        password, user_record["salt"], user_record["user_wrapped_dek"]
    )

    # Decrypt fields
    decrypted_fields = EncryptionManager.decrypt_fields(
        user_record["encrypted_fields"], dek
    )

    return decrypted_fields


def handle_password_change(
    old_password: str, new_password: str, user_record: dict[str, Any]
) -> dict[str, str]:
    """
    Handle user password change.

    Returns updated encryption data to store in PocketBase.
    """
    updated_data = EncryptionManager.change_password(
        old_password, new_password, user_record["salt"], user_record["user_wrapped_dek"]
    )

    return updated_data
