from fastapi import APIRouter

user_router = APIRouter(prefix="/api", tags=["users"])


@user_router.post("/users/register")
async def register_user():
    pass


@user_router.post("/users/login")
async def login_user():
    pass


@user_router.post("/users/logout")
async def logout_user():
    pass
