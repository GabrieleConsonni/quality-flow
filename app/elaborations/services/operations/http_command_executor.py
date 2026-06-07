from __future__ import annotations

import json
import time

import requests
from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    HttpBodyType,
    ReadApiConfigurationCommandDto,
    WriteApiConfigurationCommandDto,
)
from elaborations.services.operations.command_data_resolver import write_result_constant
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.operations.http_input_node_resolver import (
    compile_authorization,
    resolve_http_body,
    resolve_http_headers,
    resolve_http_kv_params,
    resolve_path_params_and_url,
)
from logs.models.enums.log_level import LogLevel


HttpCommandTypes = ReadApiConfigurationCommandDto | WriteApiConfigurationCommandDto


def _is_write_api(cfg: object) -> bool:
    return str(getattr(cfg, "commandCode", "") or "").strip() == "writeApi"


def _parse_response_body(response: requests.Response):
    if not response.content:
        return None
    content_type = str(response.headers.get("Content-Type") or "").lower()
    if "json" in content_type:
        try:
            return response.json()
        except ValueError:
            pass
    try:
        return response.json()
    except ValueError:
        return response.text


def _request_kwargs(session: Session, cfg: HttpCommandTypes) -> dict[str, object]:
    resolved_url = resolve_path_params_and_url(
        session,
        str(cfg.url or "").strip(),
        getattr(cfg, "pathParams", None),
    )

    resolved_headers = resolve_http_headers(session, getattr(cfg, "headers", None))

    auth_headers = compile_authorization(session, getattr(cfg, "authorization", None))
    resolved_headers.update(auth_headers)

    resolved_params = resolve_http_kv_params(session, getattr(cfg, "queryParams", None))

    kwargs: dict[str, object] = {
        "method": str(cfg.method or "").upper(),
        "url": resolved_url,
        "params": resolved_params,
        "headers": resolved_headers or None,
        "timeout": float(getattr(cfg, "timeoutSeconds", 30) or 30),
    }
    if _is_write_api(cfg):
        body = resolve_http_body(session, cfg.body, cfg.bodyType)
        if cfg.bodyType == "json":
            kwargs["json"] = body
        elif cfg.bodyType == HttpBodyType.FORM_URL_ENCODED.value:
            if body is not None:
                kwargs["data"] = body
            headers = kwargs.get("headers")
            if not isinstance(headers, dict):
                headers = {}
                kwargs["headers"] = headers
            has_content_type = any(str(key or "").strip().lower() == "content-type" for key in headers.keys())
            if not has_content_type:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif body is not None:
            if isinstance(body, str):
                kwargs["data"] = body
            else:
                kwargs["data"] = json.dumps(body, ensure_ascii=True)
    return kwargs


class HttpOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: HttpCommandTypes,
        data,
    ) -> ExecutionResultDto:
        request_kwargs = _request_kwargs(session, cfg)
        url = str(request_kwargs.get("url") or "").strip()
        if not url:
            raise ValueError("url must resolve to a non-empty string.")

        started_at = time.perf_counter()
        try:
            response = requests.request(**request_kwargs)
        except requests.Timeout as exc:
            message = f"HTTP {cfg.method} {url} timed out after {request_kwargs.get('timeout')}s."
            self.log(operation_id, message=message, level=LogLevel.ERROR)
            raise ValueError(message) from exc
        except requests.RequestException as exc:
            message = f"HTTP {cfg.method} {url} failed: {exc}"
            self.log(operation_id, message=message, level=LogLevel.ERROR)
            raise ValueError(message) from exc

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        envelope = {
            "method": str(cfg.method or "").upper(),
            "url": str(response.url or url),
            "status": int(response.status_code),
            "headers": dict(response.headers),
            "body": _parse_response_body(response),
            "elapsed_ms": elapsed_ms,
            "ok": bool(response.ok),
        }
        if cfg.resultConstant:
            write_result_constant(session, cfg.resultConstant, envelope)

        if not response.ok:
            message = (
                f"HTTP {envelope['method']} {envelope['url']} returned status {envelope['status']}."
            )
            self.log(operation_id, message=message, payload=envelope, level=LogLevel.ERROR)
            raise ValueError(message)

        message = f"HTTP {envelope['method']} {envelope['url']} returned status {envelope['status']}."
        self.log(operation_id, message=message, payload=envelope)
        return ExecutionResultDto(
            data=data,
            result=[{"message": message, **envelope}],
        )
