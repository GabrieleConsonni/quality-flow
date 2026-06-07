from config.user_context_config import get_current_user_ctx
from services.multitenant.multitenant_service import get_tenant, url_from_tenant


def url_from_env() -> str:
    """Return the database URL for the current tenant from user context."""
    tenant_id = get_current_user_ctx().tenant_id
    tenant = get_tenant(tenant_id)
    if tenant is None:
        raise RuntimeError(f"Tenant '{tenant_id}' not found in configuration.")
    return url_from_tenant(tenant)