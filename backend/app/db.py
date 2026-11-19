from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if _sqlite else {}, pool_pre_ping=not _sqlite)

if _sqlite:
    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):  # intégrité référentielle sous SQLite
        cur = dbapi_conn.cursor(); cur.execute("PRAGMA foreign_keys=ON"); cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
