from typing import Any

from pydantic import BaseModel, ConfigDict


class PreviewSendMessageTemplateRowsDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_data: Any = None
    source_type: str = ""
    for_each: Any = None
