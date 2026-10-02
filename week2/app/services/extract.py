"""
This module contains the functions to extract action items from text.
Using predefined heuristics:
- Bullet points:
Treat a line as an action item if it starts with a bullet point, such as -, *, •, or a numbered list like 1. followed by at least one space.
- Keyword prefixes:
Treat a line as an action item if it starts with keyword prefixes like todo:, action:, or next: (case‑insensitive).
- Checkbox markers:
Treat a line as an action item if it contains checkbox markers such as [ ] or [todo]. 
- Fallback heuristic:
If no lines match the above rules, split the text into sentences and select sentences start with verbs 
like add, create, implement, fix, update, write, check, verify, refactor, document, design, or investigate.
"""


from __future__ import annotations

import re
from typing import List
import json
from ollama import chat

from ..config import get_settings

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
    if "[ ]" in stripped or "[todo]" in stripped:  # 注意这里只是检查是否包含, 而不是以它们开头
        return True
    return False


def extract_action_items(text: str) -> List[str]:
    # 分行处理
    lines = text.splitlines()
    extracted: List[str] = []  # 赋初值的同时声明类型
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        # Check if the line looks like an action item
        if _is_action_line(line):
            cleaned = BULLET_PREFIX_PATTERN.sub("", line)  # 去掉行首列表项
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
    没有明确列表项或者关键词前缀的情况下,检查是否以特定动词开头:Check if a sentence looks like an imperative.
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
You are a helpful assistant that extracts action items from text.

Follow this 2-step process:

Step 1 — Identify raw action items
1. Read the user text carefully.
2. Using ONLY the following heuristics, identify and collect all lines or sentences that are action items, without changing their content yet:
   - Bullet points:
     Treat a line as an action item if it starts with a bullet point, such as "-", "*", "•", or a numbered list like "1." followed by at least one space.
   - Keyword prefixes:
     Treat a line as an action item if it starts with keyword prefixes like "todo:", "action:", or "next:" (case-insensitive).
   - Checkbox markers:
     Treat a line as an action item if it contains checkbox markers such as "[ ]" or "[todo]".
   - Fallback heuristic:
     If no lines match the above rules, split the text into sentences and select sentences that start with verbs such as "add", "create", "implement", "fix", "update", "write", "check", "verify", "refactor", "document", "design", or "investigate".

Step 2 — Strict post-processing of raw items (HIGH PRIORITY)
For each raw action item string, apply ALL of the following rules, and ONLY these rules:
1. Remove ONLY these leading prefixes when present:
   - Bullet markers: "-", "*", "•", or numbered markers like "1.", "2.", etc. (and one following space)
   - Checkbox markers: "[ ]" or "[todo]" (and one following space)
2. Keyword prefixes MUST be preserved exactly:
   - "TODO:", "ACTION:", "NEXT:" and any case variants such as "todo:", "Action:", etc.
   - NEVER delete or alter these keyword prefixes.
3. Apart from removing the bullet/checkbox prefixes above and trimming surrounding whitespace, DO NOT delete, insert, rewrite, or paraphrase any character.
4. If a line starts with a keyword prefix and has no bullet/checkbox prefix to remove, the output must be exactly the same text (except surrounding whitespace trim).
5. When in doubt, keep more original characters; never remove keyword prefixes.

Critical examples for Step 2 (raw -> final):
- Raw: "TODO: update API docs"
  Final: "TODO: update API docs"
- Raw: "[ ] TODO: update API docs"
  Final: "TODO: update API docs"
- Raw: "Action: review PR"
  Final: "Action: review PR"
- Raw: "todo: implement login feature"
  Final: "todo: implement login feature"

Forbidden transformations (WRONG):
- Raw: "TODO: update API docs" -> "update API docs"
- Raw: "Action: review PR" -> "review PR"
- Raw: "todo: implement login feature3" -> "todo: implement login feature"

Output format
- Respond ONLY with a JSON array of strings, where each string is one post-processed action item.
- Do NOT include explanations, comments, or any other text outside the JSON array.

Think through Steps 1 and 2 carefully, but only output the final JSON array.
"""


class ExtractionError(Exception):
    """Raised when the LLM call or its JSON payload cannot be used."""


def extract_action_items_llm(text: str) -> List[str]:
    try:
        response = chat(
            model=get_settings().ollama_model,
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
        raw = response.message.content
        if not isinstance(raw, str) or not raw.strip():
            raise ExtractionError("empty model response")
        items = json.loads(raw)
    except ExtractionError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError, OSError) as exc:
        raise ExtractionError("model call or JSON parse failed") from exc
    except Exception as exc:
        raise ExtractionError("model call failed") from exc

    if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
        raise ExtractionError("model response is not a JSON array of strings")

    # 去重：大小写不同视为重复，保留首次出现的原始大小写
    seen: set[str] = set()
    unique: List[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique