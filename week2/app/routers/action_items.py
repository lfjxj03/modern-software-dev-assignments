# 定义action_items的API路由，包括：
# 启发式/LLM提取、标记完成、获取所有action_items

from __future__ import annotations

from typing import Callable, List, Optional

from fastapi import APIRouter, HTTPException

from .. import db
from ..schemas import (
    ActionItemOut,
    ExtractedActionItem,
    ExtractRequest,
    ExtractResponse,
    MarkActionItemDoneRequest,
    MarkActionItemDoneResponse,
)
from ..services.extract import (
    ExtractionError,
    extract_action_items,
    extract_action_items_llm,
)


router = APIRouter(prefix="/action-items", tags=["action-items"])


def _persist_extracted(text: str, save_note: bool, items: list[str]) -> ExtractResponse:
    note_id: Optional[int] = None
    # 先可选落库；抽取失败时这条 note 仍会留下（本轮不做回滚）。
    if save_note:
        note_id = db.insert_note(text)
    ids = db.insert_action_items(items, note_id=note_id)
    return ExtractResponse(
        note_id=note_id,
        items=[ExtractedActionItem(id=i, text=t) for i, t in zip(ids, items)],
    )


def _extract_with(
    payload: ExtractRequest,
    extractor: Callable[[str], list[str]],
    *,
    wrap_llm_errors: bool,
) -> ExtractResponse:
    note_id: Optional[int] = None
    if payload.save_note:
        note_id = db.insert_note(payload.text)
    try:
        items = extractor(payload.text)
    except ExtractionError:
        if wrap_llm_errors:
            raise HTTPException(status_code=503, detail="extraction failed") from None
        raise
    ids = db.insert_action_items(items, note_id=note_id)
    return ExtractResponse(
        note_id=note_id,
        items=[ExtractedActionItem(id=i, text=t) for i, t in zip(ids, items)],
    )


# 对应本地路径http://localhost:8000/action-items/extract
@router.post("/extract", response_model=ExtractResponse)
def extract(payload: ExtractRequest) -> ExtractResponse:
    return _extract_with(payload, extract_action_items, wrap_llm_errors=False)


# 对应本地路径http://localhost:8000/action-items/extract-llm
@router.post("/extract-llm", response_model=ExtractResponse)
def extract_llm(payload: ExtractRequest) -> ExtractResponse:
    return _extract_with(payload, extract_action_items_llm, wrap_llm_errors=True)


# 对应本地路径http://localhost:8000/action-items
@router.get("", response_model=List[ActionItemOut])
def list_all(note_id: Optional[int] = None) -> List[ActionItemOut]:
    rows = db.list_action_items(note_id=note_id)
    return [
        ActionItemOut(
            id=r["id"],
            note_id=r["note_id"],
            text=r["text"],
            done=bool(r["done"]),
            created_at=str(r["created_at"]),
        )
        for r in rows
    ]


# 对应本地路径http://localhost:8000/action-items/{action_item_id}/done
@router.post("/{action_item_id}/done", response_model=MarkActionItemDoneResponse)
def mark_done(
    action_item_id: int,
    payload: MarkActionItemDoneRequest,
) -> MarkActionItemDoneResponse:
    if not db.mark_action_item_done(action_item_id, payload.done):
        raise HTTPException(status_code=404, detail="action item not found")
    return MarkActionItemDoneResponse(id=action_item_id, done=payload.done)
