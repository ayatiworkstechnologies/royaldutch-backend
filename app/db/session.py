from collections.abc import Generator
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def normalized_database_url():
    url = make_url(settings.sqlalchemy_database_url)
    unsupported_query_keys = {"sslaccept", "sslmode", "sslrootcert", "ssl_ca", "ssl_cert", "ssl_key", "ssl-mode"}
    query = {key: value for key, value in url.query.items() if not (key.lower().startswith("ssl") or "ca" in key.lower())}
    return url.set(query=query)


database_url = normalized_database_url()

connect_args = {}
if database_url.drivername.startswith("sqlite"):
    connect_args["check_same_thread"] = False
if settings.database_ssl and database_url.drivername.startswith("mysql"):
    connect_args["ssl"] = {"check_hostname": bool(settings.database_ssl_verify_identity)}
    if settings.database_ssl_ca_path and os.path.isfile(settings.database_ssl_ca_path):
        connect_args["ssl_ca"] = settings.database_ssl_ca_path
    connect_args["ssl_verify_identity"] = settings.database_ssl_verify_identity

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
