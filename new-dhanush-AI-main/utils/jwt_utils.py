# utils/jwt_utils.py

import jwt
from datetime import datetime, timedelta
from flask import current_app, session

# Generate JWT token
def generate_token(payload, expires_in=3600):
    """
    Generate a JWT token with expiration (default: 1 hour)
    """
    payload["exp"] = datetime.utcnow() + timedelta(seconds=expires_in)
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
    return token


# Decode and validate JWT
def decode_token(token):
    """
    Decode JWT token and return payload if valid
    """
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# Optional: Extract token from Flask session (used by your logger)
def decode_jwt_from_session():
    token = session.get("jwt_token")
    if not token:
        return None
    return decode_token(token)

