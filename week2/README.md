# Week 2 – Action Item Extractor / 待办提取器

A small FastAPI + SQLite app that turns free-form notes into a checklist of action items. Extraction can use local heuristics or an Ollama-backed LLM. A minimal HTML page at `/` calls the HTTP API.

小型 FastAPI + SQLite 应用：把自由文本笔记转成待办清单。提取可用本地启发式规则，或走 Ollama 上的 LLM。根路径 `/` 有一页简易 HTML，调用同一套 HTTP API。

## Setup and run / 安装与运行

Work from the **repository root** (the directory that contains `pyproject.toml` and `week2/`).

请在**仓库根目录**操作（含 `pyproject.toml` 与 `week2/` 的那一层）。

1. Create and activate the course Conda env (Python 3.12), then install dependencies with Poetry. Full steps are in the repo root `README.md`. Short version:

   创建并激活课程用 Conda 环境（Python 3.12），再用 Poetry 安装依赖。完整步骤见仓库根目录 `README.md`。简写：

  ```bash
   conda activate cs146s
   poetry install --no-interaction
  ```
2. Start the API (creates SQLite tables on startup):

   启动 API（启动时会创建 SQLite 表）：

  ```bash
   poetry run uvicorn week2.app.main:app --reload
  ```
3. Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Interactive OpenAPI docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

   打开上述首页。交互式 OpenAPI 文档见 `/docs`。

**LLM extract** (`Extract LLM` on the page, or `POST /action-items/extract-llm`) needs [Ollama](https://ollama.com) running and the model named in settings (default `llama3.1:8b`, override with `OLLAMA_MODEL`). Heuristic **Extract** does not need Ollama.

**LLM 提取**（页面上的 `Extract LLM`，或 `POST /action-items/extract-llm`）需要本机 [Ollama](https://ollama.com) 在跑，且配置里的模型可用（默认 `llama3.1:8b`，可用 `OLLAMA_MODEL` 覆盖）。启发式 **Extract** 不需要 Ollama。

Optional environment variables (also loaded from a `.env` in the process working directory if you create one):

可选环境变量（若在进程工作目录放了 `.env`，也会被加载）：

| Variable / 变量   | Role / 作用          | Default / 默认            |
| ----------------- | -------------------- | ------------------------- |
| `WEEK2_DATA_DIR`  | Directory for SQLite / SQLite 所在目录 | `week2/data`              |
| `WEEK2_DB_PATH`   | Database file / 数据库文件 | `{WEEK2_DATA_DIR}/app.db` |
| `OLLAMA_MODEL`    | Chat model / 对话模型 | `llama3.1:8b`             |
| `WEEK2_APP_TITLE` | FastAPI title / FastAPI 标题 | `Action Item Extractor`   |

## API

Empty `text` / `content` (or missing field) on extract/create-note returns **422** with `{"detail": "text is required"}` or `"content is required"`. Missing notes or action items return **404**. LLM failures return **503** with `{"detail": "extraction failed"}`.

提取或创建笔记时，`text` / `content` 为空或缺字段会返回 **422**，body 为 `{"detail": "text is required"}` 或 `"content is required"`。笔记或待办不存在返回 **404**。LLM 失败返回 **503**，`{"detail": "extraction failed"}`。

### Notes / 笔记

| Method | Path               | Purpose / 作用 |
| ------ | ------------------ | -------------- |
| `POST` | `/notes`           | Create a note. Body: `{ "content": "..." }`. / 创建笔记。 |
| `GET`  | `/notes`           | List all notes (`id`, `content`, `created_at`), newest first. / 列出全部笔记，最新在前。 |
| `GET`  | `/notes/{note_id}` | Fetch one note. / 按 id 取一条笔记。 |

### Action items / 待办

Extract bodies: `{ "text": "...", "save_note": false }`. If `save_note` is true, the source text is stored as a note first. Responses include `note_id` (or `null`) and `items` (`id`, `text`).

提取请求体如上。`save_note` 为 true 时会先把原文存成笔记。响应含 `note_id`（未保存则为 `null`）以及 `items`（`id`、`text`）。

| Method | Path                        | Purpose / 作用 |
| ------ | --------------------------- | -------------- |
| `POST` | `/action-items/extract`     | Heuristic extraction (`extract_action_items`). / 启发式提取。 |
| `POST` | `/action-items/extract-llm` | LLM extraction via Ollama (`extract_action_items_llm`). / 经 Ollama 的 LLM 提取。 |
| `GET`  | `/action-items`             | List action items. Optional query `note_id`. / 列出待办；可选按 `note_id` 过滤。 |
| `POST` | `/action-items/{id}/done`   | Mark done. Body: `{ "done": true }`. / 标记完成。 |

The HTML UI: **Extract** → heuristic endpoint; **Extract LLM** → LLM endpoint; **List Notes** → `GET /notes`. Checking an item calls mark-done.

页面按钮：**Extract** 走启发式接口；**Extract LLM** 走 LLM 接口；**List Notes** 请求 `GET /notes`。勾选一条待办会调用标记完成。

## Tests / 测试

Do **not** need the uvicorn server. From the repository root, with `cs146s` activated:

**不需要**先开 uvicorn。在仓库根目录、已 `conda activate cs146s` 的前提下：

```bash
# API tests (isolated temp SQLite; LLM is mocked)
# API 测试（临时 SQLite；LLM 被 mock）
python -m pytest week2/tests/test_api.py -v

# All week2 tests (LLM file is skipped unless the env var below is set)
# 全部 week2 测试（未设下方环境变量时会跳过 LLM 文件）
python -m pytest week2/tests -v
```

`week2/tests/test_extract.py` calls Ollama for real. Enable it only if the daemon and model are available:

`week2/tests/test_extract.py` 会真实调用 Ollama。仅在守护进程和模型都可用时再打开：

```bash
# PowerShell
$env:RUN_LLM_TESTS = "1"
python -m pytest week2/tests/test_extract.py -v
```

API tests set `WEEK2_DATA_DIR` to a temp directory so they do not write `week2/data/app.db`.

API 测试会把 `WEEK2_DATA_DIR` 指到临时目录，不会写入 `week2/data/app.db`。
