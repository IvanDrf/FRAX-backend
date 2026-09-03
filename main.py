from typing import Final

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from uvicorn import run

STATIC_PATH: Final[str] = "../FRAX-frontend/static"

app = FastAPI()
app.mount(STATIC_PATH, StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    run(app, host="localhost", port=8080)
