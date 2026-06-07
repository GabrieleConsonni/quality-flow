from contextlib import contextmanager

from _alembic.services.session_factory import SessionFactory


@contextmanager
def managed_session(tenant_id: str = None):
    session = SessionFactory.create_session(tenant_id)
    try:
        with session.begin():  # gestisce commit/rollback automatici
            yield session
    finally:
        session.close()
