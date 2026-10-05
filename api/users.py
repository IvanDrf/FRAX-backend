from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


@user_router.post("/users/login")
async def login_user():
    pass


@user_router.post("/users/logout")
async def logout_user():
    pass
