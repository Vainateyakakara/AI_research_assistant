"""
server/db.py - PostgreSQL database connection and table management.
"""

import psycopg2
import psycopg2.extras
from app import config

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id            TEXT PRIMARY KEY,
    title         TEXT DEFAULT 'New Chat',
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id                TEXT PRIMARY KEY,
    conversation_id   TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role              TEXT NOT NULL,
    content           TEXT NOT NULL,
    mode              TEXT,
    model_used        TEXT,
    sources_json      TEXT,
    pipeline_json     TEXT,
    rewritten_query   TEXT,
    resolved_paper    TEXT,
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
"""


def get_connection():
    """Get a new PostgreSQL connection."""
    return psycopg2.connect(config.DATABASE_URL)


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(_SCHEMA_SQL)
        print("PostgreSQL tables ready")
    finally:
        conn.close()


def execute(sql, params=None):
    """Execute a write query (INSERT, UPDATE, DELETE)."""
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
    finally:
        conn.close()


def fetchone(sql, params=None):
    """Execute a query and return one row as a dict."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        conn.close()


def fetchall(sql, params=None):
    """Execute a query and return all rows as dicts."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()
