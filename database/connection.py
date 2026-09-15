from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

db_url = settings.DATABASE_URL
connect_args = {}

if db_url.startswith("mysql://"):
    db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)

if "?" in db_url:
    base_url, query_params = db_url.split("?", 1)
    if "ssl-mode" in query_params or "ssl_mode" in query_params or "aiven" in db_url.lower():
        db_url = base_url
        connect_args["ssl"] = {}

pool_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 300,  # 5-minute recycle avoids dropped sockets behind Render/cloud firewalls
}

if "mysql" in db_url:
    # Safe socket and connection timeouts to prevent 30s hangs on dead remote connections
    connect_args.setdefault("connect_timeout", 10)
    connect_args.setdefault("read_timeout", 15)
    connect_args.setdefault("write_timeout", 15)
    # Expand pool size so health warm-up and migrations do not starve login requests
    pool_kwargs["pool_size"] = 10
    pool_kwargs["max_overflow"] = 20
    pool_kwargs["pool_timeout"] = 15

engine = create_engine(
    db_url,
    connect_args=connect_args,
    **pool_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
