import aiosqlite

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
