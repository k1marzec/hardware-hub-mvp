"""Password hashing helpers.

Uses passlib's bcrypt backend so passwords are never stored in plaintext.
This is the only piece of "real" security in the MVP — login now performs
an actual hash comparison against the `users` table instead of the previous
mock/no-account fallback.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
