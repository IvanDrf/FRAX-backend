from typing import Final

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from uvicorn import run

from api.frax_handlers import frax_router

STATIC_PATH: Final[str] = "../FRAX-frontend/static"

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")
app.include_router(frax_router)


if __name__ == "__main__":
    run(app, host="localhost", port=8080)
