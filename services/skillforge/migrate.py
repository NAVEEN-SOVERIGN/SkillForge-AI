
from sqlalchemy import Column, Integer, MetaData, Table, insert, inspect, select, text

from .db import engine, metadata

schema = MetaData()
state = Table("schema_revision", schema, Column("revision", Integer, primary_key=True))
REVISION = 1


def migrate():
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(81127441)"))
        schema.create_all(connection)
        existing = connection.execute(select(state.c.revision)).scalar_one_or_none()
        if existing == REVISION:
            return
        if existing is not None:
            raise RuntimeError("No migration path exists for the deployed schema revision.")
        metadata.create_all(connection)
        connection.execute(insert(state).values(revision=REVISION))


def require_current_schema():
    with engine.connect() as connection:
        if not inspect(connection).has_table(state.name):
            raise RuntimeError("Initialize the database with python -m skillforge.migrate before serving traffic.")
        revision = connection.execute(select(state.c.revision)).scalar_one_or_none()
        if revision != REVISION:
            raise RuntimeError("Apply the required database migration before serving traffic.")


if __name__ == "__main__":
    migrate()
