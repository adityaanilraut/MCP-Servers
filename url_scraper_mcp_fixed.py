#!/usr/bin/env python3
"""
URL Scraper MCP Server (fixed)
- Uses FastMCP from the official MCP Python SDK (mcp.server.fastmcp)
- Avoids low-level get_capabilities() API changes
- Exposes one tool: scrape_url(url, max_chars=5000, max_links=100)

Run options:
1) Directly as a script (stdio transport):
   python3 url-scraper-mcp-fixed.py

2) With the MCP CLI (recommended during development):
   uv run mcp dev url-scraper-mcp-fixed.py

Dependencies (add to your project):
    pip install "mcp[cli]" httpx beautifulsoup4
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

import anyio
import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

# Create the FastMCP server instance
mcp = FastMCP("URL Scraper")


def _clean_text(text: str) -> str:
    # Collapse whitespace and trim
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


@mcp.tool()
async def scrape_url(
    url: str,
    max_chars: int = 5000,
    max_links: int = 100,
    timeout_s: float = 20.0,
    user_agent: str = "url-scraper-mcp/0.1 (+https://example.local)",
) -> Dict[str, Any]:
    """
    Fetch a URL and return structured page data.

    Args:
        url: The URL to fetch (http/https only).
        max_chars: Max characters of page text to return.
        max_links: Max number of links to return.
        timeout_s: Request timeout in seconds.
        user_agent: Custom User-Agent string.

    Returns:
        dict with:
            - url: input URL
            - final_url: URL after redirects
            - status_code: HTTP status
            - title: <title> text (if any)
            - content: extracted visible text (up to max_chars)
            - links: list of {url, text} (up to max_links)
    """
    if not isinstance(url, str) or not url:
        raise ValueError("url must be a non-empty string")

    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("Only http(s) URLs are supported")

    headers = {"User-Agent": user_agent}
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=timeout_s) as client:
            resp = await client.get(url)
    except httpx.RequestError as e:
        # Return a structured error object instead of raising, so hosts can display it
        return {
            "url": url,
            "final_url": None,
            "status_code": None,
            "title": None,
            "content": "",
            "links": [],
            "error": f"request_error: {e.__class__.__name__}: {str(e)}",
        }

    content_type = resp.headers.get("content-type", "")
    is_html = "html" in content_type.lower()

    result: Dict[str, Any] = {
        "url": url,
        "final_url": str(resp.url),
        "status_code": resp.status_code,
        "title": None,
        "content": "",
        "links": [],
    }

    if is_html and resp.text:
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script/style elements
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # Title
        title = soup.title.string if soup.title and soup.title.string else ""
        result["title"] = _clean_text(title)

        # Visible text
        text_content = _clean_text(soup.get_text(" "))
        result["content"] = text_content[: max(0, int(max_chars))]

        # Links
        links: List[Dict[str, str]] = []
        for a in soup.find_all("a", href=True):
            text = _clean_text(a.get_text())
            href = a.get("href") or ""
            if href:
                links.append({"url": str(httpx.URL(result["final_url"]).join(href)), "text": text})
            if len(links) >= max(0, int(max_links)):
                break
        result["links"] = links
    else:
        # Non-HTML: just return headers and a small snippet of bytes (if present)
        snippet = None
        try:
            if resp.content:
                snippet = resp.content[:512].decode("utf-8", errors="replace")
        except Exception:
            snippet = None
        result["title"] = None
        result["content"] = snippet or ""

    return result


async def _run_server() -> None:
    """
    Run the FastMCP server using stdio transport.
    FastMCP provides multiple run methods across versions; this wrapper
    supports both `.run()` and `.run_stdio()`.
    """
    runner = getattr(mcp, "run", None) or getattr(mcp, "run_stdio", None)
    if runner is None:
        raise RuntimeError("FastMCP run method not found. Please update the MCP SDK.")
    # If the runner is an async function, await it; otherwise call it directly.
    if callable(runner):
        maybe_coro = runner()
        if hasattr(maybe_coro, "__await__"):
            await maybe_coro  # async runner
        else:
            # Some FastMCP versions expose sync run()
            maybe_coro  # type: ignore[func-returns-value]
    else:
        raise RuntimeError("Invalid FastMCP run method")


if __name__ == "__main__":
    anyio.run(_run_server)
