import config.config_loader as config_loader
from models.settings.tenant_settings import TenantSettings
from sqlalchemy import URL
from sqlalchemy.engine.url import make_url


def url_from_tenant(t: TenantSettings) -> str:
    db = t.database
    sqlalchemy_url = URL.create(
        drivername="postgresql+psycopg2",
        username=db.user,
        password=db.password,
        host=db.host,
        port=db.port,
        database=db.name,
    )
    stringified_sqlalchemy_url = sqlalchemy_url.render_as_string(hide_password=False)
    assert make_url(stringified_sqlalchemy_url) == sqlalchemy_url
    return stringified_sqlalchemy_url


def get_tenants() -> list[TenantSettings]:
    return config_loader.get_settings().akeron.multitenant.tenants


def get_tenant(tenant_id: str) -> TenantSettings | None:
    tenants: list[TenantSettings] = config_loader.get_settings().akeron.multitenant.tenants
    for t in tenants:
        if t.tenant_id == tenant_id:
            return t
    return None
