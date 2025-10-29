from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from config.config import Config

def hash_password(password: str) -> str:
    return generate_password_hash(password)

def verify_password(hash_pw: str, password: str) -> bool:
    return check_password_hash(hash_pw, password)

def generate_jwt(payload: dict) -> str:
    now = datetime.utcnow()
    exp = now + timedelta(seconds=Config.JWT_EXP_DELTA_SECONDS)
    payload_copy = payload.copy()
    payload_copy.update({"iat": now, "exp": exp})
    token = jwt.encode(payload_copy, Config.JWT_SECRET_KEY, algorithm="HS256")
    # PyJWT returns str in v2+
    return token

def decode_jwt(token: str) -> dict:
    try:
        data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
        return data
    except Exception:
        return None
