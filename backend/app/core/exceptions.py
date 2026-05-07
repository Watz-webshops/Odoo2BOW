from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 400, context: dict | None = None):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.context = context or {}
        super().__init__(message)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    body = {"error_code": exc.error_code, "message": exc.message}
    if exc.context:
        body["context"] = exc.context
    return JSONResponse(status_code=exc.status_code, content=body)
