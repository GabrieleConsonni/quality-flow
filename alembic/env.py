import os
import sys
from logging.config import fileConfig

from alembic import context
from config.config_loader import load_config
from sqlalchemy import create_engine, text
from sqlalchemy import pool

from _alembic.constants import SCHEMA
from _alembic.models import metadata
from services.multitenant.multitenant_service import (
    get_tenant,
    get_tenants,
    url_from_tenant,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = metadata


def include_object(object, name, type_, reflected, compare_to):
    # includi solo tabelle nello schema 'quality_flow_service'
    if type_ == "table" and object.schema != SCHEMA:
        return False
    else:
        return True


def create_schema_if_not_exist(tenant):
    url = url_from_tenant(tenant)
    print(f"Creating schema '{SCHEMA}' if not exists for tenant '{tenant.tenant_id}'")
    engine = create_engine(url, pool_pre_ping=True)

    with engine.connect() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        connection.commit()


def create_schemas_for_tenants():
    tenant_id = context.get_x_argument(as_dictionary=True).get("tenant", None)
    if tenant_id:
        tenant = get_tenant(tenant_id)
        if not tenant:
            raise Exception(f"Tenant {tenant_id} not found")
        create_schema_if_not_exist(tenant)
    else:
        for tenant in get_tenants():
            create_schema_if_not_exist(tenant)


def run_tenant_migrations_offline(tenant):
    url = url_from_tenant(tenant)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    tenant_id = context.get_x_argument(as_dictionary=True).get("tenant", None)

    if tenant_id:
        t = get_tenant(tenant_id)
        if not t:
            raise Exception(f"Tenant {tenant_id} not found")
        run_tenant_migrations_offline(t)
    else:
        for tenant in get_tenants():
            run_tenant_migrations_offline(tenant)


def run_tenant_migrations_online(tenant):
    url = url_from_tenant(tenant)
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        connection.execution_options(schema_translate_map={None: SCHEMA})
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=SCHEMA,
            include_schemas=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


def run_migrations_online() -> None:
    tenant_id = context.get_x_argument(as_dictionary=True).get("tenant", None)

    if tenant_id:
        t = get_tenant(tenant_id)
        if not t:
            raise Exception(f"Tenant {tenant_id} not found")
        run_tenant_migrations_online(t)
    else:
        for tenant in get_tenants():
            run_tenant_migrations_online(tenant)


load_config()
create_schemas_for_tenants()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
