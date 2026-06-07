from config.user_context_config import User, init_current_user_ctx
from fastapi import HTTPException, Request, status
from models.settings.tenant_settings import TenantSettings
from services.multitenant.multitenant_service import get_tenant
from starlette.middleware.base import BaseHTTPMiddleware


_PUBLIC_PREFIXES = ("/public/", "/docs", "/openapi.json", "/redoc", "/mock/")


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith(_PUBLIC_PREFIXES):
            try:
                tenant_id: str = request.headers.get("akn-tenant-id")
                user_id: str = request.headers.get("akn-user-id")

                tenant: TenantSettings = get_tenant(tenant_id)
                if tenant is None or user_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Tenant non valido",
                    )

                user: User = User(user_id=user_id, tenant_id=tenant_id)
                init_current_user_ctx(user)

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Tenant non valido: {str(e)}",
                )

        response = await call_next(request)
        return response
