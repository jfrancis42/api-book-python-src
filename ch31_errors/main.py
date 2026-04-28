"""Chapter 29: Consistent error responses via custom exception handlers."""
import sys
sys.path.insert(0, ".")

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import orm_models, database
from routers import users, repos, issues

orm_models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Mini-GitHub", version="0.9.0")


# ---------------------------------------------------------------------------
# Custom exception handlers — every error uses the same JSON shape
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
        headers=getattr(exc, "headers", None) or {},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation failed",
            "status_code": 422,
            "errors": errors,
        },
    )


app.include_router(users.router)
app.include_router(repos.router)
app.include_router(issues.router)
