"""Lumalog - Backend Entry Point"""
import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.auth import hash_password
from app.database import engine, Base
from app.models.user import User
from app.routers import weight, food, exercise, settings, ai, mi_fit, auth
from app.upload_paths import UPLOAD_ROOT

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    Base.metadata.create_all(bind=engine)
    ensure_lightweight_migrations()
    # Ensure upload directories exist
    os.makedirs(UPLOAD_ROOT / "food", exist_ok=True)
    os.makedirs(UPLOAD_ROOT / "avatar", exist_ok=True)
    migrate_legacy_uploads()
    yield


def ensure_lightweight_migrations():
    """Keep local SQLite installs compatible with small model additions."""
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "UPDATE users SET email = ? WHERE email = ?",
            ("default@local.lumalog", "default@local.qingji"),
        )
        conn.exec_driver_sql(
            "UPDATE users SET password_hash = ? WHERE id = 1 OR email = ?",
            (hash_password("lumalog123"), "default@local.lumalog"),
        )
        users = conn.exec_driver_sql("SELECT id FROM users WHERE id = 1").fetchone()
        if not users:
            conn.exec_driver_sql(
                "INSERT INTO users (id, email, password_hash, created_at) VALUES (1, ?, ?, CURRENT_TIMESTAMP)",
                ("default@local.lumalog", hash_password("lumalog123")),
            )
        user_columns = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()]
        if "avatar_path" not in user_columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN avatar_path VARCHAR(300)")

        columns = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(user_settings)").fetchall()]
        if "user_id" not in columns:
            conn.exec_driver_sql("ALTER TABLE user_settings ADD COLUMN user_id INTEGER DEFAULT 1")
            conn.exec_driver_sql("UPDATE user_settings SET user_id = 1 WHERE user_id IS NULL")
        if "openai_base_url" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE user_settings "
                "ADD COLUMN openai_base_url VARCHAR(300) DEFAULT 'https://api.openai.com/v1'"
            )

        for table in ("weight_records", "food_records", "exercise_records", "exercise_activity_details"):
            table_columns = [row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()]
            if "user_id" not in table_columns:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT 1")
                conn.exec_driver_sql(f"UPDATE {table} SET user_id = 1 WHERE user_id IS NULL")
        ensure_exercise_detail_user_unique(conn)


def ensure_exercise_detail_user_unique(conn):
    indexes = conn.exec_driver_sql("PRAGMA index_list(exercise_activity_details)").fetchall()
    for index in indexes:
        if not index[2]:
            continue
        columns = [
            row[2]
            for row in conn.exec_driver_sql(f"PRAGMA index_info({index[1]})").fetchall()
        ]
        if columns == ["source", "source_id"]:
            rebuild_exercise_activity_details(conn)
            return


def rebuild_exercise_activity_details(conn):
    conn.exec_driver_sql("ALTER TABLE exercise_activity_details RENAME TO exercise_activity_details_old")
    conn.exec_driver_sql(
        """
        CREATE TABLE exercise_activity_details (
            id INTEGER NOT NULL,
            user_id INTEGER DEFAULT 1,
            exercise_record_id INTEGER NOT NULL,
            source VARCHAR(30) NOT NULL,
            source_id VARCHAR(100) NOT NULL,
            track_points_json JSON,
            samples_json JSON,
            raw_report_json JSON,
            raw_detail_json JSON,
            sport_report_json JSON,
            recovery_rate_json JSON,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_exercise_detail_user_source_id UNIQUE (user_id, source, source_id),
            FOREIGN KEY(user_id) REFERENCES users (id),
            FOREIGN KEY(exercise_record_id) REFERENCES exercise_records (id)
        )
        """
    )
    conn.exec_driver_sql(
        """
        INSERT INTO exercise_activity_details (
            id, user_id, exercise_record_id, source, source_id,
            track_points_json, samples_json, raw_report_json, raw_detail_json,
            sport_report_json, recovery_rate_json, created_at, updated_at
        )
        SELECT
            id, COALESCE(user_id, 1), exercise_record_id, source, source_id,
            track_points_json, samples_json, raw_report_json, raw_detail_json,
            sport_report_json, recovery_rate_json, created_at, updated_at
        FROM exercise_activity_details_old
        """
    )
    conn.exec_driver_sql("DROP TABLE exercise_activity_details_old")
    conn.exec_driver_sql(
        "CREATE INDEX ix_exercise_activity_details_user_id ON exercise_activity_details (user_id)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX ix_exercise_activity_details_exercise_record_id ON exercise_activity_details (exercise_record_id)"
    )


def migrate_legacy_uploads():
    legacy_root = Path("uploads")
    if not legacy_root.exists() or legacy_root.resolve() == UPLOAD_ROOT:
        return
    for kind in ("food", "avatar"):
        src = legacy_root / kind
        if src.exists():
            shutil.copytree(src, UPLOAD_ROOT / kind, dirs_exist_ok=True)


app = FastAPI(
    title="Lumalog API",
    description="减重记录与健康追踪 API",
    version="0.1.0",
    lifespan=lifespan,
)

frontend_port = os.getenv("FRONTEND_PORT", "7012")

# CORS for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{frontend_port}", f"http://127.0.0.1:{frontend_port}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploaded images
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(weight.router, prefix="/api/weight", tags=["Weight"])
app.include_router(food.router, prefix="/api/food", tags=["Food"])
app.include_router(exercise.router, prefix="/api/exercise", tags=["Exercise"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(mi_fit.router, prefix="/api/mi-fit", tags=["Mi Fit"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Lumalog"}


assets_dir = FRONTEND_DIST / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    requested = FRONTEND_DIST / full_path
    if full_path and requested.is_file():
        return FileResponse(requested)

    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    raise HTTPException(status_code=404, detail="Frontend build not found. Run `npm run build` in frontend.")
