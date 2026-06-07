from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from data_sources.services.dataset_parameter_resolver import (
    SUPPORTED_DATASET_BUILT_IN_RESOLVERS,
)


SUPPORTED_RUNTIME_FUNCTIONS = ("now", "today")


class CommandType(str, Enum):
    CONTEXT = "context"
    ACTION = "action"
    ASSERT = "assert"


class CommandCode(str, Enum):
    SET_VARIABLE = "setVariable"
    DELETE_VARIABLE = "deleteVariable"
    SLEEP = "sleep"
    READ_API = "readApi"
    WRITE_API = "writeApi"
    SEND_MESSAGE_QUEUE = "sendMessageQueue"
    SAVE_TABLE = "saveTable"
    DROP_TABLE = "dropTable"
    CLEAN_TABLE = "cleanTable"
    EXPORT_DATASET = "exportDataset"
    DROP_DATASET = "dropDataset"
    CLEAN_DATASET = "cleanDataset"
    RUN_SUITE = "runSuite"
    JSON_EQUALS = "jsonEquals"
    JSON_EMPTY = "jsonEmpty"
    JSON_NOT_EMPTY = "jsonNotEmpty"
    JSON_CONTAINS = "jsonContains"
    JSON_ARRAY_EQUALS = "jsonArrayEquals"
    JSON_ARRAY_EMPTY = "jsonArrayEmpty"
    JSON_ARRAY_NOT_EMPTY = "jsonArrayNotEmpty"
    JSON_ARRAY_CONTAINS = "jsonArrayContains"
    INIT_CONSTANT = "setVariable"
    DELETE_CONSTANT = "deleteVariable"
    RECEIVE_QUEUE = "receiveQueue"
    QUERY_DATABASE = "queryDatabase"


class ConstantContext(str, Enum):
    RUN_ENVELOPE = "runEnvelope"
    GLOBAL = "global"
    LOCAL = "local"
    RESULT = "result"


class ConstantSourceType(str, Enum):
    VALUE = "value"
    JSON = "json"
    JSON_ARRAY = "jsonArray"
    DATASET = "dataset"
    FUNCTION = "function"
    RAW = "value"
    SQS_QUEUE = "sqsQueue"


class InputRefKind(str, Enum):
    RUNTIME_VALUE = "runtimeValue"
    SOURCE = "source"


class HttpInputNodeKind(str, Enum):
    LITERAL = "literal"
    RUNTIME_VALUE = "runtimeValue"
    SOURCE = "source"
    BUILT_IN = "builtIn"


class HttpBodyType(str, Enum):
    JSON = "json"
    TEXT = "text"
    FORM_URL_ENCODED = "formUrlEncoded"


class AssertEvaluatedObjectType(str, Enum):
    JSON_DATA = "json-data"


class AssertType(str, Enum):
    EQUALS = "equals"
    EMPTY = "empty"
    NOT_EMPTY = "not-empty"
    SCHEMA_VALIDATION = "schema-validation"
    CONTAINS = "contains"
    JSON_ARRAY_EQUALS = "json-array-equals"
    JSON_ARRAY_CONTAINS = "json-array-contains"


def _normalize_token(value: object) -> str:
    return str(value or "").strip()


def _normalize_path_token(value: object) -> str:
    raw = _normalize_token(value)
    if not raw:
        return ""
    return raw.replace("_", "-")


