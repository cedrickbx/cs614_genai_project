import asyncio
import json
import sqlite3
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Literal, TypedDict
from mcp.server.fastmcp import FastMCP, Context

DB_PATH = "health.db" #userDB

# ============= Define DB schema =============

@dataclass
class AppContext:
    conn: sqlite3.Connection

def _now_ts() -> int:
    return int(time.time())

def _init_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # Medical history table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS medical_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      condition TEXT NOT NULL,
      diagnosis_date TEXT,
      severity TEXT,
      status TEXT,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL
    )
    """)

    # Medication table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS medication (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      dosage TEXT,
      time_taken INTEGER,
      condition_id INTEGER,
      status TEXT,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL,
      FOREIGN KEY (condition_id) REFERENCES medical_history(id) ON DELETE SET NULL
    )
    """)

    # Food log table (past 24 hours)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS food_24h (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      notes TEXT,
      taken_at INTEGER NOT NULL,
      created_at INTEGER NOT NULL
    )
    """)

    # Table indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_med_hist_status ON medical_history(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_med_time_taken ON medication(time_taken)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_food_taken_at ON food_24h(taken_at)")

    conn.commit()

def _purge_expired(conn: sqlite3.Connection) -> None:
    """Enforce retention rules:
       - medical_history rows with status LIKE 'recovered%' kept 14 days after last update
       - food_24h rows kept only for last 24h
    """
    now = _now_ts()
    two_weeks = 14 * 24 * 3600
    day = 24 * 3600
    cur = conn.cursor()

    cur.execute("""
      DELETE FROM medical_history
      WHERE status LIKE 'recovered%' AND updated_at <= ?
    """, (now - two_weeks,))

    cur.execute("""
      DELETE FROM food_24h
      WHERE taken_at < ?
    """, (now - day,))

    conn.commit()

# # ============= Define DB lifespan =============
@asynccontextmanager
async def lifespan(server: FastMCP):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    _purge_expired(conn)  # purge once at startup only
    try:
        yield AppContext(conn=conn)
    finally:
        conn.close()

mcp = FastMCP("Health DB MCP", lifespan=lifespan)

# ============= Helpers functions to prevent error during execution =============

ALLOWED_TABLES = ("medical_history", "medication", "food_24h")

def _as_json_rows(cur: sqlite3.Cursor, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    rows = cur.fetchmany(limit) if limit else cur.fetchall()
    return [dict(r) for r in rows]

def _quote_ident(ident: str) -> str:
    if not ident.replace("_", "").isalnum():
        raise ValueError(f"Invalid identifier: {ident!r}")
    return f'"{ident}"'

def _ensure_allowed_table(table: str) -> None:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Unknown/blocked table: {table}. Allowed: {ALLOWED_TABLES}")

def _get_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    _ensure_allowed_table(table)
    cur = conn.execute(f"PRAGMA table_info({_quote_ident(table)})")
    return [r["name"] for r in cur.fetchall()]

def _validate_columns(conn: sqlite3.Connection, table: str, cols: List[str]) -> None:
    allowed = set(_get_columns(conn, table))
    bad = [c for c in cols if c not in allowed]
    if bad:
        raise ValueError(f"Invalid column(s) for {table}: {bad}. Allowed: {sorted(allowed)}")

def _build_where(where: Optional[Dict[str, Any]]) -> tuple[str, List[Any]]:
    if not where:
        return "", []
    clauses, params = [], []
    for col, val in where.items():
        col_q = _quote_ident(col)
        if isinstance(val, dict) and "op" in val and "value" in val:
            op = str(val["op"]).strip().upper()
            if op not in {"=", "!=", ">", ">=", "<", "<=", "LIKE", "IN"}:
                raise ValueError(f"Unsupported operator: {op}")
            if op == "IN":
                seq = list(val["value"])
                if not seq:
                    clauses.append("1=0")
                else:
                    placeholders = ",".join(["?"] * len(seq))
                    clauses.append(f"{col_q} IN ({placeholders})")
                    params.extend(seq)
            else:
                clauses.append(f"{col_q} {op} ?")
                params.append(val["value"])
        else:
            clauses.append(f"{col_q} = ?")
            params.append(val)
    return " WHERE " + " AND ".join(clauses), params

class SelectResult(TypedDict):
    rows: List[Dict[str, Any]]
    rowCount: int
    nextOffset: Optional[int]

class MutateResult(TypedDict):
    rowCount: int
    lastRowId: Optional[int]

# ============= MCP Resources exposed to agent =============

@mcp.resource("db://schema")
def schema_root(ctx: Context) -> str:
    conn = ctx.request_context.lifespan_context.conn
    return json.dumps({"tables": list(ALLOWED_TABLES)}, indent=2)

@mcp.resource("db://schema/{table}")
def schema_table(table: str, ctx: Context) -> str:
    conn = ctx.request_context.lifespan_context.conn
    _ensure_allowed_table(table)
    cur = conn.execute(f"PRAGMA table_info({_quote_ident(table)})")
    return json.dumps({"table": table, "columns": _as_json_rows(cur)}, indent=2)

# ============= MCP Tools for agent =============

@mcp.tool(description="Check tables and their attributes in the DB.")
def check_schema(ctx: Context | None = None) -> Dict[str, Any]:
    conn = ctx.request_context.lifespan_context.conn
    out = {}
    for t in ALLOWED_TABLES:
        cur = conn.execute(f"PRAGMA table_info({_quote_ident(t)})")
        out[t] = _as_json_rows(cur)
    return out

@mcp.tool(description="Query a table with optional where/order/limit/offset.")
def table_query(
    table: str,
    columns: Optional[List[str]] = None,
    where: Optional[Dict[str, Any]] = None,
    order_by: Optional[List[str]] = None,
    limit: int = 100,
    offset: int = 0,
    ctx: Context | None = None,
) -> SelectResult:
    conn = ctx.request_context.lifespan_context.conn

    _ensure_allowed_table(table)
    
    if where == {}:
        where = None
    if order_by == []:
        order_by = None
    if columns == []:
        columns = None

    if columns:
        _validate_columns(conn, table, columns)
    cols_sql = ", ".join(_quote_ident(c) for c in columns) if columns else "*"

    if order_by:
        _validate_columns(conn, table, order_by)
    order_sql = " ORDER BY " + ", ".join(_quote_ident(c) for c in order_by) if order_by else ""

    where_sql, params = _build_where(where)
    cur = conn.execute(
        f"SELECT {cols_sql} FROM {_quote_ident(table)}{where_sql}{order_sql} LIMIT ? OFFSET ?",
        (*params, limit, offset),
    )
    rows = _as_json_rows(cur)
    cur2 = conn.execute(f"SELECT COUNT(*) AS c FROM {_quote_ident(table)}{where_sql}", params)
    total = int(cur2.fetchone()["c"])
    next_offset = offset + limit if offset + limit < total else None
    return {"rows": rows, "rowCount": total, "nextOffset": next_offset}

@mcp.tool(description="Insert a record into a table.")
def table_insert(
    table: str,
    values: Dict[str, Any],
    ctx: Context | None = None,
) -> MutateResult:
    conn = ctx.request_context.lifespan_context.conn
    _ensure_allowed_table(table)
    if not values:
        raise ValueError("values cannot be empty")

    now = _now_ts()
    cols_available = _get_columns(conn, table)
    vals = dict(values)
    if "created_at" in cols_available and "created_at" not in vals:
        vals["created_at"] = now
    if "updated_at" in cols_available and "updated_at" not in vals:
        vals["updated_at"] = now

    _validate_columns(conn, table, list(vals.keys()))
    cols = ", ".join(_quote_ident(k) for k in vals.keys())
    placeholders = ", ".join(["?"] * len(vals))
    cur = conn.execute(
        f"INSERT INTO {_quote_ident(table)} ({cols}) VALUES ({placeholders})",
        list(vals.values()),
    )
    conn.commit()
    return {"rowCount": cur.rowcount if cur.rowcount != -1 else 1, "lastRowId": cur.lastrowid}

@mcp.tool(description="Update record(s) in a table (requires a WHERE).")
def table_update(
    table: str,
    values: Dict[str, Any],
    where: Dict[str, Any],
    ctx: Context | None = None,
) -> MutateResult:
    conn = ctx.request_context.lifespan_context.conn
    _ensure_allowed_table(table)
    if not values:
        raise ValueError("values cannot be empty")

    cols_available = _get_columns(conn, table)
    vals = dict(values)
    if "updated_at" in cols_available:
        vals.setdefault("updated_at", _now_ts())

    _validate_columns(conn, table, list(vals.keys()))
    set_clause = ", ".join(f"{_quote_ident(k)}=?" for k in vals.keys())
    where_sql, params_where = _build_where(where)
    if not where_sql:
        raise ValueError("Refusing to update without WHERE")
    cur = conn.execute(
        f"UPDATE {_quote_ident(table)} SET {set_clause}{where_sql}",
        [*vals.values(), *params_where],
    )
    conn.commit()
    return {"rowCount": cur.rowcount, "lastRowId": None}

@mcp.tool(description="Delete record(s) from a table (requires a WHERE).")
def table_delete(
    table: str,
    where: Dict[str, Any],
    ctx: Context | None = None,
) -> MutateResult:
    conn = ctx.request_context.lifespan_context.conn
    _ensure_allowed_table(table)
    where_sql, params = _build_where(where)
    if not where_sql:
        raise ValueError("Refusing to delete without WHERE")
    cur = conn.execute(f"DELETE FROM {_quote_ident(table)}{where_sql}", params)
    conn.commit()
    return {"rowCount": cur.rowcount, "lastRowId": None}

if __name__ == "__main__":
    mcp.run()
