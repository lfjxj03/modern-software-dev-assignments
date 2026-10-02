"""Pydantic models for /action-items API contracts."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

#  POST /action-items/extract请求的请求体数据模型
#  FastAPI会在 请求到达路由处理函数之前 自动将请求体转换为ExtractRequest对象，
#    并验证请求体是否符合ExtractRequest的定义
class ExtractRequest(BaseModel):
    """POST /action-items/extract request body."""

    model_config = ConfigDict(str_strip_whitespace=True)  # 自动去除请求体中的前导和尾随空白字符

    # 校验失败时，会返回422状态码，并返回错误信息
    text: str = Field(
        ...,
        min_length=1,
        description=(
            "Source text to extract action items from. "
            "Leading and trailing whitespace is stripped before validation."
        ),
    )
    save_note: bool = Field(
        default=False,
        description="If true, persist the source text as a note before extraction.",
    )


class ExtractedActionItem(BaseModel):
    """One extracted item returned from extract (id assigned after DB insert)."""

    id: int = Field(..., description="Database id of the action_items row.")
    text: str = Field(..., description="Post-processed action item text.")


class ExtractResponse(BaseModel):
    """POST /action-items/extract response body."""

    note_id: Optional[int] = Field(
        default=None,
        description="Id of the saved note when save_note was true; otherwise null.",
    )
    items: list[ExtractedActionItem] = Field(
        default_factory=list,
        description="Inserted action items with ids.",
    )


class ActionItemOut(BaseModel):
    """Single action item in GET /action-items list."""

    id: int
    note_id: Optional[int] = None
    text: str
    done: bool
    created_at: str = Field(..., description="ISO-like timestamp string from SQLite.")


class MarkActionItemDoneRequest(BaseModel):
    """POST /action-items/{id}/done request body."""

    done: bool = Field(default=True, description="Whether the item is marked done.")


class MarkActionItemDoneResponse(BaseModel):
    """POST /action-items/{id}/done response body."""

    id: int
    done: bool
