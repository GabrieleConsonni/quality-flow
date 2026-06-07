from enum import Enum


class OnFailure(str,Enum):
    CONTINUE = "CONTINUE"
    ABORT = "ABORT"
