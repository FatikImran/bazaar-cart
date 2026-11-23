from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Iterator

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection, connect
from psycopg.rows import dict_row

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    store text NOT NULL, sku text NOT NULL, name text NOT NULL,
    color text NOT NULL, size text NOT NULL, price integer NOT NULL CHECK (price > 0),
    stock integer NOT NULL CHECK (stock >= 0), PRIMARY KEY (store, sku)
);
CREATE TABLE IF NOT EXISTS preferences (
    store text NOT NULL, customer text NOT NULL, data jsonb NOT NULL,
    PRIMARY KEY (store, customer)
);
CREATE TABLE IF NOT EXISTS orders (
    id uuid PRIMARY KEY, store text NOT NULL, customer text NOT NULL,
    items jsonb NOT NULL, total integer NOT NULL CHECK (total > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS orders_store_created_idx ON orders (store, created_at DESC);
CREATE TABLE IF NOT EXISTS model_usage (
    day date PRIMARY KEY, calls integer NOT NULL
);
"""


@contextmanager
def database() -> Iterator[Connection]:
    with connect(os.environ["DATABASE_URL"], row_factory=dict_row,
                 connect_timeout=8) as connection:
        yield connection


def initialize() -> None:
    with database() as connection:
        connection.execute("SELECT pg_advisory_xact_lock(834512)")
        connection.execute(SCHEMA)
    with connect(os.environ["DATABASE_URL"], autocommit=True, row_factory=dict_row,
                 connect_timeout=8) as connection:
        connection.execute("SELECT pg_advisory_lock(834512)")
        PostgresSaver(connection).setup()


def seed() -> None:
    products = [
        ("black-shirt-m", "Classic Shirt", "black", "M", 2200, 15),
        ("black-shirt-l", "Classic Shirt", "black", "L", 2200, 12),
        ("white-shirt-m", "Everyday Shirt", "white", "M", 2000, 10),
        ("white-shirt-s", "Everyday Shirt", "white", "S", 2000, 8),
        ("navy-polo-m", "Cotton Polo", "navy", "M", 2400, 7),
        ("navy-polo-l", "Cotton Polo", "navy", "L", 2400, 8),
        ("black-cap", "Cotton Cap", "black", "One size", 850, 20),
        ("cream-tote", "Canvas Tote", "cream", "One size", 1100, 10),
    ]
    with database() as connection, connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO products VALUES ('demo', %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT DO NOTHING", products
        )


def seller_tokens() -> dict[str, str]:
    return json.loads(os.environ.get("SELLER_TOKENS_JSON") or "{}")


if __name__ == "__main__":
    initialize()
    seed()
