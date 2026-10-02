# 定义notes的API路由，包括：
# 创建note、列出全部notes、获取单个note

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from .. import db
from ..schemas import NoteCreateRequest, NoteOut


router = APIRouter(prefix="/notes", tags=["notes"])


def _note_out(row) -> NoteOut:
    return NoteOut(
        id=row["id"],
        content=row["content"],
        created_at=str(row["created_at"]),
    )


# 对应本地路径http://localhost:8000/notes
@router.post("", response_model=NoteOut)
def create_note(payload: NoteCreateRequest) -> NoteOut:
    note_id = db.insert_note(payload.content)
    note = db.get_note(note_id)
    if note is None:
        raise HTTPException(status_code=500, detail="note not found after insert")
    return _note_out(note)


# 对应本地路径http://localhost:8000/notes （须写在 /{note_id} 之前）
@router.get("", response_model=List[NoteOut])
def list_notes() -> List[NoteOut]:
    return [_note_out(row) for row in db.list_notes()]


# 对应本地路径http://localhost:8000/notes/{note_id}
@router.get("/{note_id}", response_model=NoteOut)
def get_single_note(note_id: int) -> NoteOut:
    row = db.get_note(note_id)
    if row is None:
        raise HTTPException(status_code=404, detail="note not found")
    return _note_out(row)
