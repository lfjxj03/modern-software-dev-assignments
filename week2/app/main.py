from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import init_db
from .routers import action_items, notes


# 建表放在应用启动阶段，避免 import main 时产生副作用。
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


#  应用主程序，使用FastAPI框架
app = FastAPI(title=get_settings().app_title, lifespan=lifespan)


# 定义RequestValidationError异常处理函数，当请求体验证失败时，会调用这个函数
@app.exception_handler(RequestValidationError)
def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """422 with a short message for empty/missing text or content (matches former 400 wording)."""
    errors = exc.errors()
    if len(errors) == 1:
        err = errors[0]
        loc = tuple(err.get("loc", ()))
        typ = err.get("type", "")
        if loc and loc[-1] == "text" and typ in ("missing", "string_too_short"):
            return JSONResponse(
                status_code=422,
                content={"detail": "text is required"},
            )
        if loc and loc[-1] == "content" and typ in ("missing", "string_too_short"):
            return JSONResponse(
                status_code=422,
                content={"detail": "content is required"},
            )
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    html_path = get_settings().frontend_dir / "index.html"
    return html_path.read_text(encoding="utf-8")


app.include_router(notes.router)
app.include_router(action_items.router)


app.mount(
    "/static",
    StaticFiles(directory=str(get_settings().frontend_dir)),
    name="static",
)