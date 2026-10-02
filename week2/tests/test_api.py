from __future__ import annotations

from unittest.mock import patch

from ..app.routers import action_items as action_items_router
from ..app.services.extract import ExtractionError


# 测试提取action_items成功时的返回值形状
# 使用patch.object装饰器，模拟extract_action_items_llm函数返回值为["Alpha", "Beta"]
@patch.object(action_items_router, "extract_action_items_llm", return_value=["Alpha", "Beta"])
def test_extract_success_shape(mock_llm, client):  # patch 管 mock_llm，fixture 管 client
    r = client.post(
        "/action-items/extract-llm",
        json={"text": "some note", "save_note": False},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["note_id"] is None  # 因为save_note为False，所以note_id为None
    assert len(data["items"]) == 2  # 因为extract_action_items_llm返回了2个action_items
    assert {data["items"][0]["text"], data["items"][1]["text"]} == {"Alpha", "Beta"}  # 因为extract_action_items_llm返回了2个action_items
    assert "id" in data["items"][0]  # 因为action_item对象列表中每个action_item都有id字段


@patch.object(action_items_router, "extract_action_items_llm", side_effect=ExtractionError("model down"))
def test_extract_llm_failure_503(mock_llm, client):
    r = client.post(
        "/action-items/extract-llm",
        json={"text": "some note", "save_note": False},
    )
    assert r.status_code == 503
    assert r.json() == {"detail": "extraction failed"}


# 测试提取action_items成功时，save_note为True时的返回值形状
@patch.object(action_items_router, "extract_action_items_llm", return_value=["Only"])
def test_extract_with_save_note_sets_note_id(mock_llm, client):
    r = client.post(
        "/action-items/extract-llm",
        json={"text": "persist me", "save_note": True},
    )
    assert r.status_code == 200
    data = r.json()  # 把body转换为字典
    assert data["note_id"] is not None
    note = client.get(f"/notes/{data['note_id']}")
    assert note.status_code == 200
    assert note.json()["content"] == "persist me"


# 测试提取action_items失败时，text为空时的返回值形状
# 这部分测试对应了app.main.py中的validation_exception_handler函数
# 以及FastAPI根据schemas.py中的ExtractRequest模型进行请求体验证的功能
def test_extract_empty_text_422_friendly_detail(client):
    r = client.post("/action-items/extract", json={"text": "", "save_note": False})
    assert r.status_code == 422
    assert r.json() == {"detail": "text is required"}


def test_extract_whitespace_only_text_422_friendly_detail(client):
    r = client.post("/action-items/extract", json={"text": "   \n\t  ", "save_note": False})
    assert r.status_code == 422
    assert r.json() == {"detail": "text is required"}


def test_extract_missing_text_422_friendly_detail(client):
    r = client.post("/action-items/extract", json={"save_note": False})
    assert r.status_code == 422
    assert r.json() == {"detail": "text is required"}


def test_create_note_empty_content_422_friendly_detail(client):
    r = client.post("/notes", json={"content": ""})
    assert r.status_code == 422
    assert r.json() == {"detail": "content is required"}


def test_create_note_missing_content_422_friendly_detail(client):
    r = client.post("/notes", json={})
    assert r.status_code == 422
    assert r.json() == {"detail": "content is required"}


def test_get_note_not_found(client):
    r = client.get("/notes/999999")
    assert r.status_code == 404


@patch.object(action_items_router, "extract_action_items_llm", return_value=["Task"])
def test_mark_action_item_done(mock_llm, client):
    ex = client.post(
        "/action-items/extract-llm",
        json={"text": "x", "save_note": False},
    )
    assert ex.status_code == 200
    item_id = ex.json()["items"][0]["id"]

    r = client.post(f"/action-items/{item_id}/done", json={"done": True})
    assert r.status_code == 200
    assert r.json() == {"id": item_id, "done": True}

    listed = client.get("/action-items")
    assert listed.status_code == 200
    row = next(x for x in listed.json() if x["id"] == item_id)
    assert row["done"] is True


def test_mark_action_item_done_not_found(client):
    r = client.post("/action-items/999999/done", json={"done": True})
    assert r.status_code == 404
    assert r.json() == {"detail": "action item not found"}


def test_list_notes_empty(client):
    r = client.get("/notes")
    assert r.status_code == 200
    assert r.json() == []


def test_list_notes_returns_created(client):
    created = client.post("/notes", json={"content": "hello list"})
    assert created.status_code == 200
    r = client.get("/notes")
    assert r.status_code == 200
    contents = [n["content"] for n in r.json()]
    assert "hello list" in contents
