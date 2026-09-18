from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.utils.security import decode_access_token


bearer_scheme = HTTPBearer()


async def get_current_empresa_id(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    )
) -> str:

    token = credentials.credentials

    id_empresa = decode_access_token(token)

    if id_empresa is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    return id_empresa