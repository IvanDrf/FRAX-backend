from typing import Final

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from uvicorn import run

from api.risk_factors import risk_factor_router

STATIC_PATH: Final[str] = "./static"

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")
app.include_router(risk_factor_router)


if __name__ == "__main__":
    run(app, host="localhost", port=8080)
