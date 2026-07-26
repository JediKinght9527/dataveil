"""
Vault encryption: Argon2id + AES-256-GCM
"""

import secrets

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class VaultCrypto:
    """Encrypt/decrypt arbitrary bytes with a user password."""

    SALT_LEN = 16
    NONCE_LEN = 12
    KEY_LEN = 32
    TIME_COST = 3
    MEMORY_COST = 65536
    PARALLELISM = 4

    @classmethod
    def derive_key(cls, password: str, salt: bytes) -> bytes:
        return hash_secret_raw(
            secret=password.encode(),
            salt=salt,
            time_cost=cls.TIME_COST,
            memory_cost=cls.MEMORY_COST,
            parallelism=cls.PARALLELISM,
            hash_len=cls.KEY_LEN,
            type=Type.ID,
        )

    @classmethod
    def encrypt(cls, plaintext: bytes, password: str) -> bytes:
        salt = secrets.token_bytes(cls.SALT_LEN)
        nonce = secrets.token_bytes(cls.NONCE_LEN)
        key = cls.derive_key(password, salt)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
        return salt + nonce + ciphertext

    @classmethod
    def decrypt(cls, token: bytes, password: str) -> bytes:
        salt = token[: cls.SALT_LEN]
        nonce = token[cls.SALT_LEN : cls.SALT_LEN + cls.NONCE_LEN]
        ciphertext = token[cls.SALT_LEN + cls.NONCE_LEN :]
        key = cls.derive_key(password, salt)
        return AESGCM(key).decrypt(nonce, ciphertext, None)
