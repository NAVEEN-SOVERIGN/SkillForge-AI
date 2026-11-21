
import hashlib
import secrets
import time

from sqlalchemy import (
    JSON,
    Column,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    insert,
    select,
    update,
)

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
metadata = MetaData()
sessions = Table(
    "sessions", metadata, Column("token", String(64), primary_key=True),
    Column("owner", String(110), nullable=False), Column("expires", Integer, nullable=False),
    Column("github", String(100)),
)
scans = Table(
    "scans", metadata, Column("id", String(36), primary_key=True), Column("owner", String(110), nullable=False),
    Column("repo", String(160), nullable=False), Column("state", String(20), nullable=False),
    Column("created", Integer, nullable=False), Column("updated", Integer, nullable=False),
    Column("lease", String(64)), Column("options", JSON, nullable=False), Column("result", JSON),
)
attempts = Table(
    "attempts", metadata, Column("id", String(36), primary_key=True), Column("owner", String(110), nullable=False),
    Column("created", Integer, nullable=False), Column("problem", String(60), nullable=False),
    Column("result", JSON, nullable=False),
)
profiles = Table(
    "profiles", metadata, Column("owner", String(110), primary_key=True), Column("data", JSON, nullable=False),
    Column("revision", Integer, nullable=False),
)
Index("ix_scans_owner_created", scans.c.owner, scans.c.created)
Index("ix_scans_queue", scans.c.state, scans.c.updated)
Index("ix_attempts_owner_created", attempts.c.owner, attempts.c.created)
Index("ix_sessions_expires", sessions.c.expires)


def now():
    return int(time.time())


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def provision(owner=None, github=None, previous=None):
    token = secrets.token_urlsafe(32)
    owner = owner or "guest:" + secrets.token_urlsafe(24)
    with engine.begin() as connection:
        if previous:
            connection.execute(update(sessions).where(sessions.c.token == digest(previous)).values(expires=now()))
        connection.execute(insert(sessions).values(
            token=digest(token), owner=owner, github=github,
            expires=now() + (30 * 86400 if github else 2 * 3600),
        ))
    return token


def session(token):
    if not token or len(token) > 120:
        return None
    with engine.connect() as connection:
        return connection.execute(select(sessions).where(
            sessions.c.token == digest(token), sessions.c.expires > now(),
        )).mappings().first()


def touch(token, current):
    if current and not current["github"] and current["expires"] < now() + 7000:
        with engine.begin() as connection:
            connection.execute(update(sessions).where(sessions.c.token == digest(token), sessions.c.expires > now()).values(
                expires=now() + 7200,
            ))


def expire_guests():
    with engine.begin() as connection:
        expired = select(sessions.c.owner).where(
            sessions.c.expires <= now(), sessions.c.owner.startswith("guest:"),
        )
        for table in (scans, attempts, profiles):
            connection.execute(delete(table).where(table.c.owner.in_(expired)))
        connection.execute(delete(sessions).where(sessions.c.expires <= now()))
