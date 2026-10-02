import os

import pytest

#  应用于本文件中所有测试函数的装饰器。
pytestmark = [
    pytest.mark.integration,  # 标记为集成测试。
    # 如果环境变量RUN_LLM_TESTS不为1、true或yes，跳过测试。
    pytest.mark.skipif(
        os.getenv("RUN_LLM_TESTS", "").lower() not in ("1", "true", "yes"),  
        reason="Calls Ollama; set RUN_LLM_TESTS=1 to run these tests",
    ),
]


@pytest.fixture
def extract_action_items_llm():
    pytest.importorskip("ollama")  # 如果ollama模块不存在，跳过测试。
    from ..app.services.extract import extract_action_items_llm as fn

    return fn


def test_extract_bullets_and_checkboxes(extract_action_items_llm):
    text = """
    Notes from meeting:
    - [ ] Set up database
    * implement API extract endpoint1
    • implement API extract endpoint2
    1. Write tests
    2.implement API extract endpoint3
    [todo] implement API extract endpoint4
    Some narrative sentence.
    """.strip()

    items = extract_action_items_llm(text)  # 这里调用的是函数参数extract_action_items_llm，而不是fixture
    assert "Set up database" in items
    assert "implement API extract endpoint1" in items
    assert "implement API extract endpoint2" in items
    assert "Write tests" in items
    assert "implement API extract endpoint3" in items
    assert "implement API extract endpoint4" in items
    assert "Some narrative sentence." not in items


def test_extract_action_keyword_prefixed_lines(extract_action_items_llm):
    text = """
    TODO: write tests
    ACTION: review PR
    NEXT: implement API extract endpoint
    Ship it!
    """.strip()
    items = extract_action_items_llm(text)
    assert "TODO: write tests" in items
    assert "ACTION: review PR" in items
    assert "NEXT: implement API extract endpoint" in items
    assert "Ship it!" not in items  # 没有明确列表项或者关键词前缀的情况下,检查是否以特定动词开头


def test_extract_action_fallback_heuristic(extract_action_items_llm):
    text = """
    Implement API extract endpoint
    Review PR
    Check tests
    Verify implementation
    Refactor code
    """.strip()
    items = extract_action_items_llm(text)
    assert "Review PR" in items
    assert "Check tests" in items
    assert "Verify implementation" in items
    assert "Refactor code" in items
    assert "Changes in document" not in items
    assert "Implement API extract endpoint" in items