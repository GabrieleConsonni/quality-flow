import contextvars
from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    user_id: str
    tenant_id: str


_current_user_ctx: contextvars.ContextVar[Optional["User"]] = contextvars.ContextVar(
    "current_user_ctx", default=None
)


def init_current_user_ctx(user: User | None):
    _current_user_ctx.set(user)


def get_current_user_ctx() -> User:
    user = _current_user_ctx.get()
    if user is None:
        raise RuntimeError(
            "current_user_ctx non inizializzato. Chiama init_current_user_ctx() prima."
        )
    return user
