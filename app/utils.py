import hashlib, secrets
from datetime import datetime, timedelta

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def token_hex(n=32):
    return secrets.token_hex(n)

def now():
    return datetime.utcnow()

def in_minutes(m: int):
    return now() + timedelta(minutes=m)
