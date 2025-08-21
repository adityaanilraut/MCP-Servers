# py_runner_server.py
# Minimal MCP server that safely runs short Python snippets in a subprocess.
# Requires: pip install "mcp[cli]"

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    raise ImportError("The 'mcp' package is not installed or the import path is incorrect. Please install it with 'pip install \"mcp[cli]\"' or check the correct import path.")
import asyncio, subprocess, sys, tempfile, textwrap, os

mcp = FastMCP(name="py-runner")

@mcp.tool()
async def run_python(
    code: str,
    input_text: str | None = None,
    timeout_secs: int = 5,
) -> dict:
    """
    Run a short Python snippet in an isolated subprocess.

    Args:
        code: Python source code to execute.
        input_text: Optional stdin to pass to the process.
        timeout_secs: Kill the process after this many seconds.

    Returns: {stdout, stderr, exit_code, duration_ms}
    """
    # Basic guardrails: dedent, temp directory, subprocess with timeout
    code = textwrap.dedent(code)

    loop = asyncio.get_event_loop()
    t0 = loop.time()

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "main.py")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)

        proc = await asyncio.create_subprocess_exec(
            sys.executable, src,
            stdin=asyncio.subprocess.PIPE if input_text else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tmp,
        )

        try:
            out, err = await asyncio.wait_for(
                proc.communicate(input_text.encode() if input_text else None),
                timeout=timeout_secs,
            )
        except asyncio.TimeoutError:
            proc.kill()
            return {"error": f"Timeout after {timeout_secs}s"}

    return {
        "stdout": out.decode(),
        "stderr": err.decode(),
        "exit_code": proc.returncode,
        "duration_ms": int((loop.time() - t0) * 1000),
    }

if __name__ == "__main__":
    # Uses stdio transport by default, which LM Studio expects for local commands
    mcp.run()
