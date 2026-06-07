from typing import Any

from pydantic import BaseModel


class QueueMessagesDto(BaseModel):
    messages: list[Any]