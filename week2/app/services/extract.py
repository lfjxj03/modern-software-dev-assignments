from __future__ import annotations

import os
import re
from typing import List
import json
from typing import Any
from ollama import chat
from dotenv import load_dotenv

load_dotenv()

BULLET_PREFIX_PATTERN = re.compile(r"^\s*([-*•]|\d+\.)\s+")
KEYWORD_PREFIXES = (
    "todo:",
    "action:",
    "next:",
)


def _is_action_line(line: str) -> bool:
    """
    明确的列表项的检查:Check if a line looks like an action item according to the predefined heuristics, including 
    bullet points(列表项), keyword prefixes, and checkbox markers(复选框标记).
    """
    stripped = line.strip().lower()
    if not stripped:
        return False
    if BULLET_PREFIX_PATTERN.match(stripped):
        return True
    if any(stripped.startswith(prefix) for prefix in KEYWORD_PREFIXES):
        return True
    if "[ ]" in stripped or "[todo]" in stripped:
        return True
    return False


def extract_action_items(text: str) -> List[str]:
    # 分行处理
    lines = text.splitlines()
    extracted: List[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        # Check if the line looks like an action item
        if _is_action_line(line):
            cleaned = BULLET_PREFIX_PATTERN.sub("", line)  # 去掉列表项
            cleaned = cleaned.strip()  # 去掉空白字符
            # Trim common checkbox markers
            cleaned = cleaned.removeprefix("[ ]").strip()  # 去掉复选框标记
            cleaned = cleaned.removeprefix("[todo]").strip()  # 去掉复选框标记
            extracted.append(cleaned)  # 添加到结果列表
    # Fallback(备用方案): if nothing matched, heuristically split into sentences and pick imperative-like ones
    if not extracted:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())  # 按句号、感叹号、问号分割
        for sentence in sentences:
            s = sentence.strip()  # 去掉空白字符
            if not s:
                continue
            if _looks_imperative(s):  # 如果句子看起来像是一个命令（动词开头）
                extracted.append(s)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: List[str] = []
    for item in extracted:
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)  # 去重保留的是lowered的版本
        unique.append(item)  # 添加到结果列表的是item的原始版本
    return unique


def _looks_imperative(sentence: str) -> bool:
    """
    没有明确列表项的情况下,检查是否以特定动词开头:Check if a sentence looks like an imperative.
    """
    words = re.findall(r"[A-Za-z']+", sentence)  # 分词
    if not words:
        return False
    first = words[0]
    # 粗略的启发式: 将这些视为命令开头
    # Crude heuristic: treat these as imperative starters
    imperative_starters = {
        "add",
        "create",
        "implement",
        "fix",
        "update",
        "write",
        "check",
        "verify",
        "refactor",
        "document",
        "design",
        "investigate",
    }
    return first.lower() in imperative_starters

# Todo 1: implement an LLM-powered alternative, extract_action_items_llm(), that utilizes Ollama to perform action item 
# extraction via a large language model.
SYSTEM_PROMPT = """
You are a helpful assistant that extracts action items from text. You should use the predefined heuristics 
to extract action items. Here are the predefined heuristics:
- Bullet points:
Treat a line as an action item if it starts with a bullet point, such as -, *, •, or a numbered list like 1. followed by at least one space.
- Keyword prefixes:
Treat a line as an action item if it starts with keyword prefixes like todo:, action:, or next: (case‑insensitive).
- Checkbox markers:
Treat a line as an action item if it contains checkbox markers such as [ ] or [todo]. 
- Fallback heuristic:
If no lines match the above rules, split the text into sentences and select sentences start with verbs 
like add, create, implement, fix, update, write, check, verify, refactor, document, design, or investigate.

The post‑processing steps are:Remove bullet and checkbox markers prefixes from the extracted text, then deduplicate 
items in a case‑insensitive way while preserving their original order.

Respond only with structured data.
"""

def extract_action_items_llm(text: str) -> List[str]:
    response = chat(
        model="llama3.1:8b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        format={
            "type": "array",
            "items": {
                "type": "string"
            }  # 定义返回的数组项类型为字符串
        }
    )
    # Parse the response as a JSON array of strings
    return json.loads(response.message.content)