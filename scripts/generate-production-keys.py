#!/usr/bin/env python3
"""Generate secure random keys for production deployment.

This script generates:
1. Database password (32 bytes, URL-safe)
2. Encryption key (32 bytes hex for AES-256)
3. Secret key (64 bytes hex for Flask sessions)

Usage:
    python scripts/generate-production-keys.py
"""

import secrets


def generate_keys() -> None:
    """Generate all required production keys and display them."""
    separator = "=" * 80

    print(separator)
    print("PRODUCTION SECURITY KEYS")
    print(separator)
    print()
    print("IMPORTANT: Store these keys securely!")
    print("- Add them to your .env file")
    print("- DO NOT commit them to version control")
    print("- Keep backups in a secure location (password manager, vault)")
    print()
    print(separator)
    print()

    # Generate database password (32 bytes URL-safe)
    db_password = secrets.token_urlsafe(32)
    print("1. DATABASE PASSWORD (DB_PASSWORD):")
    print(f"   {db_password}")
    print()

    # Generate encryption key (32 bytes = 64 hex characters for AES-256)
    encryption_key = secrets.token_hex(32)
    print("2. ENCRYPTION KEY (ENCRYPTION_KEY):")
    print(f"   {encryption_key}")
    print()

    # Generate secret key (64 bytes = 128 hex characters for Flask sessions)
    secret_key = secrets.token_hex(64)
    print("3. SECRET KEY (SECRET_KEY):")
    print(f"   {secret_key}")
    print()

    print(separator)
    print()
    print("NEXT STEPS:")
    print("1. Copy .env.production to .env")
    print("2. Replace the CHANGE_ME placeholders with the keys above")
    print("3. Update DATABASE_URL with the DB_PASSWORD")
    print("4. Review and configure other settings (HTTPS, AWS, etc.)")
    print("5. Restart services: docker compose down && docker compose up -d")
    print()
    print(separator)


if __name__ == "__main__":
    generate_keys()
