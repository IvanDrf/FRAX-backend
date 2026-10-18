from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from redis.asyncio import Redis
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.redis import get_redis_client
from db.session import get_db
from models.user import User
from schemas import UserSchema

user_router = APIRouter(prefix="/api", tags=["users"])


@user_router.post("/users/register", status_code=status.HTTP_201_CREATED)
async def register_user(session: Annotated[AsyncSession, Depends(get_db)], user: UserSchema):
    stmt = select(User).where(User.username == user.username)

    res = await session.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="пользователь с таким именем уже существует")

    u = User(username=user.username, password=user.password)
    session.add(u)
    await session.commit()


SESSION_EXP = 15 * 60


@user_router.post("/users/login", status_code=status.HTTP_204_NO_CONTENT)
async def login_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    user: UserSchema,
    response: Response,
):
    stmt = select(User).where(and_(User.username == user.username, User.password == user.password))

    res = await session.execute(stmt)
    u = res.scalar_one_or_none()
    if u is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="неправильный логин или пароль")

    session_id = str(uuid4())
    await redis.setex(f"session:{session_id}", SESSION_EXP, u.id)

    response.set_cookie(key="session_id", value=session_id, max_age=SESSION_EXP, secure=False, httponly=True)


@user_router.post("/users/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(redis: Annotated[Redis, Depends(get_redis_client)], session_id: Annotated[str, Cookie()], response: Response):
    user_id = await redis.get(session_id)

    if user_id:
        await redis.delete(session_id)

    response.delete_cookie(key="session_id")
