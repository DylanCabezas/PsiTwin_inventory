from datetime import (
    datetime,
    timedelta,
    timezone
)

import jwt

from pwdlib import PasswordHash

from app.config.settings import (
    settings
)


password_hasher = PasswordHash.recommended()


def hash_password(
    password: str
) -> str:

    return password_hasher.hash(
        password
    )


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    try:

        return password_hasher.verify(
            plain_password,
            hashed_password
        )

    except Exception:

        return False


def create_access_token(
    id_empresa: str
) -> str:

    expiration = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": id_empresa,
        "exp": expiration
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(
    token: str
) -> str | None:

    try:

        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[
                settings.JWT_ALGORITHM
            ]
        )

        id_empresa = payload.get(
            "sub"
        )

        if id_empresa is None:
            return None

        return str(
            id_empresa
        )

    except jwt.InvalidTokenError:

        return None