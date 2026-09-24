import os
from uuid import UUID

import jwt
from fastapi import Header, HTTPException


def actor_id(authorization: str = Header(default="")) -> UUID:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sessão inválida. Entre novamente.")
    token = authorization[7:]
    try:
        if os.environ.get("APP_ENV") == "local":
            key = os.environ["LOCAL_JWT_SECRET"]
            algorithms = ["HS256"]
        else:
            key = jwt.PyJWKClient(os.environ["JWT_JWKS_URL"]).get_signing_key_from_jwt(token).key
            algorithms = ["RS256", "ES256"]
        claims = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience="authenticated",
            issuer=os.environ["JWT_ISSUER"],
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
        return UUID(claims["sub"])
    except jwt.PyJWTError, ValueError, KeyError:
        raise HTTPException(401, "Sessão inválida. Entre novamente.") from None
