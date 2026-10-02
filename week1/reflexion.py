import os
import re
from typing import Callable, List, Tuple
from dotenv import load_dotenv
from ollama import chat

load_dotenv()

NUM_RUNS_TIMES = 1

SYSTEM_PROMPT = """
You are a coding assistant. Output ONLY a single fenced Python code block that defines
the function is_valid_password(password: str) -> bool. No prose or comments.
Keep the implementation minimal.
"""

# TODO: Fill this in!
YOUR_REFLEXION_PROMPT = """
You are a programming assistant. Continuously refine the code according to the code generated 
last time and the test results provided by the user as feedback.
Your job:
    1. Read every failure entry—do not stop after fixing the first one.
    2. For each failure, use the input, expected vs actual result, and "Failing checks" to identify what the code is missing or doing wrong.
    3. Revise the code so that all listed failures would be resolved in one updated implementation.
    4. Keep any logic that is already correct; only add or adjust what the failures indicate.
Before outputting, mentally verify your revision against each failure in the list.
Return only the revised code in a single Markdown fenced Python code block. No explanations or comments.
"""


# Ground-truth test suite used to evaluate generated code
# 密码应当包含：大小写字母，数字，特殊字符
SPECIALS = set("!@#$%^&*()-_")
TEST_CASES: List[Tuple[str, bool]] = [
    ("Password1!", True),       # valid
    ("password1!", False),      # missing uppercase
    ("Password!", False),       # missing digit
    ("Password1", False),       # missing special
    ("Pass", False),            # length < 8
]


def extract_code_block(text: str) -> str:
    m = re.findall(r"```python\n([\s\S]*?)```", text, flags=re.IGNORECASE)
    if m:
        return m[-1].strip()
    m = re.findall(r"```\n([\s\S]*?)```", text)
    if m:
        return m[-1].strip()
    return text.strip()

# 从字符串中生成函数，主要通过exec执行函数定义代码，从而产生可调用的函数对象。
def load_function_from_code(code_str: str) -> Callable[[str], bool]:
    namespace: dict = {}  # 用于存储代码中定义的函数对象
    # 动态执行字符串形式的 Python 代码，并将执行结果存储在指定的命名空间中。code_str中应当定义函数is_valid_password。
    # noqa:no quality assurance，不进行代码质量检查。静态检查工具知道这里有「执行动态代码」的风险；
    exec(code_str, namespace)  # noqa: S102 (executing controlled code from model for exercise)
    func = namespace.get("is_valid_password")  # 从命名空间中获取函数对象
    if not callable(func):
        raise ValueError("No callable is_valid_password found in generated code")
    return func


def evaluate_function(func: Callable[[str], bool]) -> Tuple[bool, List[str]]:
    # 评估模型返回代码执行结果是否正确，错误的话给出错误信息
    failures: List[str] = []
    for pw, expected in TEST_CASES:
        try:
            result = bool(func(pw))
        except Exception as exc:
            failures.append(f"Input: {pw} → raised exception: {exc}")
            continue

        if result != expected:
            # Compute diagnostic based on ground-truth rules
            # 根据密码长度、大小写字母、数字、特殊字符、空格等规则，生成失败原因
            # 可能同时违反多个规则，因此reasons列表中可能包含多个原因
            reasons = []
            if len(pw) < 8:
                reasons.append("length < 8")
            if not any(c.islower() for c in pw):
                reasons.append("missing lowercase")
            if not any(c.isupper() for c in pw):
                reasons.append("missing uppercase")
            if not any(c.isdigit() for c in pw):
                reasons.append("missing digit")
            if not any(c in SPECIALS for c in pw):
                reasons.append("missing special")
            if any(c.isspace() for c in pw):
                reasons.append("has whitespace")

            failures.append(
                f"Input: {pw} → expected {expected}, got {result}. Failing checks: {', '.join(reasons) or 'unknown'}"
            )

    return (len(failures) == 0, failures)  # 返回的第一个字段为是否通过测试，第二个字段为失败原因列表


def generate_initial_function(system_prompt: str) -> str:
    response = chat(
        model="llama3.1:8b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Provide the implementation now."},
        ],
        options={"temperature": 0.2},  # 模型输出随机性较低
    )
    return extract_code_block(response.message.content)


def your_build_reflexion_context(prev_code: str, failures: List[str]) -> str:
    """TODO: Build the user message for the reflexion step using prev_code and failures.

    Return a string that will be sent as the user content alongside the reflexion system prompt.
    """
    reflex_context = f"""
    Code：{prev_code}
    Failures: {failures}
    """
    return reflex_context


def apply_reflexion(
    reflexion_prompt: str,
    build_context: Callable[[str, List[str]], str],
    prev_code: str,
    failures: List[str],
) -> str:
    reflection_context = build_context(prev_code, failures)
    print(f"REFLECTION CONTEXT: {reflection_context}, {reflexion_prompt}")
    response = chat(
        model="llama3.1:8b",
        messages=[
            {"role": "system", "content": reflexion_prompt},
            {"role": "user", "content": reflection_context},
        ],
        options={"temperature": 0.2},
    )
    return extract_code_block(response.message.content)


def run_reflexion_flow(
    system_prompt: str,
    reflexion_prompt: str,
    build_context: Callable[[str, List[str]], str],
) -> bool:
    # 1) Generate initial function
    initial_code = generate_initial_function(system_prompt)
    print("Initial code:\n" + initial_code)
    func = load_function_from_code(initial_code)  # 从文本中生成函数对象
    passed, failures = evaluate_function(func)  # 如果passed == True，则failures应当为空
    if passed:
        print("SUCCESS (initial implementation passed all tests)")
        return True
    else:
        print(f"FAILURE (initial implementation failed some tests): {failures}")

    # 2) Single reflexion iteration
    improved_code = apply_reflexion(reflexion_prompt, build_context, initial_code, failures)
    print("\nImproved code:\n" + improved_code)
    improved_func = load_function_from_code(improved_code)
    passed2, failures2 = evaluate_function(improved_func)
    if passed2:
        print("SUCCESS")
        return True

    print("Tests still failing after reflexion:")
    for f in failures2:
        print("- " + f)
    return False


if __name__ == "__main__":
    run_reflexion_flow(SYSTEM_PROMPT, YOUR_REFLEXION_PROMPT, your_build_reflexion_context)
