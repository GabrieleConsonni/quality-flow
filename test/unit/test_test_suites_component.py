import sys
import types
from pathlib import Path


if "streamlit" not in sys.modules:
    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = {}
    streamlit_stub.dialog = lambda *args, **kwargs: (lambda fn: fn)
    sys.modules["streamlit"] = streamlit_stub

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "app" / "ui"
if str(UI_ROOT) not in sys.path:
    sys.path.append(str(UI_ROOT))


from ui.test_suites.components import test_suites_component


def _reset_session_state():
    sys.modules["streamlit"].session_state.clear()


def test_render_suite_selector_list_keeps_add_button_when_empty():
    _reset_session_state()

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state
            self.button_calls = []
            self.info_calls = []

        def info(self, message, **kwargs):
            self.info_calls.append(message)
            return None

        def button(self, *args, **kwargs):
            payload = dict(kwargs)
            if args:
                payload["label"] = args[0]
            self.button_calls.append(payload)
            return False

    stub = StreamlitStub()
    original_st = test_suites_component.st
    try:
        test_suites_component.st = stub
        test_suites_component._render_suite_selector_list([], "")
    finally:
        test_suites_component.st = original_st

    assert stub.info_calls == ["No test suites configured."]
    add_button_call = next(
        call for call in stub.button_calls if call.get("key") == "test_suite_add_btn"
    )
    assert add_button_call["label"] == "Add new suite"
