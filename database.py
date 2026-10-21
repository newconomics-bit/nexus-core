import json

import aiosqlite

from models import Quote

DB_PATH = "rakitdigital.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                client_name TEXT NOT NULL,
                state TEXT NOT NULL
            )
            """
        )
        cursor = await db.execute("PRAGMA table_info(projects)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "spec_json" not in columns:
            await db.execute("ALTER TABLE projects ADD COLUMN spec_json TEXT")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                quote_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                hpp_breakdown TEXT NOT NULL,
                margin_pct REAL NOT NULL,
                discount_pct REAL NOT NULL,
                final_price INTEGER NOT NULL,
                status TEXT NOT NULL,
                valid_until_days INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def create_project(project_id: str, client_name: str, state: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO projects (id, client_name, state) VALUES (?, ?, ?)",
            (project_id, client_name, state),
        )
        await db.commit()


async def get_project(project_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, client_name, state, spec_json FROM projects WHERE id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "client_name": row["client_name"],
            "state": row["state"],
            "spec_json": row["spec_json"],
        }


async def save_project_spec(project_id: str, spec_json: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE projects SET spec_json = ? WHERE id = ?",
            (spec_json, project_id),
        )
        await db.commit()


async def update_project_state(project_id: str, new_state: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE projects SET state = ? WHERE id = ?",
            (new_state, project_id),
        )
        await db.commit()


def _row_to_quote(row: aiosqlite.Row) -> Quote:
    return Quote.model_validate(
        {
            "quote_id": row["quote_id"],
            "project_id": row["project_id"],
            "version": row["version"],
            "hpp_breakdown": json.loads(row["hpp_breakdown"]),
            "margin_pct": row["margin_pct"],
            "discount_pct": row["discount_pct"],
            "final_price": row["final_price"],
            "status": row["status"],
            "valid_until_days": row["valid_until_days"],
            "created_at": row["created_at"],
        }
    )


async def save_quote(quote: Quote) -> None:
    payload = quote.model_dump(mode="json")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO quotes (
                quote_id, project_id, version, hpp_breakdown, margin_pct,
                discount_pct, final_price, status, valid_until_days, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(quote_id) DO UPDATE SET
                project_id = excluded.project_id,
                version = excluded.version,
                hpp_breakdown = excluded.hpp_breakdown,
                margin_pct = excluded.margin_pct,
                discount_pct = excluded.discount_pct,
                final_price = excluded.final_price,
                status = excluded.status,
                valid_until_days = excluded.valid_until_days,
                created_at = excluded.created_at
            """,
            (
                payload["quote_id"],
                payload["project_id"],
                payload["version"],
                json.dumps(payload["hpp_breakdown"]),
                payload["margin_pct"],
                payload["discount_pct"],
                payload["final_price"],
                payload["status"],
                payload["valid_until_days"],
                payload["created_at"],
            ),
        )
        await db.commit()


async def get_quote(quote_id: str) -> Quote | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM quotes WHERE quote_id = ?",
            (quote_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_quote(row)


async def get_latest_quote(project_id: str) -> Quote | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM quotes
            WHERE project_id = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (project_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_quote(row)
