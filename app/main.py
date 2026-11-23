from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

from anthropic import APIError
from fastapi import Body, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Error as DatabaseError
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from app.agent import BudgetExhausted, build_graph
from app.database import database, initialize, seed, seller_tokens

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.environ.get("DATABASE_URL"):
        initialize()
        seed()
    yield


app = FastAPI(title="BazaarCart", lifespan=lifespan)
origins = [origin.strip() for origin in os.environ.get("FRONTEND_ORIGINS", "").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                   allow_headers=["Authorization", "Content-Type", "X-Store"])

Identifier = Annotated[str, StringConstraints(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")]
Store = Annotated[str, Header(alias="X-Store", min_length=1, max_length=48, pattern=r"^[a-z0-9-]+$")]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: Identifier
    thread_id: Identifier
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]


class ChatReply(BaseModel):
    reply: str
    tool_calls: list[dict]
    tokens: dict[str, int]


class Product(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    sku: Annotated[str, StringConstraints(min_length=1, max_length=48, pattern=r"^[a-z0-9-]+$")]
    name: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    color: Annotated[str, StringConstraints(min_length=1, max_length=30)]
    size: Annotated[str, StringConstraints(min_length=1, max_length=20)]
    price: int = Field(ge=1, le=1_000_000)
    stock: int = Field(ge=0, le=100_000)


def require_seller(store: str, authorization: str | None) -> None:
    expected = seller_tokens().get(store)
    scheme, _, supplied = (authorization or "").partition(" ")
    if not expected or scheme.lower() != "bearer" or not hmac.compare_digest(
        supplied.encode(), expected.encode()
    ):
        raise HTTPException(401, "Invalid seller credentials", headers={"WWW-Authenticate": "Bearer"})


def require_database() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(503, "The catalog database is awaiting configuration.")


@app.exception_handler(DatabaseError)
async def database_error(_request: Request, exc: DatabaseError):
    from fastapi.responses import JSONResponse

    log.error("Database request failed (%s)", type(exc).__name__)
    return JSONResponse({"detail": "Database temporarily unavailable. Try again."}, status_code=503)


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.post("/chat", response_model=ChatReply)
def chat(body: ChatRequest, store: Store = "demo") -> ChatReply:
    if not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("DATABASE_URL"):
        raise HTTPException(503, "The agent is awaiting service configuration.")
    key = hashlib.sha256(json.dumps([store, body.user_id, body.thread_id]).encode()).hexdigest()
    try:
        with database() as connection:
            connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (key,))
            graph = build_graph(PostgresSaver(connection))
            result = graph.invoke(
                {"turn": uuid4().hex}, {"configurable": {"thread_id": key}},
                context={"connection": connection, "store": store, "customer": body.user_id,
                         "message": body.message},
                durability="exit",
            )
            return ChatReply(reply=result["reply"], tool_calls=result["tool_calls"], tokens=result["tokens"])
    except BudgetExhausted:
        raise HTTPException(429, "The daily model usage limit has been reached.") from None
    except APIError as exc:
        log.warning("Model request failed (%s)", type(exc).__name__)
        raise HTTPException(503, "The model is temporarily unavailable. Try again.") from None


@app.get("/catalog")
def catalog(store: Store = "demo"):
    require_database()
    with database() as connection:
        return connection.execute(
            "SELECT sku, name, color, size, price, stock FROM products "
            "WHERE store = %s AND stock > 0 ORDER BY name, size, sku LIMIT 200", (store,)
        ).fetchall()


@app.get("/seller/dashboard")
def dashboard(store: Store = "demo", authorization: Annotated[str | None, Header()] = None):
    require_seller(store, authorization)
    require_database()
    with database() as connection:
        products = connection.execute(
            "SELECT sku, name, color, size, price, stock FROM products WHERE store = %s "
            "ORDER BY sku LIMIT 500", (store,),
        ).fetchall()
        orders = connection.execute(
            "SELECT id, items, total, created_at FROM orders WHERE store = %s "
            "ORDER BY created_at DESC LIMIT 50", (store,),
        ).fetchall()
        sales = connection.execute(
            "SELECT count(*) AS order_count, coalesce(sum(total), 0) AS total "
            "FROM orders WHERE store = %s", (store,),
        ).fetchone()
    return {"products": products, "orders": orders, "sales": sales}


@app.post("/seller/catalog")
def upload_catalog(
    payload: Annotated[str, Body(min_length=1, max_length=90_000)],
    store: Store = "demo",
    authorization: Annotated[str | None, Header()] = None,
):
    require_seller(store, authorization)
    rows = csv.DictReader(io.StringIO(payload.lstrip("\ufeff")), strict=True)
    products: dict[str, Product] = {}
    try:
        if not rows.fieldnames or sorted(rows.fieldnames) != sorted(Product.model_fields):
            raise HTTPException(422, "CSV header must be sku,name,color,size,price,stock.")
        for line, row in enumerate(rows, start=2):
            if line > 501:
                raise HTTPException(422, "Upload at most 500 products at a time.")
            try:
                product = Product.model_validate(row)
            except (ValidationError, TypeError):
                raise HTTPException(422, f"Invalid product on CSV line {line}.") from None
            if product.sku in products:
                raise HTTPException(422, f"Duplicate SKU on CSV line {line}.")
            products[product.sku] = product
    except csv.Error:
        raise HTTPException(422, "Invalid CSV formatting.") from None
    if not products:
        raise HTTPException(422, "Include at least one product row.")
    require_database()
    with database() as connection, connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO products (store, sku, name, color, size, price, stock) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (store, sku) DO UPDATE SET "
            "name = EXCLUDED.name, color = EXCLUDED.color, size = EXCLUDED.size, "
            "price = EXCLUDED.price, stock = EXCLUDED.stock",
            [(store, p.sku, p.name, p.color, p.size, p.price, p.stock)
             for p in sorted(products.values(), key=lambda product: product.sku)],
        )
    return {"updated": len(products)}
