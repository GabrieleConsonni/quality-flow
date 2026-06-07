from config.user_context_config import get_current_user_ctx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from services.multitenant.multitenant_service import get_tenant, url_from_tenant


class SessionFactory:
    _engines = {}

    @staticmethod
    def create_session(tenant_id: str = None) -> Session:
        tenant_id = tenant_id or get_current_user_ctx().tenant_id
        tenant = get_tenant(tenant_id)
        if tenant is None:
            raise RuntimeError(f"Tenant '{tenant_id}' not found in configuration.")

        if tenant_id not in SessionFactory._engines:
            SessionFactory._engines[tenant_id] = create_engine(
                url_from_tenant(tenant), pool_pre_ping=True
            )

        engine = SessionFactory._engines[tenant_id]
        session_local = sessionmaker(bind=engine)
        return session_local()
