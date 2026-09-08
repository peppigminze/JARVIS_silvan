"""
FetchUrlTool tests. The happy path mocks httpx.AsyncClient rather than
hitting a real server, for two reasons: no test should depend on real
internet access, and - more importantly - the tool's own SSRF guard
would correctly *refuse* a request to a local test server (127.0.0.1),
so there's no way to exercise a real successful fetch without either
disabling the guard (defeats the point) or faking the HTTP layer.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
import pytest

from app.tools.web_tools import MAX_TEXT_CHARS, FetchUrlTool


class FakeResponse:
    def __init__(self, body: bytes, content_type: str = "text/html", url: str = "https://example.com/", status_code: int = 200):
        self._body = body
        self.headers = {"content-type": content_type}
        self.url = httpx.URL(url)
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)  # type: ignore[arg-type]

    async def aiter_bytes(self):
        yield self._body


class FakeAsyncClient:
    def __init__(self, *args, response: FakeResponse | None = None, **kwargs):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @asynccontextmanager
    async def stream(self, method, url):
        yield self._response


def _patch_client(monkeypatch, response: FakeResponse):
    def factory(*args, **kwargs):
        return FakeAsyncClient(*args, response=response, **kwargs)

    monkeypatch.setattr("app.tools.web_tools.httpx.AsyncClient", factory)


async def test_fetch_url_extracts_readable_text(monkeypatch):
    html = b"<html><head><title>Test Page</title></head><body><script>ignored()</script><p>Hello world.</p></body></html>"
    _patch_client(monkeypatch, FakeResponse(html))

    result = await FetchUrlTool().execute(url="https://example.com/article")

    assert result.success is True
    assert result.data["title"] == "Test Page"
    assert "Hello world." in result.data["content"]
    assert "ignored()" not in result.data["content"]
    assert result.data["truncated"] is False


async def test_fetch_url_truncates_long_content(monkeypatch):
    html = ("<html><body><p>" + "x " * (MAX_TEXT_CHARS) + "</p></body></html>").encode()
    _patch_client(monkeypatch, FakeResponse(html))

    result = await FetchUrlTool().execute(url="https://example.com/long")

    assert result.success is True
    assert result.data["truncated"] is True
    assert len(result.data["content"]) == MAX_TEXT_CHARS


async def test_fetch_url_rejects_non_html_content_type(monkeypatch):
    _patch_client(monkeypatch, FakeResponse(b"binary", content_type="application/pdf"))

    result = await FetchUrlTool().execute(url="https://example.com/file.pdf")

    assert result.success is False
    assert "content type" in result.error


async def test_fetch_url_blocks_private_ip_before_any_request(monkeypatch):
    called = False

    def factory(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("Should never construct a client for a blocked URL")

    monkeypatch.setattr("app.tools.web_tools.httpx.AsyncClient", factory)

    result = await FetchUrlTool().execute(url="http://127.0.0.1/admin")

    assert result.success is False
    assert "Refused" in result.error
    assert called is False


async def test_fetch_url_rejects_localhost_hostname(monkeypatch):
    result = await FetchUrlTool().execute(url="http://localhost:8000/api/status")
    assert result.success is False
    assert "Refused" in result.error
