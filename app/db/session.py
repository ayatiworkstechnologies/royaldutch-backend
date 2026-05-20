from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def normalized_database_url():
    url = make_url(settings.sqlalchemy_database_url)
    unsupported_query_keys = {"sslaccept", "sslmode", "sslrootcert"}
    query = {key: value for key, value in url.query.items() if key.lower() not in unsupported_query_keys}
    return url.set(query=query)


connect_args = {}
if settings.database_ssl:
    connect_args["ssl"] = {}
    if settings.database_ssl_ca_path:
        connect_args["ssl_ca"] = settings.database_ssl_ca_path
    connect_args["ssl_verify_identity"] = settings.database_ssl_verify_identity

engine = create_engine(
    normalized_database_url(),
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
