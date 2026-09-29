from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.services.seed import seed_if_empty


def ensure_peak_columns() -> None:
    """给已存在的库补高峰配置列(create_all 不会改已有表)。"""
    stmts = [
        "ALTER TABLE lines ADD COLUMN IF NOT EXISTS peak_start_min INTEGER",
        "ALTER TABLE lines ADD COLUMN IF NOT EXISTS peak_end_min INTEGER",
        "ALTER TABLE lines ADD COLUMN IF NOT EXISTS peak_headway_min DOUBLE PRECISION",
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_peak_columns()
    if settings.seed_on_empty:
        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()
    yield


app = FastAPI(title="BusGap", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
