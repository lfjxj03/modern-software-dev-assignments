# Week 3 学习步骤（按知识点拆分）

对照 `[assignment.md](./assignment.md)`。每一步只解决一个核心概念。做题时按序号推进；第 12 步为 extra credit，可跳过。

已选定上游：**Open-Meteo**（详见第 2 步）。传输默认本地 STDIO（Cursor）。**不要**提交 [MCP Server Quickstart](https://modelcontextprotocol.io/quickstart/server) 的原样示例。

---

## 第 1 步：搞清 MCP 是什么（相对普通 HTTP API）

**核心问题：** 模型为什么不直接 `fetch` 天气接口，而要经过 MCP？

弄清三件套：

- **tools**：可调用的动作
- **resources**：可读上下文
- **prompts**：可复用的提示模板

对照本仓库已在用的 filesystem MCP：列目录 / 读文件都是客户端通过协议调 server 上的能力。作业硬性要求至少 2 个 tool；resource / prompt 属于 learning goals，可放到第 9 步。

---

## 第 2 步：选定真实外部 API，并写清要用的端点

**核心问题：** MCP 只是“插座”，业务能力来自上游 HTTP。

**选定：** [Open-Meteo](https://open-meteo.com) 公开 REST（地理编码 + 预报）。课程作业属教育用途，走免费非商用条款即可。文档： [Forecast](https://open-meteo.com/en/docs)、 [Geocoding](https://open-meteo.com/en/docs/geocoding-api)、 [Terms](https://open-meteo.com/en/terms)。

### 是否需要 API key

**不需要。** 非商用免费接口公开可调。文档里的 `apikey` 仅给商用客户（主机名前缀 `customer-`）；本作业不要配这个。

### Base URL 与至少两个 path

城市名不能直接查天气，预报接口要 **WGS84 经纬度**。因此 MCP 的两个 tool 会先 geocode，再 forecast。


| 用途          | Method | URL                                              |
| ----------- | ------ | ------------------------------------------------ |
| 地名 → 坐标     | `GET`  | `https://geocoding-api.open-meteo.com/v1/search` |
| 当前天气 / 逐日预报 | `GET`  | `https://api.open-meteo.com/v1/forecast`         |


**Geocoding 查询参数（作业会用到的）：**

- `name`（必填）：地名或邮编，如 `Beijing`、`Tokyo`
- `count`：返回条数，默认 10，作业里可取 `1`
- `language`：默认 `en`
- 单字符 / 空 `name`：文档写明无结果
- 成功 JSON：`results[]`，常用字段 `name`、`latitude`、`longitude`、`timezone`、`country`、`admin1`
- 找不到：`results` 缺失或空数组（不是一定 HTTP 错误）
- 参数非法：HTTP **400**，body 形如 `{"error": true, "reason": "..."}`

**Forecast 查询参数（作业会用到的）：**

- `latitude`、`longitude`（必填）
- `timezone`：IANA 名，或 `auto`
- 当前天气：`current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m`
- 逐日预报：`daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum`，以及 `forecast_days`（文档默认 7，最长 16；MCP 侧可把天数限制在 1–7，便于参数校验）
- 成功时 `current` / `daily` 对象里带对应数组；`weather_code` 为 [WMO 天气代码](https://open-meteo.com/en/docs)

示例（只说明，本步不发请求）：

```text
GET https://geocoding-api.open-meteo.com/v1/search?name=Beijing&count=1
GET https://api.open-meteo.com/v1/forecast?latitude=39.91&longitude=116.40&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto
GET https://api.open-meteo.com/v1/forecast?latitude=35.69&longitude=139.69&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum&forecast_days=3&timezone=auto
```



### 限流（免费非商用）

据 Open-Meteo Terms of Use（Free / Open-Access）：

- 每天少于 **10,000** 次调用
- 每小时少于 **5,000**
- 每分钟少于 **600**
- 滥用可能被封 IP / 应用

课程里两个 tool、人工点几下远低于上限。实现时仍应识别 **HTTP 429**（及 `Retry-After`），做有限退避或把限流信息返回给模型（对应作业 Resilience / 第 8 步）。

### 和官方 MCP weather 示例的区别

Quickstart 常见的是美国 NWS 等另一套接口。这里用 Open-Meteo 的 geocoding + forecast，满足“真实外部 API、至少两个端点”，且不是那份示例的副本。

第 11 步写 README 时，可把本节表格和限流数字直接搬过去。

---



## 第 3 步：选定传输方式——先做本地 STDIO

**核心问题：** STDIO 下 **stdout 被协议占用**，`print` 会把 JSON-RPC 弄坏；日志必须走 **stderr**。

**选定：** 作业主体用 **本地 STDIO**，在本机由 Cursor（或 Claude Desktop / MCP Inspector）拉起 Python 进程。不在此刻做远程 HTTP 部署；那是第 12 步 extra credit。

### 作业里的两种模式（只选一种就能交）


|        | 本地 STDIO（本步选定）                         | 远程 HTTP（第 12 步可选）             |
| ------ | -------------------------------------- | ----------------------------- |
| 进程怎么起来 | 客户端执行 `command` + `args`，父子进程          | 自己监听端口，或部署到公网                 |
| 报文走哪   | **stdin / stdout** 上的 JSON-RPC         | HTTP（如 Streamable HTTP）       |
| 配客户端   | `.cursor/mcp.json` 或 Claude Desktop 配置 | URL + 可选鉴权                    |
| 评分     | 满足 requirement 5 的 Local 项             | extra credit +5（再加 Auth 另 +5） |


STDIO 足够：server 可在本机运行，且能被 Cursor 发现。这与你已经在用的 filesystem MCP 是同一类接入方式。

### 必须记住的日志规则

客户端把 server 的 **stdout 当成协议流** 解析。因此：

- **禁止** `print(...)`（默认打到 stdout），也禁止把库的进度条、调试 JSON 打到 stdout
- 用 `logging`，并把 handler 绑到 `sys.stderr`
- 调试时在终端里直接跑 `python -m week3.server.main` 会像“卡住”——那是在等 stdin 上的 MCP 消息，属正常，不是死机

第 4 步搭空服务器时就要遵守这条，不要等接到 Open-Meteo 再改。

### 客户端稍后会怎么配（本步只定原则，不改文件）

原则是：`command` 启动解释器 / Poetry，`args` 指向入口模块，`cwd` **必须是含** `pyproject.toml` **的仓库根**（Windows 尤其容易配错）。真正改 `[.cursor/mcp.json](../.cursor/mcp.json)` 放到第 10 步，避免还没 server 就配上一个起不来的进程。

### 本步明确不做

- 不写 `week3/server/`
- 不改 `mcp.json`
- 不申请公网 URL、不做 MCP Authorization

---

---



## 第 4 步：搭最小可运行的 MCP 空服务器

**核心问题：** Python MCP SDK（`MCPServer`）怎么启动、`mcp.run(transport="stdio")` 在干什么。

**选定 SDK：** 官方 PyPI 包 `mcp`（当前装的是 2.x）。`FastMCP` 已改名为 `MCPServer`：

```python
from mcp.server.mcpserver import MCPServer
mcp = MCPServer("open-meteo")
mcp.run(transport="stdio")
```

作业链接的 Quickstart 若仍写 `mcp.server.fastmcp.FastMCP`，那是 1.x API；不要再装另一个独立包 `fastmcp`。本仓库用 `poetry add mcp` 写入主依赖。

**安装：** 在仓库根、`conda activate cs146s` 之后用 Poetry 写入项目依赖（装进 Poetry venv，不是只 `pip` 进 conda）：

```bash
poetry add mcp
```

**入口：** `[week3/server/main.py](./server/main.py)`

- `FastMCP("open-meteo")` + `mcp.run(transport="stdio")`：从 stdin 读 JSON-RPC，往 stdout 写应答
- 目前只有 tool `ping` → `"pong"`，不访问网络
- 日志：`logging` → `sys.stderr`

本机自检（会阻塞等 stdin，属正常）：

```bash
poetry run python -m week3.server.main
```

用 Inspector 看 tools 列表：

```bash
npx @modelcontextprotocol/inspector poetry run python -m week3.server.main
```

`.cursor/mcp.json` 仍留到第 10 步再改。本步不接 Open-Meteo。

---



## 第 5 步：单独写上游 HTTP 客户端（先不接 MCP）

**核心问题：** 把“调外部 API”和“MCP 协议”拆开。

**模块：** [`week3/server/client.py`](./server/client.py)

- `OpenMeteoClient.geocode` → `GET .../v1/search`
- `current_weather` / `forecast` → 先 geocode 再 `GET .../v1/forecast`
- 用 `httpx`（已升到 Poetry **主依赖**，MCP 进程不依赖 `--with dev`）
- 本步**不**改 `main.py` 的 tools；`ping` 仍然是唯一 MCP tool
- 429 退避留给第 8 步；这里已有超时、HTTP 错误、空地名 / 找不到地点

在仓库根、已 `conda activate cs146s` 时打一次真实请求（结果 JSON 打 stdout，日志打 stderr）：

```bash
poetry run python -m week3.server.client
```

应看到 `Beijing` 的经纬度和 `temperature_c` 等字段。

Mock HTTP 的单元测试（不访问真实 API）：

```bash
python -m pytest week3/tests -v
```

覆盖：当前天气 / 预报成功、空地名、找不到地点、超时、HTTP 500。429 退避的测试留到第 8 步。

---



## 第 6 步：第一个带类型参数的 tool

**核心问题：** tool 的函数签名如何变成模型能填的 schema（类型注解 / 文档字符串）。

已在 [`week3/server/main.py`](./server/main.py) 增加 **`get_current_weather(location, timezone=None)`**，内部调用 `OpenMeteoClient.current_weather`。`OpenMeteoError` 变成返回字符串 `Error: ...`，进程不退出。`ping` 仍保留。

Inspector：Connect 后 List Tools 应看到 `ping` 和 `get_current_weather`；`location=Beijing` 应返回 JSON。

---

---



## 第 7 步：第二个 tool（作业硬性要求）

**核心问题：** 两个 tool 应覆盖不同能力，而不是换个名字的同一请求。

已在 [`week3/server/main.py`](./server/main.py) 增加 **`get_weather_forecast(location, days=3, timezone=None)`**，调用 `OpenMeteoClient.forecast`（`daily=`，与当前天气的 `current=` 不同）。`days` 超出 1–7 返回 `Error: days must be between 1 and 7`。`ping` 仍保留。Inspector 需 Reconnect 后才能看到新 tool。

---



## 第 8 步：可靠性——超时、HTTP 失败、空结果、限流

**核心问题：** 上游挂了时 **server 进程不能崩**，要给模型可读错误。

已在 [`week3/server/client.py`](./server/client.py) 的 `_get` 中：对 **HTTP 429** 读取 `Retry-After`（否则指数退避上限 8s），最多 `max_retries` 次后再报 `rate limited ... 429`。其它 4xx/5xx 不重试。测试里注入 `sleep=lambda _: None`。geocode 缺坐标时改为 `OpenMeteoError`。新增 `test_rate_limit_then_success` / `test_rate_limit_exhausted`。

---



## 第 9 步（建议）：补一个 resource 和一个 prompt

**核心问题：** tool 会“做事”，resource 提供只读说明，prompt 预置“怎么用这两个 tool”。

已在 [`week3/server/main.py`](./server/main.py)：

- Resource `weather://open-meteo/docs`：上游 URL 与错误约定（不发 HTTP）
- Prompt `compare_two_cities(city_a, city_b)`：引导各调一次 `get_current_weather`

Inspector 的 Resources / Prompts 页可列出；需重启再连。

---



## 第 10 步：接到 Cursor（或 Claude Desktop）并亲手点一遍

**核心问题：** `mcp.json` 的 `command` / `args` / `cwd`（Windows 下 `cwd` 必须是含 `pyproject.toml` 的仓库根）。

已在 [`.cursor/mcp.json`](../.cursor/mcp.json) **保留 filesystem**，并增加 `open-meteo`。Cursor 从 GUI 启动时往往没有 `poetry` 的 PATH，因此 `command` 直接指向 conda `cs146s` 的 `python.exe`，`args` 为 `["-m", "week3.server.main"]`，`cwd` 为仓库根。

保存后请在 Cursor 中重载 MCP / 新开对话，问「北京现在天气」和「东京未来 3 天预报」，再试一个不存在的地名，确认出现 `Error:` 而不是断连。

---



## 第 11 步：写 `week3/README.md`（正式 deliverable）

已写 [`week3/README.md`](./README.md)：前置与运行、Cursor / Claude Desktop 配置、tool 参数与失败行为、Inspector / 对话示例、pytest。未写 `writeup.md`（作业未要求）。

---



## 第 12 步（可选 extra credit）：HTTP 传输和/或鉴权

已实现。**tools / resources / prompts 与 STDIO 完全共用**；这一步只处理两件事：

1. 命令行识别 `--transport stdio|http`（以及 HTTP 的 `--host` / `--port`）
2. 传给 `mcp.run()` 的差异：stdio 只需 `transport="stdio"`；HTTP 要 `transport="streamable-http"`（CLI 的 `http` 是简称）加上 `host`、`port`

**鉴权未做**。Cursor 仍用默认 stdio。