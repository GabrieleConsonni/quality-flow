import threading

from _alembic.services.session_context_manager import managed_session
from mock_servers.models.runtime_models import MockRuntimeServer
from mock_servers.services.alembic.mock_server_service import MockServerService
from mock_servers.services.runtime.mock_queue_listener_thread import (
    MockQueueListenerThread,
)
from mock_servers.services.runtime.mock_runtime_loader import load_runtime_server
from mock_servers.services.runtime.mock_runtime_logger import log_mock_server_event


class MockServerRuntimeRegistry:
    _lock = threading.RLock()
    _servers_by_id: dict[str, MockRuntimeServer] = {}
    _server_ids_by_endpoint: dict[str, str] = {}
    _queue_threads_by_server_id: dict[str, list[MockQueueListenerThread]] = {}

    @classmethod
    def _normalize_endpoint(cls, endpoint: str) -> str:
        return str(endpoint or "").strip().strip("/").lower()

    @classmethod
    def get_server_by_endpoint(cls, endpoint: str) -> MockRuntimeServer | None:
        endpoint_value = cls._normalize_endpoint(endpoint)
        with cls._lock:
            server_id = cls._server_ids_by_endpoint.get(endpoint_value)
            if not server_id:
                return None
            return cls._servers_by_id.get(server_id)

    @classmethod
    def bootstrap_active_servers(cls, tenant_id: str = None):
        with managed_session(tenant_id) as session:
            active_servers = MockServerService().get_all_active(session)
            server_ids = [str(server.id or "") for server in active_servers if server.id]
        for server_id in server_ids:
            try:
                cls.start_server(server_id, tenant_id=tenant_id)
            except Exception as exc:
                log_mock_server_event(
                    server_id,
                    f"Cannot bootstrap mock server '{server_id}': {str(exc)}",
                )

    @classmethod
    def start_server(cls, mock_server_id: str, tenant_id: str = None):
        with managed_session(tenant_id) as session:
            server = MockServerService().get_by_id(session, mock_server_id)
            if not server:
                raise ValueError(f"Mock server '{mock_server_id}' not found.")
            runtime_server = load_runtime_server(session, server)

        with cls._lock:
            cls._stop_server_locked(mock_server_id)
            cls._servers_by_id[mock_server_id] = runtime_server
            cls._server_ids_by_endpoint[runtime_server.endpoint] = mock_server_id
            threads: list[MockQueueListenerThread] = []
            for queue_binding in runtime_server.queues:
                queue_thread = MockQueueListenerThread(
                    mock_server_id,
                    queue_binding,
                    tenant_id=tenant_id,
                )
                queue_thread.start()
                threads.append(queue_thread)
            cls._queue_threads_by_server_id[mock_server_id] = threads
        log_mock_server_event(
            mock_server_id,
            (
                f"Mock server '{runtime_server.description or runtime_server.id}' started. "
                f"Endpoint '/mock/{runtime_server.endpoint}', queue listeners={len(runtime_server.queues)}"
            ),
        )

    @classmethod
    def _stop_server_locked(cls, mock_server_id: str):
        runtime_server = cls._servers_by_id.pop(mock_server_id, None)
        if runtime_server:
            endpoint = cls._normalize_endpoint(runtime_server.endpoint)
            current_server_id = cls._server_ids_by_endpoint.get(endpoint)
            if current_server_id == mock_server_id:
                cls._server_ids_by_endpoint.pop(endpoint, None)
        queue_threads = cls._queue_threads_by_server_id.pop(mock_server_id, [])
        for queue_thread in queue_threads:
            queue_thread.stop()
        for queue_thread in queue_threads:
            queue_thread.join(timeout=5)

    @classmethod
    def stop_server(cls, mock_server_id: str):
        with cls._lock:
            cls._stop_server_locked(mock_server_id)
        log_mock_server_event(mock_server_id, "Mock server stopped.")

    @classmethod
    def remove_server(cls, mock_server_id: str):
        cls.stop_server(mock_server_id)
