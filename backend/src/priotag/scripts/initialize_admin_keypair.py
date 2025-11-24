"""Initialize private / public key pair for an institution and secure private key with admin password.

This script generates an RSA keypair for institution administrators:
- Public key: Stored in the institution record in PocketBase, used by the server to encrypt user DEKs
- Private key: Stored securely by the institution admin (NOT on the server), used to decrypt user data if needed

Usage:
    python -m priotag.scripts.initialize_admin_keypair

The generated public key should be provided when creating a new institution via create_institution.py
"""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_admin_keypair():
    # Generate RSA keypair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )

    # Get admin passphrase for private key encryption
    passphrase = input("Enter passphrase to protect admin private key: ").encode()

    # Serialize private key (encrypted with passphrase)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(passphrase),
    )

    # Serialize public key (no encryption needed)
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Save keys
    with open("admin_private_key.pem", "wb") as f:
        f.write(private_pem)
    print("✓ Private key saved to admin_private_key.pem")
    print(
        "  Store this securely - NOT on the server! Admin needs it to decrypt user data."
    )

    with open("admin_public_key.pem", "wb") as f:
        f.write(public_pem)
    print("✓ Public key saved to admin_public_key.pem")
    print("  Provide this when creating the institution (stored in institution record)")


if __name__ == "__main__":
    generate_admin_keypair()
