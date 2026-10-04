import base64
import hashlib
import hmac
import os
import time

import jwt

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60

if SECRET_KEY == "dev-only-change-me":
    print("WARNING: using the default SECRET_KEY. Set SECRET_KEY before deploying.")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, digest_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except ValueError:
        return False
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return hmac.compare_digest(digest, expected)


def create_token(user_id: int, role: str) -> str:
    payload = {"sub": str(user_id), "role": role, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
