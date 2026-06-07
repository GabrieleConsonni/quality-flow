from fastapi import Request
from fastapi.responses import JSONResponse
from exceptions.app_exception import QualityFlowAppException


async def app_exception_handler(request: Request, exc: QualityFlowAppException):

    print(exc)

    return JSONResponse(
        status_code=500,
        content={"detail": exc.message}
    )

async def generic_exception_handler(request: Request, exc: Exception):

    print(exc)

    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )