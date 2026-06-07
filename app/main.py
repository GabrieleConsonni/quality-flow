import logging
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request

from alembic_runner import run_alembic_migrations
from config.config_loader import load_config
from elasticmq.elasticmq_config import init_elasticmq
from exceptions.app_exception import QualityFlowAppException
from exceptions.exception_handler import app_exception_handler, generic_exception_handler
from middleware.tenant_middleware import TenantMiddleware
from brokers.api.broker_api import router as brokers_connection_router
from brokers.api.broker_queues_api import router as brokers_router
from data_sources.api.json_array_data_source_api import router as json_array_router
from data_sources.api.database_data_source_api import router as database_router
from data_sources.api.database_table_data_source_api import (
    router as database_table_data_source_router,
)
from elaborations.api.execution_events_api import router as execution_events_router
from elaborations.api.test_suite_schedules_api import router as test_suite_schedules_router
from elaborations.api.test_suite_executions_api import router as test_suite_executions_router
from elaborations.api.test_suites_api import router as test_suites_router
from elaborations.services.test_suite_schedules.scheduler_runtime import (
    bootstrap_scheduler_runtime,
    shutdown_scheduler_runtime,
)
from json_utils.api.json_utils_api import router as json_utils_router
from logs.api.logs_api import router as logs_router
from mock_servers.api.mock_runtime_api import router as mock_runtime_router
from mock_servers.api.mock_server_api import router as mock_servers_router
from mock_servers.services.runtime.mock_server_runtime_registry import (
    MockServerRuntimeRegistry,
)
from public.idp_config_api import router as idp_config_router
from services.multitenant.multitenant_service import get_tenants


def _build_api_access_logger() -> logging.Logger:
    logger = logging.getLogger("quality-flow.api")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)
    return logger


api_access_logger = _build_api_access_logger()


def load_environment():
    load_dotenv()

    print("Loading application configuration...")
    load_config()
    print("Application configuration loaded.")

    print("Starting Alembic migrations...")
    try:
        run_alembic_migrations()
    except Exception as e:
        print(f"Error during Alembic migrations: {str(e)}")
        raise e
    print("Alembic migrations completed.")

    init_elasticmq()

load_environment()

app = FastAPI()

app.add_middleware(TenantMiddleware)


@app.middleware("http")
async def log_incoming_api_calls(request: Request, call_next):
    started_at = time.perf_counter()
    client_host = request.client.host if request.client else "-"
    path = request.url.path
    query = request.url.query
    target = f"{path}?{query}" if query else path

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - started_at) * 1000
        api_access_logger.exception(
            "api request failed method=%s path=%s client=%s duration_ms=%.2f",
            request.method,
            target,
            client_host,
            duration_ms,
        )
        raise

    duration_ms = (time.perf_counter() - started_at) * 1000
    print(
        "api request "
        f"method={request.method} path={target} status={response.status_code} "
        f"client={client_host} duration_ms={duration_ms:.2f}",
        flush=True,
    )
    api_access_logger.info(
        "api request method=%s path=%s status=%s client=%s duration_ms=%.2f",
        request.method,
        target,
        response.status_code,
        client_host,
        duration_ms,
    )
    return response

app.include_router(brokers_router)
app.include_router(brokers_connection_router)
app.include_router(json_array_router)
app.include_router(database_router)
app.include_router(database_table_data_source_router)
app.include_router(test_suites_router)
app.include_router(test_suite_schedules_router)
app.include_router(execution_events_router)
app.include_router(test_suite_executions_router)
app.include_router(json_utils_router)
app.include_router(logs_router)
app.include_router(mock_servers_router)
app.include_router(mock_runtime_router)
app.include_router(idp_config_router)

app.add_exception_handler(QualityFlowAppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.on_event("startup")
def bootstrap_mock_servers_runtime():
    for tenant in get_tenants():
        MockServerRuntimeRegistry.bootstrap_active_servers(tenant_id=tenant.tenant_id)
    bootstrap_scheduler_runtime()


@app.on_event("shutdown")
def stop_background_runtimes():
    shutdown_scheduler_runtime()
