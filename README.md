# MCP Utility Servers

Small, focused [Model Context Protocol (MCP)](https://modelcontextprotocol.io) servers you can run locally:
- **File Manager (Python)** — safe file and directory operations
- **Python Runner (Python/FastMCP)** — execute short Python snippets in a sandboxed subprocess
- **URL Scraper (Python/FastMCP)** — fetch a web page and return structured text + links
- **Shell Exec (Node.js)** — execute shell commands with guardrails

> Transport: all servers communicate over stdio, so they can be launched directly by your MCP host/tooling.

---

## Repository layout

```
file-manager-server.py       # JSON-RPC style MCP server for file ops
py_runner_server.py          # FastMCP server exposing run_python
url_scraper_mcp_fixed.py     # FastMCP server exposing scrape_url
shell-exec-server.js         # Node.js server exposing shell tools
setup.py                     # Packaging for the URL Scraper server
```

---

## Requirements

- **Python** ≥ 3.9
- **Node.js** (for the Shell Exec server)
- **MCP Python SDK / CLI**: `pip install "mcp[cli]"`
- URL Scraper extras: `httpx`, `beautifulsoup4`, `anyio`

> The URL Scraper can be installed as a package via `setup.py` (see **Install**).

---

## Install

### Option A — Run from source (no install)
```bash
# Python deps (shared)
pip install "mcp[cli]"

# URL Scraper deps
pip install httpx beautifulsoup4 anyio
```

### Option B — Install the URL Scraper package
From the repo root:
```bash
pip install -e .
# This installs the console entrypoint: `url-scraper-mcp`
```

---

## Running the servers

### File Manager (Python)
```bash
python3 file-manager-server.py
```

### Python Runner (FastMCP)
```bash
python3 py_runner_server.py
# or, with the MCP CLI developer runner:
# uv run mcp dev py_runner_server.py     # if you use uv
# mcp dev py_runner_server.py            # if `mcp` is on PATH
```

### URL Scraper (FastMCP)
```bash
python3 url_scraper_mcp_fixed.py
# or, with the MCP CLI developer runner:
# uv run mcp dev url_scraper_mcp_fixed.py
# If installed as a package:
url-scraper-mcp
```

### Shell Exec (Node.js)
```bash
node shell-exec-server.js
```

> Configure your MCP host to launch any of these commands via stdio.

---

## Tool reference

### 1) File Manager server — `file-manager-server.py`

**Methods** (called through the generic JSON-RPC `tools/call`):
- `read_file(path, encoding="utf-8")`
- `write_file(path, content, encoding="utf-8", append=False)`
- `list_files(path=".", pattern="*", recursive=False)`
- `create_directory(path, parents=True)`
- `delete_file(path, recursive=False)`
- `move_file(source, destination)`
- `copy_file(source, destination, recursive=False)`
- `get_file_info(path)` — includes readable size, mime, and MD5 for files <100MB
- `search_files(directory=".", pattern, file_pattern="*")`

**Example JSON-RPC call** (stdio line-based, one JSON per line):
```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"read_file","arguments":{"path":"README.md"}}}
```

**Safety**
- Blocks access to sensitive roots (e.g., `/etc`, `/sys`, `/proc`, certain Windows system paths).
- Text/binary detection for reads; binary content is base64-encoded in responses.

---

### 2) Python Runner — `py_runner_server.py`

**Server name:** `py-runner` (FastMCP)

**Tool**
- `run_python(code: str, input_text: str | None = None, timeout_secs: int = 5) -> {stdout, stderr, exit_code, duration_ms}`

**Behavior & guardrails**
- Dedents code, writes it into a temp directory, and executes via a subprocess.
- Supports optional stdin (`input_text`) and enforces a timeout (default 5s). On timeout, returns `{"error": "Timeout after ...s"}`.

**Example**
```json
{"method":"tools/call","params":{"name":"run_python","arguments":{"code":"print('hi')"}}}
```

---

### 3) URL Scraper — `url_scraper_mcp_fixed.py`

**Server name:** `URL Scraper` (FastMCP)

**Tool**
- `scrape_url(url: str, max_chars: int = 5000, max_links: int = 100, timeout_s: float = 20.0, user_agent: str = "...") -> {url, final_url, status_code, title, content, links}`

**Behavior**
- Follows redirects, extracts `<title>`, visible text (trimmed to `max_chars`), and up to `max_links` absolute links.
- Returns structured error info on request failure; for non-HTML content, returns a short decoded snippet.
- Accepts only `http(s)` URLs.

**Examples**
```json
{"method":"tools/call","params":{"name":"scrape_url","arguments":{"url":"https://example.org","max_chars":2000}}}
```

**Packaging**
- Installable package (`url-scraper-mcp`) with a console entrypoint for easy launching.

---

### 4) Shell Exec — `shell-exec-server.js`

**Tools**
- `execute_command(command: string, cwd?: string, timeout?: number)`
- `list_directory(path?: string)`
- `get_system_info()`
- `set_environment(name: string, value: string)`

**Behavior & guardrails**
- Uses `exec` with a configurable timeout; blocks obviously dangerous patterns (e.g., `rm -rf /`, raw disk writes).
- `list_directory` uses `ls -la` on POSIX or `dir` on Windows automatically.
- `get_system_info` returns a JSON object with platform, cpu count, memory, node version, cwd, etc.

**Example**
```json
{"method":"tools/call","params":{"name":"execute_command","arguments":{"command":"echo hello"}}}
```

---

## Developing with the MCP CLI

If you use the MCP Python CLI, you can run the FastMCP servers in dev mode:

```bash
uv run mcp dev py_runner_server.py
uv run mcp dev url_scraper_mcp_fixed.py
```

This starts a stdio MCP server process you can connect to from compatible hosts.

---

## Security notes & defaults

- **File Manager**: path gate to avoid system directories; base64 for binary reads; MD5 computed only for files <100MB.
- **Python Runner**: runs code in a temp working dir; subprocess timeout defaults to 5s.
- **URL Scraper**: HTTP(S) only; 20s timeout by default; strips scripts/styles; normalizes text and links.
- **Shell Exec**: blocks dangerous commands; 30s default timeout; customizable environment per session.

---

## Troubleshooting

- **`ModuleNotFoundError: mcp.server.fastmcp`** — Install the SDK: `pip install "mcp[cli]"`.
- **Hangs or no output** — Ensure you’re launching via stdio and emitting exactly one JSON-RPC object per line.
- **Network failures in URL Scraper** — Verify the URL is reachable over HTTP(S) and not blocked by your environment.
- **Permissions/paths** — Some servers intentionally block system paths and destructive commands by design.

---

## License

Add your preferred license here (e.g., MIT).

