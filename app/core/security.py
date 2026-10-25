
import os

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    secret = os.getenv("JWT_SECRET")

    if not secret:
        raise HTTPException(
            status_code=500,
            detail="JWT_SECRET is not configured",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            secret,
            algorithms=["HS256"],
        )

        user_id = payload.get("sub")
        organization_id = payload.get("organization_id")
        username = payload.get("username")

        if (
            not user_id
            or not isinstance(organization_id, int)
            or organization_id <= 0
            or not username
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "user_id": int(user_id),
            "organization_id": organization_id,
            "username": username,
            "role": payload.get("role"),
        }

    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
