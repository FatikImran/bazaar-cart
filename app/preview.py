"""Serve the actual storefront and API from one origin for local preview."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.main import app as api
from app.main import lifespan

app = FastAPI(lifespan=lifespan)
app.mount("/api", api)
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[1] / "web", html=True))
