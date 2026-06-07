from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationOperationDto,
)


@dataclass
class AssertEvaluationContext:
    session: Session
    cfg: AssertConfigurationOperationDto
    data: list[dict]
    actual: object | None = None
    expected: object | None = None


class AssertEvaluator(ABC):
    @abstractmethod
    def evaluate(self, context: AssertEvaluationContext) -> None:
        raise NotImplementedError

