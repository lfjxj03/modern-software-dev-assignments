# Week 3 – Open-Meteo MCP server (STDIO or Streamable HTTP)

Local Model Context Protocol server that wraps the public [Open-Meteo](https://open-meteo.com) **geocoding** and **forecast** REST APIs. No API key. Default transport is **stdio** (Cursor, Claude Desktop, MCP Inspector). The same tools can also be served over **Streamable HTTP** (no auth in this version).

本地 MCP 服务器：封装 Open-Meteo 地理编码与预报接口，无需 API key。默认 STDIO；可用 `--transport http` 开 Streamable HTTP（无鉴权）。

This is **not** a copy of the official MCP weather quickstart (that sample uses a different upstream). Here the server geocodes a place name, then calls Open-Meteo forecast.

## Prerequisites / 前置

Work from the **repository root** (the directory that contains `pyproject.toml`). Python 3.12 via the course Conda env.

在**仓库根目录**操作。

```bash
conda activate cs146s
poetry install --no-interaction
```

This repo’s [`poetry.toml`](../poetry.toml) sets `virtualenvs.create = false`, so Poetry installs into the **active** `cs146s` env. Always activate `cs146s` before `poetry add` / `poetry run`.

No environment variables are required. Do not set Open-Meteo’s commercial `apikey`.

## Upstream endpoints / 上游接口

| Purpose | Method | URL |
| ------- | ------ | --- |
| Place name → lat/lon | `GET` | `https://geocoding-api.open-meteo.com/v1/search` |
| Current weather / daily forecast | `GET` | `https://api.open-meteo.com/v1/forecast` |

Free non-commercial limits (Open-Meteo terms): about **10,000 calls/day**, **5,000/hour**, **600/minute**. The client retries **HTTP 429** using `Retry-After` or exponential backoff (capped at 8s).

## Run locally / 本机运行

### STDIO (default)

STDIO servers read JSON-RPC from stdin. Starting the module in a terminal looks idle; that is waiting for a client, not a hang.

单独在终端运行入口会像卡住，这是在等 stdin。Cursor 配置不要加 `--transport http`。

```bash
poetry run python -m week3.server.main
# same as --transport stdio
```

Logs go to **stderr** only on stdio (never `print` to stdout).

MCP Inspector (stdio):

```bash
npx @modelcontextprotocol/inspector poetry run python -m week3.server.main
```

If port 6274 is in use, stop the old Inspector or set another `CLIENT_PORT`. In the UI: Connect (STDIO) → Tools → list/call `get_current_weather` and `get_weather_forecast`.

### Streamable HTTP

Same `mcp` app (tools / resources / prompts). Only CLI flags and `mcp.run(...)` kwargs change. Default `http://127.0.0.1:8000/mcp`. No API-key auth.

同一套 tool / resource / prompt；差别只在命令行参数和传给 `mcp.run()` 的 `transport` / `host` / `port`。本机默认如下；**未做鉴权**。

```bash
poetry run python -m week3.server.main --transport http --host 127.0.0.1 --port 8000
```

Optional env: `MCP_TRANSPORT=http`, `MCP_HTTP_HOST`, `MCP_HTTP_PORT`.

Inspector: start the HTTP server in one terminal, then point Inspector at Streamable HTTP / URL `http://127.0.0.1:8000/mcp` (UI labels vary by Inspector version).

Do not bind `--host 0.0.0.0` on an untrusted network without adding auth later.

One live HTTP check **without** MCP (JSON on stdout):

```bash
poetry run python -m week3.server.client
```

## Configure Cursor / 在 Cursor 中接入

Project file: [`.cursor/mcp.json`](../.cursor/mcp.json). Keep any other servers (e.g. `filesystem`). Example `open-meteo` block:

**Windows (this machine):** Cursor often cannot see `poetry` on `PATH`, so point at the `cs146s` interpreter:

```json
{
  "mcpServers": {
    "open-meteo": {
      "command": "C:\\Users\\think\\.conda\\envs\\cs146s\\python.exe",
      "args": ["-m", "week3.server.main"],
      "cwd": "d:\\workcode\\cs146s\\modern-software-dev-assignments"
    }
  }
}
```

Replace `command` and `cwd` with **your** `cs146s` `python.exe` and this repo’s root.

If `poetry` is on `PATH` (typical in a Conda-activated terminal, or macOS/Linux):

```json
{
  "mcpServers": {
    "open-meteo": {
      "command": "poetry",
      "args": ["run", "python", "-m", "week3.server.main"],
      "cwd": "<absolute path to repo root>"
    }
  }
}
```

Reload MCP (or restart Cursor). Start a **new** chat, then ask:

- “What is the current weather in Beijing?” / 「北京现在天气怎么样？」
- “3-day forecast for Tokyo” / 「东京未来 3 天预报」
- A nonsense place name — you should see a string starting with `Error:`, not a disconnected server.

## Configure Claude Desktop / Claude Desktop 配置

Edit `claude_desktop_config.json` (Claude → Settings → Developer). Same shape as Cursor: `command` + `args` + **`cwd` = repo root**.

macOS example:

```json
{
  "mcpServers": {
    "open-meteo": {
      "command": "poetry",
      "args": ["run", "python", "-m", "week3.server.main"],
      "cwd": "/path/to/modern-software-dev-assignments"
    }
  }
}
```

Restart Claude Desktop after saving.

## Tool reference / 工具参考

### `ping`

No parameters. Returns `pong`. Does not call Open-Meteo.

### `get_current_weather`

| Parameter | Type | Required | Notes |
| --------- | ---- | -------- | ----- |
| `location` | string | yes | Place name, e.g. `Beijing` |
| `timezone` | string | no | IANA tz; default is geocoded timezone or `auto` |

Example input: `{ "location": "Beijing" }`

Example output (JSON string): `location` label, lat/lon, `observed_at`, `conditions`, `temperature_c`, humidity, wind.

Failures return `Error: ...` (process stays up): empty `location`, no geocode hit, timeout, HTTP 4xx/5xx, rate limit after retries.

### `get_weather_forecast`

| Parameter | Type | Required | Notes |
| --------- | ---- | -------- | ----- |
| `location` | string | yes | Place name |
| `days` | int | no | 1–7, default 3 |
| `timezone` | string | no | IANA tz |

Example input: `{ "location": "Tokyo", "days": 3 }`

Example output: location plus `forecast[]` (`date`, max/min °C, precipitation mm, conditions).

`days` outside 1–7 → `Error: days must be between 1 and 7`.

## Resource and prompt

- Resource `weather://open-meteo/docs` — short description of wrapped URLs and error behavior (no network).
- Prompt `compare_two_cities(city_a, city_b)` — instructs the model to call `get_current_weather` twice and compare.

## Tests / 测试

Mocked `httpx` (no live Open-Meteo). From the repository root:

```bash
python -m pytest week3/tests -v
```

## Layout

```
week3/
  server/main.py     # MCP entry (stdio default; --transport http)
  server/client.py   # Open-Meteo HTTP client
  tests/test_client.py
  README.md
```
