from typing import Any
from unittest.mock import MagicMock, patch


def build_return_value_service_mock(
    targets: list[str], magic_mock: MagicMock
) -> list[Any]:
    patchers = []

    for target in targets:
        patcher = patch(target)
        mock_obj = patcher.start()
        mock_obj.return_value = magic_mock
        patchers.append(patcher)

    return patchers