def _first_non_empty(data: dict, *keys: str):
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _normalize_target_path(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.startswith("$."):
        return raw
    if raw.startswith("$"):
        return f"$.{raw[1:].lstrip('.')}"
    return f"$.{raw.lstrip('.')}"


def _normalize_definition_id(value: object) -> str:
    return _normalize_token(value)


def _normalize_compare_keys(value: object) -> list[str]:
    if isinstance(value, str):
        raw_items = value.replace(";", ",").replace("\n", ",").split(",")
        return [item.strip() for item in raw_items if item and item.strip()]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            normalized = _normalize_token(item)
            if normalized:
                result.append(normalized)
        return result
    return []


def _normalize_value_type(value: object, *, allow_sources: bool) -> str:
    normalized = _normalize_token(value)
    if normalized == "raw":
        normalized = ConstantSourceType.VALUE.value
    if allow_sources:
        supported = {item.value for item in ConstantSourceType}
    else:
        supported = {
            ConstantSourceType.VALUE.value,
            ConstantSourceType.JSON.value,
            ConstantSourceType.FUNCTION.value,
        }
    if normalized not in supported:
        raise ValueError("Unsupported valueType.")
    return normalized


def _normalize_http_method(value: object) -> str:
    return _normalize_token(value).upper()


def _normalize_http_body_type(value: object) -> str:
    raw_value = _normalize_token(value)
    normalized_key = raw_value.replace("-", "").replace("_", "").lower()
    if not normalized_key:
        return HttpBodyType.JSON.value
    aliases = {
        HttpBodyType.JSON.value.lower(): HttpBodyType.JSON.value,
        HttpBodyType.TEXT.value.lower(): HttpBodyType.TEXT.value,
        "formurlencoded": HttpBodyType.FORM_URL_ENCODED.value,
        "xwwwformurlencoded": HttpBodyType.FORM_URL_ENCODED.value,
    }
    normalized = aliases.get(normalized_key)
    if normalized is None:
        raise ValueError("bodyType must be one of: json, text, formUrlEncoded.")
    return normalized


def _coerce_json_object(value: object, *, field_name: str) -> dict | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    raise ValueError(f"{field_name} must be an object.")


def _coerce_query_params(value: object) -> dict | list | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    raise ValueError("queryParams must be an object or array.")


def _coerce_authorization(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("authorization must be an object.")

    auth_type = _normalize_token(value.get("type"))
    if not auth_type:
        return {}

    if auth_type == "basic":
        username = _normalize_token(value.get("username"))
        password = str(value.get("password") or "")
        if not username:
            raise ValueError("authorization.username is required for basic auth.")
        if not password:
            raise ValueError("authorization.password is required for basic auth.")
        return {
            "type": "basic",
            "username": username,
            "password": password,
        }
    if auth_type == "bearer":
        token = _normalize_token(value.get("token"))
        if not token:
            raise ValueError("authorization.token is required for bearer auth.")
        return {
            "type": "bearer",
            "token": token,
        }
    if auth_type == "apiKey":
        username = _normalize_token(value.get("username"))
        api_key = _normalize_token(value.get("apiKey"))
        auth_endpoint = _normalize_token(value.get("authEndpoint"))
        if not username:
            raise ValueError("authorization.username is required for apiKey auth.")
        if not api_key:
            raise ValueError("authorization.apiKey is required for apiKey auth.")
        if not auth_endpoint:
            raise ValueError("authorization.authEndpoint is required for apiKey auth.")
        return {
            "type": "apiKey",
            "username": username,
            "apiKey": api_key,
            "authEndpoint": auth_endpoint,
        }
    if auth_type == "oauth2":
        token_url = _normalize_token(value.get("tokenUrl"))
        client_id = _normalize_token(value.get("clientId"))
        client_secret = str(value.get("clientSecret") or "")
        if not token_url:
            raise ValueError("authorization.tokenUrl is required for oauth2 auth.")
        if not client_id:
            raise ValueError("authorization.clientId is required for oauth2 auth.")
        if not client_secret:
            raise ValueError("authorization.clientSecret is required for oauth2 auth.")
        return {
            "type": "oauth2",
            "tokenUrl": token_url,
            "clientId": client_id,
            "clientSecret": client_secret,
        }

    raise ValueError("authorization.type must be one of: basic, bearer, apiKey, oauth2.")


_HTTP_INPUT_NODE_KINDS = {item.value for item in HttpInputNodeKind}


class HttpInputNode(BaseModel):
    kind: str
    value: object | None = None
    definitionId: str | None = None
    fieldPath: str | None = None
    sourceCode: str | None = None
    resolver: str | None = None

    @model_validator(mode="after")
    def validate_node(self):
        self.kind = _normalize_token(self.kind)
        if self.kind not in _HTTP_INPUT_NODE_KINDS:
            raise ValueError(
                "kind must be one of: literal, runtimeValue, source, builtIn."
            )
        if self.kind == HttpInputNodeKind.LITERAL.value:
            self.definitionId = None
            self.fieldPath = None
            self.sourceCode = None
            self.resolver = None
        elif self.kind == HttpInputNodeKind.RUNTIME_VALUE.value:
            self.definitionId = _normalize_token(self.definitionId)
            if not self.definitionId:
                raise ValueError("definitionId is required for runtimeValue nodes.")
            self.fieldPath = _normalize_token(self.fieldPath) or None
            self.value = None
            self.sourceCode = None
            self.resolver = None
        elif self.kind == HttpInputNodeKind.SOURCE.value:
            self.sourceCode = _normalize_token(self.sourceCode)
            if not self.sourceCode:
                raise ValueError("sourceCode is required for source nodes.")
            self.value = None
            self.definitionId = None
            self.fieldPath = None
            self.resolver = None
        elif self.kind == HttpInputNodeKind.BUILT_IN.value:
            self.resolver = _normalize_token(self.resolver)
            if self.resolver not in SUPPORTED_RUNTIME_FUNCTIONS:
                supported = ", ".join(SUPPORTED_RUNTIME_FUNCTIONS)
                raise ValueError(f"resolver must be one of: {supported}.")
            self.value = None
            self.definitionId = None
            self.fieldPath = None
            self.sourceCode = None
        return self


def _coerce_http_input_node(value: object) -> HttpInputNode | None:
    if value is None:
        return None
    if isinstance(value, HttpInputNode):
        return value
    if isinstance(value, dict):
        kind = _normalize_token(value.get("kind"))
        if kind in _HTTP_INPUT_NODE_KINDS:
            return HttpInputNode(
                kind=kind,
                value=value.get("value"),
                definitionId=_first_non_empty(value, "definitionId", "definition_id"),
                fieldPath=_first_non_empty(value, "fieldPath", "field_path"),
                sourceCode=_first_non_empty(value, "sourceCode", "source_code"),
                resolver=value.get("resolver"),
            )
    return None


def _coerce_to_http_input_node(value: object) -> HttpInputNode:
    node = _coerce_http_input_node(value)
    if node is not None:
        return node
    return HttpInputNode(kind=HttpInputNodeKind.LITERAL.value, value=value)


def _coerce_http_input_tree(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, HttpInputNode):
        return value
    if isinstance(value, dict):
        node = _coerce_http_input_node(value)
        if node is not None:
            return node
        return {key: _coerce_http_input_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_coerce_http_input_tree(item) for item in value]
    return _coerce_to_http_input_node(value)


def _is_http_form_scalar(value: object) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _validate_http_form_body_node(node: HttpInputNode, *, field_name: str) -> HttpInputNode:
    if node.kind == HttpInputNodeKind.SOURCE.value:
        raise ValueError(f"body.{field_name} does not support source nodes for formUrlEncoded.")
    if node.kind == HttpInputNodeKind.LITERAL.value and not _is_http_form_scalar(node.value):
        raise ValueError(
            f"body.{field_name} must resolve to a scalar literal for formUrlEncoded."
        )
    return node


def _coerce_http_form_body(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("body must be an object for formUrlEncoded.")

    result: dict[str, HttpInputNode] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key or "").strip()
        if not key:
            raise ValueError("body keys are required for formUrlEncoded.")
        node = _coerce_to_http_input_node(raw_value)
        result[key] = _validate_http_form_body_node(node, field_name=key)
    return result or None


def _serialize_http_input_node(node: object) -> object:
    if isinstance(node, HttpInputNode):
        result = {"kind": node.kind}
        if node.kind == HttpInputNodeKind.LITERAL.value:
            result["value"] = node.value
        elif node.kind == HttpInputNodeKind.RUNTIME_VALUE.value:
            result["definitionId"] = node.definitionId
            if node.fieldPath:
                result["fieldPath"] = node.fieldPath
        elif node.kind == HttpInputNodeKind.SOURCE.value:
            result["sourceCode"] = node.sourceCode
        elif node.kind == HttpInputNodeKind.BUILT_IN.value:
            result["resolver"] = node.resolver
        return result
    if isinstance(node, dict):
        return {key: _serialize_http_input_node(item) for key, item in node.items()}
    if isinstance(node, list):
        return [_serialize_http_input_node(item) for item in node]
    return node


def _coerce_http_kv_params(value: object) -> dict | None:
    if value is None:
        return None
    if isinstance(value, dict):
        result: dict = {}
        for key, item in value.items():
            result[str(key)] = _coerce_to_http_input_node(item)
        return result if result else None
    if isinstance(value, list):
        return {str(i): _coerce_to_http_input_node(item) for i, item in enumerate(value)} if value else None
    return None


def _coerce_authorization_guided(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("authorization must be an object.")

    auth_type = _normalize_token(value.get("type"))
    if not auth_type:
        return {}

    def _leaf(raw):
        return _coerce_to_http_input_node(raw)

    if auth_type == "basic":
        username = value.get("username")
        password = value.get("password")
        if username is None and password is None:
            return {}
        return {
            "type": "basic",
            "username": _leaf(username),
            "password": _leaf(password),
        }
    if auth_type == "bearer":
        token = value.get("token")
        if token is None:
            return {}
        return {
            "type": "bearer",
            "token": _leaf(token),
        }
    if auth_type == "apiKey":
        return {
            "type": "apiKey",
            "username": _leaf(value.get("username")),
            "apiKey": _leaf(value.get("apiKey")),
            "authEndpoint": _leaf(value.get("authEndpoint")),
        }
    if auth_type == "oauth2":
        return {
            "type": "oauth2",
            "tokenUrl": _leaf(value.get("tokenUrl")),
            "clientId": _leaf(value.get("clientId")),
            "clientSecret": _leaf(value.get("clientSecret")),
        }

    raise ValueError("authorization.type must be one of: basic, bearer, apiKey, oauth2.")


class ConstantRefDto(BaseModel):
    definitionId: str

    @model_validator(mode="after")
    def validate_definition_id(self):
        self.definitionId = _normalize_token(self.definitionId)
        if not self.definitionId:
            raise ValueError("definitionId is required.")
        return self


class RuntimeValueRefDto(ConstantRefDto):
    pass


class SourceRefDto(BaseModel):
    sourceCode: str

    @model_validator(mode="after")
    def validate_source_code(self):
        self.sourceCode = _normalize_token(self.sourceCode)
        if not self.sourceCode:
            raise ValueError("sourceCode is required.")
        return self


class InputRefDto(BaseModel):
    kind: str
    definitionId: str | None = None
    sourceCode: str | None = None

    @model_validator(mode="after")
    def validate_ref(self):
        self.kind = _normalize_token(self.kind)
        if self.kind not in {item.value for item in InputRefKind}:
            raise ValueError("kind must be one of: runtimeValue, source.")
        if self.kind == InputRefKind.RUNTIME_VALUE.value:
            self.definitionId = _normalize_token(self.definitionId)
            self.sourceCode = None
            if not self.definitionId:
                raise ValueError("definitionId is required for runtimeValue refs.")
            return self
        self.sourceCode = _normalize_token(self.sourceCode)
        self.definitionId = None
        if not self.sourceCode:
            raise ValueError("sourceCode is required for source refs.")
        return self


class ResultConstantDto(BaseModel):
    definitionId: str
    name: str
    valueType: str = ConstantSourceType.JSON.value

    @model_validator(mode="after")
    def validate_result_constant(self):
        self.definitionId = _normalize_token(self.definitionId)
        self.name = _normalize_token(self.name)
        self.valueType = _normalize_value_type(self.valueType, allow_sources=True)
        if not self.definitionId:
            raise ValueError("resultConstant.definitionId is required.")
        if not self.name:
            raise ValueError("resultConstant.name is required.")
        return self


class SendMessageTemplateConstantDto(BaseModel):
    name: str
    kind: str
    value: object | None = None

    @model_validator(mode="after")
    def validate_constant(self):
        self.name = _normalize_token(self.name)
        self.kind = _normalize_token(self.kind).lower()
        if self.kind == "str":
            self.kind = "string"
        if self.kind == "booleano":
            self.kind = "boolean"
        if not self.name:
            raise ValueError("messageTemplate.constants[].name is required.")
        if self.kind not in {"string", "number", "date", "datetime", "boolean", "variable", "function"}:
            raise ValueError(
                "messageTemplate.constants[].kind must be one of: string, number, date, datetime, boolean, variable, function."
            )
        if self.kind == "variable":
            normalized_value = str(self.value or "").strip()
            if not normalized_value:
                raise ValueError("messageTemplate.constants[].value is required for variable constants.")
            self.value = normalized_value
        if self.kind == "function":
            normalized_value = _normalize_token(self.value).lower()
            if normalized_value not in SUPPORTED_RUNTIME_FUNCTIONS:
                raise ValueError("messageTemplate.constants[].value must be one of: now, today.")
            self.value = normalized_value
        return self


class SendMessageTemplateDto(BaseModel):
    forEach: str | None = None
    fields: list[str] = Field(default_factory=list)
    constants: list[SendMessageTemplateConstantDto] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_template(self):
        normalized_fields: list[str] = []
        for field in self.fields:
            normalized = _normalize_token(field)
            if normalized and normalized not in normalized_fields:
                normalized_fields.append(normalized)
        self.fields = normalized_fields
        self.forEach = _normalize_token(self.forEach) or None
        if not self.fields and not self.constants:
            raise ValueError("messageTemplate requires at least one field or constant.")
        return self


class DatasetParameterBindingDto(BaseModel):
    kind: str
    definitionId: str | None = None
    resolver: str | None = None

    @model_validator(mode="after")
    def validate_binding(self):
        self.kind = _normalize_token(self.kind).lower()
        if self.kind == "constant_ref":
            self.definitionId = _normalize_token(self.definitionId)
            if not self.definitionId:
                raise ValueError("definitionId is required for dataset parameter constant_ref bindings.")
            self.resolver = None
            return self
        if self.kind == "built_in":
            self.resolver = _normalize_token(self.resolver)
            if self.resolver not in SUPPORTED_DATASET_BUILT_IN_RESOLVERS:
                supported = ", ".join(SUPPORTED_DATASET_BUILT_IN_RESOLVERS)
                raise ValueError(f"resolver must be one of: {supported}.")
            self.definitionId = None
            return self
        raise ValueError("dataset parameter binding kind must be one of: constant_ref, built_in.")


def _coerce_runtime_value_ref(value: object) -> RuntimeValueRefDto | None:
    if isinstance(value, RuntimeValueRefDto):
        return value
    if isinstance(value, ConstantRefDto):
        return RuntimeValueRefDto(definitionId=value.definitionId)
    if isinstance(value, dict):
        definition_id = _first_non_empty(value, "definitionId", "definition_id")
        if definition_id:
            return RuntimeValueRefDto(definitionId=definition_id)
    return None


def _coerce_source_ref(value: object) -> SourceRefDto | None:
    if isinstance(value, SourceRefDto):
        return value
    if isinstance(value, dict):
        source_code = _first_non_empty(value, "sourceCode", "source_code")
        if source_code:
            return SourceRefDto(sourceCode=source_code)
    return None


def _coerce_input_ref(value: object) -> InputRefDto | None:
    if isinstance(value, InputRefDto):
        return value
    if isinstance(value, RuntimeValueRefDto):
        return InputRefDto(kind=InputRefKind.RUNTIME_VALUE.value, definitionId=value.definitionId)
    if isinstance(value, SourceRefDto):
        return InputRefDto(kind=InputRefKind.SOURCE.value, sourceCode=value.sourceCode)
    if isinstance(value, dict):
        if _first_non_empty(value, "kind"):
            return InputRefDto(
                kind=_first_non_empty(value, "kind"),
                definitionId=_first_non_empty(value, "definitionId", "definition_id"),
                sourceCode=_first_non_empty(value, "sourceCode", "source_code"),
            )
        runtime_value_ref = _coerce_runtime_value_ref(value)
        if runtime_value_ref is not None:
            return InputRefDto(kind=InputRefKind.RUNTIME_VALUE.value, definitionId=runtime_value_ref.definitionId)
        source_ref = _coerce_source_ref(value)
        if source_ref is not None:
            return InputRefDto(kind=InputRefKind.SOURCE.value, sourceCode=source_ref.sourceCode)
    return None


def _coerce_result_constant(value: object) -> ResultConstantDto | None:
    if isinstance(value, ResultConstantDto):
        return value
    if isinstance(value, dict):
        definition_id = _first_non_empty(value, "definitionId", "definition_id")
        name = _first_non_empty(value, "name")
        value_type = _first_non_empty(value, "valueType", "value_type")
        if definition_id or name:
            return ResultConstantDto(
                definitionId=definition_id or "",
                name=name or "",
                valueType=value_type or ConstantSourceType.JSON.value,
            )
    return None


def _coerce_send_message_template(value: object) -> SendMessageTemplateDto | None:
    if value is None:
        return None
    if isinstance(value, SendMessageTemplateDto):
        return value
    if isinstance(value, dict):
        return SendMessageTemplateDto(
            forEach=_first_non_empty(value, "forEach", "for_each"),
            fields=value.get("fields") or [],
            constants=value.get("constants") or [],
        )
    raise ValueError("messageTemplate must be an object.")


def _coerce_dataset_parameter_bindings(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("parameters must be an object.")
    normalized: dict[str, object] = {}
    for raw_name, raw_binding in value.items():
        parameter_name = _normalize_token(raw_name)
        if not parameter_name:
            raise ValueError("parameters keys must be non-empty strings.")
        if isinstance(raw_binding, dict):
            normalized_kind = _normalize_token(raw_binding.get("kind")).lower()
            if normalized_kind in {"constant_ref", "built_in"}:
                binding = DatasetParameterBindingDto(
                    kind=normalized_kind,
                    definitionId=_first_non_empty(raw_binding, "definitionId", "definition_id"),
                    resolver=_first_non_empty(raw_binding, "resolver"),
                )
                payload = {"kind": binding.kind}
                if binding.kind == "constant_ref":
                    payload["definitionId"] = binding.definitionId
                else:
                    payload["resolver"] = binding.resolver
                normalized[parameter_name] = payload
                continue
        normalized[parameter_name] = raw_binding
    return normalized or None


def _normalize_command_type(value: object) -> str:
    normalized = _normalize_token(value).lower()
    if normalized in {item.value for item in CommandType}:
        return normalized
    return normalized


def _normalize_command_code(value: object) -> str:
    raw = _normalize_token(value)
    if not raw:
        return ""
    legacy = raw.replace("_", "-").lower()
    legacy_mapping = {
        "data": CommandCode.SET_VARIABLE.value,
        "data-from-json-array": CommandCode.SET_VARIABLE.value,
        "data-from-db": CommandCode.SET_VARIABLE.value,
        "data-from-queue": CommandCode.SET_VARIABLE.value,
        "read-api": CommandCode.READ_API.value,
        "write-api": CommandCode.WRITE_API.value,
        "publish": CommandCode.SEND_MESSAGE_QUEUE.value,
        "save-internal-db": CommandCode.SAVE_TABLE.value,
        "save-external-db": CommandCode.EXPORT_DATASET.value,
        "run-suite": CommandCode.RUN_SUITE.value,
        "set-var": CommandCode.SET_VARIABLE.value,
        "initconstant": CommandCode.SET_VARIABLE.value,
        "deleteconstant": CommandCode.DELETE_VARIABLE.value,
    }
    return legacy_mapping.get(legacy, raw)


def _derive_assert_command_code(data: dict) -> str:
    assert_type = _normalize_token(_first_non_empty(data, "assert_type", "assertType")).replace("_", "-").lower()
    if assert_type == "equals":
        return CommandCode.JSON_EQUALS.value
    if assert_type == "empty":
        expected_json_array_id = _first_non_empty(
            data,
            "expected_json_array_id",
            "expectedJsonArrayId",
            "json_array_id",
        )
        return CommandCode.JSON_ARRAY_EMPTY.value if expected_json_array_id else CommandCode.JSON_EMPTY.value
    if assert_type == "not-empty":
        expected_json_array_id = _first_non_empty(
            data,
            "expected_json_array_id",
            "expectedJsonArrayId",
            "json_array_id",
        )
        return CommandCode.JSON_ARRAY_NOT_EMPTY.value if expected_json_array_id else CommandCode.JSON_NOT_EMPTY.value
    if assert_type == "contains":
        expected_json_array_id = _first_non_empty(
            data,
            "expected_json_array_id",
            "expectedJsonArrayId",
            "json_array_id",
        )
        return CommandCode.JSON_ARRAY_CONTAINS.value if expected_json_array_id else CommandCode.JSON_CONTAINS.value
    if assert_type == "json-array-equals":
        return CommandCode.JSON_ARRAY_EQUALS.value
    return CommandCode.JSON_EQUALS.value


class ConfigurationCommandDto(BaseModel):
    commandCode: str
    commandType: str

    @model_validator(mode="after")
    def validate_command_keys(self):
        self.commandCode = _normalize_command_code(self.commandCode)
        self.commandType = _normalize_command_type(self.commandType)
        if not self.commandCode:
            raise ValueError("commandCode is required.")
        if self.commandType not in {item.value for item in CommandType}:
            raise ValueError("commandType must be one of: context, action, assert.")
        return self


class SetVariableConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.SET_VARIABLE.value
    commandType: str = CommandType.CONTEXT.value
    definitionId: str | None = None
    name: str | None = None
    context: str | None = None
    valueType: str | None = None
    sourceType: str | None = None
    value: object = None
    data: object = None
    functionName: str | None = None
    resolver: str | None = None
    function: str | None = None
    dataset_id: str | None = None
    json_array_id: str | None = None
    parameters: dict | None = None
    target: str | None = None
    key: str | None = None
    scope: str | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.definitionId = _normalize_definition_id(self.definitionId)
        if not self.definitionId:
            raise ValueError("definitionId is required for setVariable.")
        self.target = _normalize_target_path(self.target)
        if self.target:
            target_tokens = [token for token in self.target.split(".") if token]
            if len(target_tokens) >= 3:
                self.context = self.context or target_tokens[1]
                self.name = self.name or target_tokens[-1]
        self.name = _normalize_token(self.name or self.key)
        if not self.name:
            raise ValueError("name is required for setVariable.")

        normalized_context = _normalize_token(self.context or self.scope or ConstantContext.LOCAL.value)
        normalized_context = {
            "run": ConstantContext.RUN_ENVELOPE.value,
            "vars": ConstantContext.GLOBAL.value,
            "auto": ConstantContext.LOCAL.value,
        }.get(normalized_context, normalized_context)
        if normalized_context not in {item.value for item in ConstantContext}:
            raise ValueError("context must be one of: runEnvelope, global, local, result.")
        self.context = normalized_context

        if self.value is None and self.data is not None:
            self.value = self.data

        legacy_value_type = _normalize_token(self.sourceType or self.valueType or ConstantSourceType.VALUE.value)
        if legacy_value_type in {
            ConstantSourceType.JSON_ARRAY.value,
            ConstantSourceType.DATASET.value,
        }:
            self.valueType = legacy_value_type
            self.functionName = None
            return self

        self.valueType = _normalize_value_type(legacy_value_type, allow_sources=False)
        if self.valueType == ConstantSourceType.FUNCTION.value:
            self.functionName = _normalize_token(self.functionName or self.resolver or self.function).lower()
            if self.functionName not in SUPPORTED_RUNTIME_FUNCTIONS:
                raise ValueError("functionName must be one of: now, today.")
            self.value = None
        else:
            self.functionName = None
        return self


class DeleteVariableConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.DELETE_VARIABLE.value
    commandType: str = CommandType.CONTEXT.value
    targetRuntimeValueRef: RuntimeValueRefDto | None = None
    targetConstantRef: RuntimeValueRefDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.targetRuntimeValueRef = _coerce_runtime_value_ref(
            self.targetRuntimeValueRef or self.targetConstantRef
        )
        if self.targetRuntimeValueRef is None:
            raise ValueError("targetRuntimeValueRef is required for deleteVariable.")
        return self


class SleepConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.SLEEP.value
    commandType: str = CommandType.ACTION.value
    duration: int


class ReadApiConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.READ_API.value
    commandType: str = CommandType.ACTION.value
    method: str = "GET"
    url: str
    queryParams: dict | list | None = None
    headers: dict | None = None
    pathParams: dict | None = None
    authorization: dict | None = None
    bodyType: str = HttpBodyType.JSON.value
    timeoutSeconds: int | float | None = 30
    resultConstant: ResultConstantDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.method = _normalize_http_method(self.method or "GET")
        self.url = _normalize_token(self.url)
        self.queryParams = _coerce_http_kv_params(self.queryParams)
        self.headers = _coerce_http_kv_params(self.headers)
        self.pathParams = _coerce_http_kv_params(self.pathParams)
        self.authorization = _coerce_authorization_guided(self.authorization)
        self.bodyType = _normalize_http_body_type(self.bodyType)
        self.resultConstant = _coerce_result_constant(self.resultConstant)
        if self.method != "GET":
            raise ValueError("readApi.method must be GET.")
        if not self.url:
            raise ValueError("url is required for readApi.")
        if self.timeoutSeconds is not None and float(self.timeoutSeconds) <= 0:
            raise ValueError("timeoutSeconds must be > 0.")
        return self


class WriteApiConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.WRITE_API.value
    commandType: str = CommandType.ACTION.value
    method: str
    url: str
    queryParams: dict | list | None = None
    headers: dict | None = None
    pathParams: dict | None = None
    authorization: dict | None = None
    body: object | None = None
    bodyType: str = HttpBodyType.JSON.value
    timeoutSeconds: int | float | None = 30
    resultConstant: ResultConstantDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.method = _normalize_http_method(self.method)
        self.url = _normalize_token(self.url)
        self.queryParams = _coerce_http_kv_params(self.queryParams)
        self.headers = _coerce_http_kv_params(self.headers)
        self.pathParams = _coerce_http_kv_params(self.pathParams)
        self.authorization = _coerce_authorization_guided(self.authorization)
        self.bodyType = _normalize_http_body_type(self.bodyType)
        if self.bodyType == HttpBodyType.FORM_URL_ENCODED.value:
            self.body = _coerce_http_form_body(self.body)
        else:
            self.body = _coerce_http_input_tree(self.body)
        self.resultConstant = _coerce_result_constant(self.resultConstant)
        if self.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("writeApi.method must be one of: POST, PUT, PATCH, DELETE.")
        if not self.url:
            raise ValueError("url is required for writeApi.")
        if self.timeoutSeconds is not None and float(self.timeoutSeconds) <= 0:
            raise ValueError("timeoutSeconds must be > 0.")
        return self


class SendMessageQueueConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.SEND_MESSAGE_QUEUE.value
    commandType: str = CommandType.ACTION.value
    queue_id: str
    inputRef: InputRefDto | None = None
    sourceConstantRef: RuntimeValueRefDto | None = None
    message_template: SendMessageTemplateDto | None = None
    template_id: str | None = None
    template_params: dict | None = None
    resultConstant: ResultConstantDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.inputRef = _coerce_input_ref(self.inputRef or self.sourceConstantRef)
        self.message_template = _coerce_send_message_template(self.message_template)
        self.resultConstant = _coerce_result_constant(self.resultConstant)
        if self.inputRef is None:
            raise ValueError("inputRef is required for sendMessageQueue.")
        return self


class SaveTableConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.SAVE_TABLE.value
    commandType: str = CommandType.ACTION.value
    table_name: str
    inputRef: InputRefDto | None = None
    sourceConstantRef: RuntimeValueRefDto | None = None
    resultConstant: ResultConstantDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.inputRef = _coerce_input_ref(self.inputRef or self.sourceConstantRef)
        self.resultConstant = _coerce_result_constant(self.resultConstant)
        if self.inputRef is None:
            raise ValueError("inputRef is required for saveTable.")
        return self


class DropTableConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.DROP_TABLE.value
    commandType: str = CommandType.ACTION.value
    table_name: str


class CleanTableConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.CLEAN_TABLE.value
    commandType: str = CommandType.ACTION.value
    table_name: str


class ExportDatasetConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.EXPORT_DATASET.value
    commandType: str = CommandType.ACTION.value
    connection_id: str | None = None
    table_name: str | None = None
    inputRef: InputRefDto | None = None
    sourceConstantRef: RuntimeValueRefDto | None = None
    mode: str = "append"
    mapping_keys: list[str] | None = None
    dataset_description: str | None = None
    dataset_id: str | None = None
    resultConstant: ResultConstantDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.inputRef = _coerce_input_ref(self.inputRef or self.sourceConstantRef)
        self.resultConstant = _coerce_result_constant(self.resultConstant)
        if self.inputRef is None:
            raise ValueError("inputRef is required for exportDataset.")
        normalized_mode = _normalize_token(self.mode).replace("_", "-").lower() or "append"
        if normalized_mode not in {"append", "drop-create", "insert-update"}:
            raise ValueError("mode must be one of: append, drop-create, insert-update.")
        self.mode = normalized_mode
        self.mapping_keys = _normalize_compare_keys(self.mapping_keys) or None
        return self


class DropDatasetConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.DROP_DATASET.value
    commandType: str = CommandType.ACTION.value
    dataset_id: str


class CleanDatasetConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.CLEAN_DATASET.value
    commandType: str = CommandType.ACTION.value
    dataset_id: str


class ReceiveQueueConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.RECEIVE_QUEUE.value
    commandType: str = CommandType.ACTION.value
    queue_id: str
    max_messages: int = 1
    retry: int = 3
    wait_time_seconds: int = 1
    target: str | None = None
    resultConstant: ResultConstantDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.queue_id = _normalize_token(self.queue_id)
        if not self.queue_id:
            raise ValueError("queue_id is required for receiveQueue.")
        if self.max_messages <= 0:
            raise ValueError("max_messages must be greater than zero for receiveQueue.")
        if self.retry < 0:
            raise ValueError("retry must be greater than or equal to zero for receiveQueue.")
        if self.wait_time_seconds < 0:
            raise ValueError(
                "wait_time_seconds must be greater than or equal to zero for receiveQueue."
            )
        self.target = _normalize_target_path(self.target) or None
        self.resultConstant = _coerce_result_constant(self.resultConstant)
        return self


class QueryDatabaseConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.QUERY_DATABASE.value
    commandType: str = CommandType.ACTION.value
    connection_id: str
    query: str
    target: str | None = None
    resultConstant: ResultConstantDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.connection_id = _normalize_token(self.connection_id)
        if not self.connection_id:
            raise ValueError("connection_id is required for queryDatabase.")
        normalized_query = str(self.query or "").strip()
        if not normalized_query:
            raise ValueError("query is required for queryDatabase.")
        self.query = normalized_query
        self.target = _normalize_target_path(self.target) or None
        self.resultConstant = _coerce_result_constant(self.resultConstant)
        return self


class RunSuiteConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str = CommandCode.RUN_SUITE.value
    commandType: str = CommandType.ACTION.value
    suite_id: str
    runtimeValueRefs: list[RuntimeValueRefDto] = Field(default_factory=list)
    constantRefs: list[RuntimeValueRefDto] = Field(default_factory=list)
    resultConstant: ResultConstantDto | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.suite_id = _normalize_token(self.suite_id)
        if not self.suite_id:
            raise ValueError("suite_id is required for runSuite.")
        normalized_runtime_refs: list[RuntimeValueRefDto] = []
        legacy_refs = list(self.constantRefs or [])
        for item in list(self.runtimeValueRefs or []) + legacy_refs:
            normalized = _coerce_runtime_value_ref(item)
            if normalized is not None:
                normalized_runtime_refs.append(normalized)
        self.runtimeValueRefs = normalized_runtime_refs
        self.resultConstant = _coerce_result_constant(self.resultConstant)
        return self


class AssertConfigurationCommandDto(ConfigurationCommandDto):
    commandCode: str
    commandType: str = CommandType.ASSERT.value
    error_message: str | None = None
    evaluated_object_type: str = AssertEvaluatedObjectType.JSON_DATA.value
    actualRef: InputRefDto | None = None
    actualConstantRef: RuntimeValueRefDto | None = None
    expected: object | None = None
    expectedRef: InputRefDto | None = None
    expected_json_array_id: str | None = None
    compare_keys: list[str] | None = None
    json_schema: dict | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.commandCode = _normalize_command_code(self.commandCode)
        supported_codes = {
            CommandCode.JSON_EQUALS.value,
            CommandCode.JSON_EMPTY.value,
            CommandCode.JSON_NOT_EMPTY.value,
            CommandCode.JSON_CONTAINS.value,
            CommandCode.JSON_ARRAY_EQUALS.value,
            CommandCode.JSON_ARRAY_EMPTY.value,
            CommandCode.JSON_ARRAY_NOT_EMPTY.value,
            CommandCode.JSON_ARRAY_CONTAINS.value,
        }
        if self.commandCode not in supported_codes:
            raise ValueError("Unsupported assert commandCode.")
        self.actualRef = _coerce_input_ref(self.actualRef or self.actualConstantRef)
        self.expectedRef = _coerce_input_ref(self.expectedRef)
        if self.expectedRef is None and _normalize_token(self.expected_json_array_id):
            self.expectedRef = InputRefDto(
                kind=InputRefKind.SOURCE.value,
                sourceCode=self.expected_json_array_id,
            )
        self.evaluated_object_type = _normalize_path_token(self.evaluated_object_type).lower()
        self.compare_keys = _normalize_compare_keys(self.compare_keys) or None
        if self.actualRef is None:
            raise ValueError("actualRef is required for assert commands.")
        if self.commandCode in {
            CommandCode.JSON_ARRAY_EQUALS.value,
            CommandCode.JSON_ARRAY_CONTAINS.value,
        }:
            if self.expectedRef is None:
                raise ValueError("expectedRef is required for jsonArray assert commands.")
            if not self.compare_keys:
                raise ValueError("compare_keys is required for jsonArray assert commands.")
        if self.commandCode == CommandCode.JSON_CONTAINS.value:
            if self.expected is None and self.expectedRef is None:
                raise ValueError("expected or expectedRef is required for jsonContains.")
            if not self.compare_keys:
                raise ValueError("compare_keys is required for jsonContains.")
        if self.commandCode == CommandCode.JSON_EQUALS.value and self.expected is None and self.expectedRef is None:
            raise ValueError("expected or expectedRef is required for jsonEquals.")
        return self

    @property
    def assert_type(self) -> str:
        mapping = {
            CommandCode.JSON_EQUALS.value: "equals",
            CommandCode.JSON_EMPTY.value: "empty",
            CommandCode.JSON_NOT_EMPTY.value: "not-empty",
            CommandCode.JSON_CONTAINS.value: "contains",
            CommandCode.JSON_ARRAY_EQUALS.value: "json-array-equals",
            CommandCode.JSON_ARRAY_EMPTY.value: "empty",
            CommandCode.JSON_ARRAY_NOT_EMPTY.value: "not-empty",
            CommandCode.JSON_ARRAY_CONTAINS.value: "json-array-contains",
        }
        return mapping[self.commandCode]


ConfigurationCommandTypes = (
    SetVariableConfigurationCommandDto
    | DeleteVariableConfigurationCommandDto
    | SleepConfigurationCommandDto
    | ReadApiConfigurationCommandDto
    | WriteApiConfigurationCommandDto
    | SendMessageQueueConfigurationCommandDto
    | SaveTableConfigurationCommandDto
    | DropTableConfigurationCommandDto
    | CleanTableConfigurationCommandDto
    | ExportDatasetConfigurationCommandDto
    | DropDatasetConfigurationCommandDto
    | CleanDatasetConfigurationCommandDto
    | ReceiveQueueConfigurationCommandDto
    | QueryDatabaseConfigurationCommandDto
    | RunSuiteConfigurationCommandDto
    | AssertConfigurationCommandDto
)


def convert_to_config_operation_type(data: dict):
    return convert_to_config_command_type(data)


def convert_to_config_command_type(data: dict):
    command_code = _normalize_command_code(
        _first_non_empty(data, "commandCode", "command_code", "operationType", "operation_type", "type")
    )
    if command_code == "assert":
        command_code = _derive_assert_command_code(data)
    command_type = _normalize_command_type(_first_non_empty(data, "commandType", "command_type"))

    if command_code == CommandCode.SET_VARIABLE.value:
        function_name = _first_non_empty(data, "functionName", "function_name")
        legacy_source_type = _first_non_empty(data, "sourceType", "source_type")
        if str(legacy_source_type or "").strip() in {"raw", "value"}:
            legacy_source_type = ConstantSourceType.VALUE.value
        elif str(legacy_source_type or "").strip() == "json":
            legacy_source_type = ConstantSourceType.JSON.value
        elif str(legacy_source_type or "").strip() == "function":
            legacy_source_type = ConstantSourceType.FUNCTION.value
        return SetVariableConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.CONTEXT.value,
            definitionId=_first_non_empty(data, "definitionId", "definition_id"),
            name=_first_non_empty(data, "name", "key"),
            context=_first_non_empty(data, "context", "scope"),
            valueType=_first_non_empty(data, "valueType", "value_type") or legacy_source_type,
            value=_first_non_empty(data, "value", "data"),
            functionName=function_name or _first_non_empty(data, "resolver", "function"),
            target=_first_non_empty(data, "target"),
            key=_first_non_empty(data, "key"),
            scope=_first_non_empty(data, "scope"),
        )
    if command_code == CommandCode.DELETE_VARIABLE.value:
        return DeleteVariableConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.CONTEXT.value,
            targetRuntimeValueRef=_first_non_empty(
                data,
                "targetRuntimeValueRef",
                "target_runtime_value_ref",
                "targetConstantRef",
                "target_constant_ref",
            ),
        )
    if command_code == CommandCode.SLEEP.value:
        return SleepConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            duration=int(_first_non_empty(data, "duration") or 0),
        )
    if command_code == CommandCode.READ_API.value:
        return ReadApiConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            method=_first_non_empty(data, "method") or "GET",
            url=_first_non_empty(data, "url"),
            queryParams=_first_non_empty(data, "queryParams", "query_params"),
            headers=_first_non_empty(data, "headers"),
            pathParams=_first_non_empty(data, "pathParams", "path_params"),
            authorization=_first_non_empty(data, "authorization"),
            bodyType=_first_non_empty(data, "bodyType", "body_type") or HttpBodyType.JSON.value,
            timeoutSeconds=_first_non_empty(data, "timeoutSeconds", "timeout_seconds") or 30,
            resultConstant=_first_non_empty(data, "resultConstant", "result_constant"),
        )
    if command_code == CommandCode.WRITE_API.value:
        return WriteApiConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            method=_first_non_empty(data, "method"),
            url=_first_non_empty(data, "url"),
            queryParams=_first_non_empty(data, "queryParams", "query_params"),
            headers=_first_non_empty(data, "headers"),
            pathParams=_first_non_empty(data, "pathParams", "path_params"),
            authorization=_first_non_empty(data, "authorization"),
            body=_first_non_empty(data, "body"),
            bodyType=_first_non_empty(data, "bodyType", "body_type") or HttpBodyType.JSON.value,
            timeoutSeconds=_first_non_empty(data, "timeoutSeconds", "timeout_seconds") or 30,
            resultConstant=_first_non_empty(data, "resultConstant", "result_constant"),
        )
    if command_code == CommandCode.SEND_MESSAGE_QUEUE.value:
        return SendMessageQueueConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            queue_id=_first_non_empty(data, "queue_id", "queueId"),
            inputRef=_first_non_empty(data, "inputRef", "input_ref", "sourceConstantRef", "source_constant_ref"),
            message_template=_first_non_empty(data, "message_template", "messageTemplate"),
            template_id=_first_non_empty(data, "template_id", "templateId"),
            template_params=_first_non_empty(data, "template_params", "templateParams"),
            resultConstant=_first_non_empty(data, "resultConstant", "result_constant"),
        )
    if command_code == CommandCode.SAVE_TABLE.value:
        return SaveTableConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            table_name=_first_non_empty(data, "table_name", "tableName"),
            inputRef=_first_non_empty(data, "inputRef", "input_ref", "sourceConstantRef", "source_constant_ref"),
            resultConstant=_first_non_empty(data, "resultConstant", "result_constant"),
        )
    if command_code == CommandCode.DROP_TABLE.value:
        return DropTableConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            table_name=_first_non_empty(data, "table_name", "tableName"),
        )
    if command_code == CommandCode.CLEAN_TABLE.value:
        return CleanTableConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            table_name=_first_non_empty(data, "table_name", "tableName"),
        )
    if command_code == CommandCode.EXPORT_DATASET.value:
        return ExportDatasetConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            connection_id=_first_non_empty(data, "connection_id", "connectionId", "dataset_id", "datasetId"),
            table_name=_first_non_empty(data, "table_name", "tableName"),
            inputRef=_first_non_empty(data, "inputRef", "input_ref", "sourceConstantRef", "source_constant_ref"),
            mode=_first_non_empty(data, "mode", "export_mode", "exportMode") or "append",
            mapping_keys=_normalize_compare_keys(_first_non_empty(data, "mapping_keys", "mappingKeys")),
            dataset_description=_first_non_empty(data, "dataset_description", "datasetDescription"),
            dataset_id=_first_non_empty(data, "dataset_id", "datasetId"),
            resultConstant=_first_non_empty(data, "resultConstant", "result_constant"),
        )
    if command_code == CommandCode.DROP_DATASET.value:
        return DropDatasetConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            dataset_id=_first_non_empty(data, "dataset_id", "datasetId"),
        )
    if command_code == CommandCode.CLEAN_DATASET.value:
        return CleanDatasetConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            dataset_id=_first_non_empty(data, "dataset_id", "datasetId"),
        )
    if command_code == CommandCode.RUN_SUITE.value:
        return RunSuiteConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            suite_id=_first_non_empty(data, "suite_id", "suiteId"),
            runtimeValueRefs=_first_non_empty(data, "runtimeValueRefs", "runtime_value_refs", "constantRefs", "constant_refs") or [],
            resultConstant=_first_non_empty(data, "resultConstant", "result_constant"),
        )
    if command_code == CommandCode.RECEIVE_QUEUE.value:
        return ReceiveQueueConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            queue_id=_first_non_empty(data, "queue_id", "queueId"),
            max_messages=_first_non_empty(data, "max_messages", "maxMessages") or 1,
            retry=_first_non_empty(data, "retry") or 3,
            wait_time_seconds=_first_non_empty(
                data, "wait_time_seconds", "waitTimeSeconds"
            ) or 1,
            target=_first_non_empty(data, "target"),
            resultConstant=_first_non_empty(data, "resultConstant", "result_constant"),
        )
    if command_code == CommandCode.QUERY_DATABASE.value:
        return QueryDatabaseConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ACTION.value,
            connection_id=_first_non_empty(data, "connection_id", "connectionId"),
            query=_first_non_empty(data, "query", "sql"),
            target=_first_non_empty(data, "target"),
            resultConstant=_first_non_empty(data, "resultConstant", "result_constant"),
        )
    if command_code in {
        CommandCode.JSON_EQUALS.value,
        CommandCode.JSON_EMPTY.value,
        CommandCode.JSON_NOT_EMPTY.value,
        CommandCode.JSON_CONTAINS.value,
        CommandCode.JSON_ARRAY_EQUALS.value,
        CommandCode.JSON_ARRAY_EMPTY.value,
        CommandCode.JSON_ARRAY_NOT_EMPTY.value,
        CommandCode.JSON_ARRAY_CONTAINS.value,
    }:
        expected_json_array_id = _first_non_empty(
            data,
            "expected_json_array_id",
            "expectedJsonArrayId",
            "json_array_id",
        )
        expected_ref = _first_non_empty(data, "expectedRef", "expected_ref")
        if expected_ref is None and expected_json_array_id:
            expected_ref = {"kind": InputRefKind.SOURCE.value, "sourceCode": expected_json_array_id}
        return AssertConfigurationCommandDto(
            commandCode=command_code,
            commandType=command_type or CommandType.ASSERT.value,
            error_message=_first_non_empty(data, "error_message", "errorMessage"),
            evaluated_object_type=_first_non_empty(
                data,
                "evaluated_object_type",
                "evaluetedObjectType",
                "evaluatedObjectType",
            ) or AssertEvaluatedObjectType.JSON_DATA.value,
            actualRef=_first_non_empty(data, "actualRef", "actual_ref", "actualConstantRef", "actual_constant_ref"),
            expected=_first_non_empty(data, "expected"),
            expectedRef=expected_ref,
            compare_keys=_normalize_compare_keys(_first_non_empty(data, "compare_keys", "compareKeys")),
            json_schema=_first_non_empty(data, "json_schema", "jsonSchema"),
        )
    raise ValueError(f"Unsupported command code: {command_code}")


