import threading

from config.user_context_config import User, get_current_user_ctx, init_current_user_ctx


class TenantAwareThread(threading.Thread):
    """Thread that captures and propagates tenant/user context from the parent thread.

    Subclasses should override ``run_with_context()`` instead of ``run()``.
    If the subclass already overrides ``run()`` directly, it can call
    ``self._init_tenant_context()`` at the top of its ``run()`` method.
    """

    def __init__(self, *args, tenant_id: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant_id:
            self._captured_user = User(user_id="system", tenant_id=tenant_id)
        else:
            try:
                self._captured_user = get_current_user_ctx()
            except RuntimeError:
                self._captured_user = None

    def _init_tenant_context(self):
        if self._captured_user:
            init_current_user_ctx(self._captured_user)
