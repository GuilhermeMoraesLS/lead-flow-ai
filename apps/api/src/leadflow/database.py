import os
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import Connection, create_engine, text

engine = create_engine(
    os.environ["DATABASE_URL"],
    pool_size=2,
    max_overflow=0,
    pool_pre_ping=True,
    hide_parameters=True,
)


@contextmanager
def transaction(actor: UUID, organization: UUID | None = None) -> Iterator[Connection]:
    with engine.begin() as connection:
        connection.execute(
            text(
                "SELECT set_config('app.user_id', :actor, true), "
                "set_config('app.organization_id', :org, true)"
            ),
            {"actor": str(actor), "org": str(organization) if organization else ""},
        )
        yield connection
