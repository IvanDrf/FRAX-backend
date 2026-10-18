from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Security, status
from fastapi.security import APIKeyCookie
from redis.asyncio import Redis

from db.redis import get_redis_client

SessionCookie = APIKeyCookie(name="session_id", auto_error=False)


async def strict_auth_middleware(session_id: Annotated[str, Security(SessionCookie)], redis: Annotated[Redis, Depends(get_redis_client)]):
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="не авторизован")

    user_id = await redis.get(f"session:{session_id}")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="не авторизован")

    try:
        return int(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="невалидное user_id")


async def auth_middleware(redis: Annotated[Redis, Depends(get_redis_client)], session_id: Annotated[str | None, Cookie()] = None):
    if not session_id:
        return None

    user_id = await redis.get(f"session:{session_id}")
    if not user_id:
        return None

    try:
        return int(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="невалидное user_id")
