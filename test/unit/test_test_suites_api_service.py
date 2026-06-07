import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "app" / "ui"
if str(UI_ROOT) not in sys.path:
    sys.path.append(str(UI_ROOT))


from test_suites.services import api_service


def test_execute_test_by_id_posts_without_body_contract_fields(monkeypatch):
    captured = {}

    def fake_api_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"execution_id": "exec-1"}

    monkeypatch.setattr(api_service, "api_post", fake_api_post)

    result = api_service.execute_test_by_id("suite-1", "test-9")

    assert result == {"execution_id": "exec-1"}
    assert captured["path"] == "/elaborations/test-suite/suite-1/test/test-9/execute"
    assert captured["payload"] == {}