# Backward import aliases used by the current codebase during the refactor.
ConfigurationOperationDto = ConfigurationCommandDto
ConfigurationOperationTypes = ConfigurationCommandTypes
InitConstantConfigurationCommandDto = SetVariableConfigurationCommandDto
DeleteConstantConfigurationCommandDto = DeleteVariableConfigurationCommandDto
DataConfigurationOperationDto = SetVariableConfigurationCommandDto
DataFromJsonArrayConfigurationOperationDto = SetVariableConfigurationCommandDto
DataFromDbConfigurationOperationDto = SetVariableConfigurationCommandDto
DataFromQueueConfigurationOperationDto = SetVariableConfigurationCommandDto
SleepConfigurationOperationDto = SleepConfigurationCommandDto
PublishConfigurationOperationDto = SendMessageQueueConfigurationCommandDto
SaveInternalDBConfigurationOperationDto = SaveTableConfigurationCommandDto
SaveToExternalDBConfigurationOperationDto = ExportDatasetConfigurationCommandDto
RunSuiteConfigurationOperationDto = RunSuiteConfigurationCommandDto
SetVarConfigurationOperationDto = SetVariableConfigurationCommandDto
AssertConfigurationOperationDto = AssertConfigurationCommandDto
SetResponseStatusConfigurationOperationDto = ConfigurationCommandDto
SetResponseHeaderConfigurationOperationDto = ConfigurationCommandDto
SetResponseBodyConfigurationOperationDto = ConfigurationCommandDto
BuildResponseFromTemplateConfigurationOperationDto = ConfigurationCommandDto
