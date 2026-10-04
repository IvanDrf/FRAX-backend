from contextlib import asynccontextmanager

from fastapi import FastAPI
from uvicorn import run

from api.risk_factors import risk_factor_router
from api.users import user_router
from db.minio import minio_client


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await minio_client.close_session()


app = FastAPI(lifespan=lifespan)
app.include_router(risk_factor_router)
app.include_router(user_router)


if __name__ == "__main__":
    run(app, host="localhost", port=8080)
