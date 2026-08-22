import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core import rate_limit
from app.core.rate_limit import SlidingWindow, client_ip, llm_rate_limit


@pytest.fixture(autouse=True)
def _clear_counters():
    rate_limit.reset()
    yield
    rate_limit.reset()


def test_window_allows_up_to_limit_then_reports_retry_after():
    win = SlidingWindow(limit=2, window_s=60)
    for _ in range(2):
        assert win.retry_after("ip", now=100.0) is None
        win.record("ip", now=100.0)

    retry = win.retry_after("ip", now=100.0)
    assert retry is not None and retry > 0


def test_window_frees_up_once_hits_age_out():
    win = SlidingWindow(limit=1, window_s=60)
    win.record("ip", now=100.0)
    assert win.retry_after("ip", now=130.0) is not None
    assert win.retry_after("ip", now=161.0) is None


def test_checking_does_not_consume_a_slot():
    """`retry_after` must be side-effect free so a request rejected by one limit
    doesn't silently burn quota in another."""
    win = SlidingWindow(limit=1, window_s=60)
    for _ in range(5):
        assert win.retry_after("ip", now=100.0) is None
    win.record("ip", now=100.0)
    assert win.retry_after("ip", now=100.0) is not None


def test_windows_are_tracked_per_key():
    win = SlidingWindow(limit=1, window_s=60)
    win.record("a", now=100.0)
    assert win.retry_after("a", now=100.0) is not None
    assert win.retry_after("b", now=100.0) is None


def test_forwarded_header_wins_over_proxy_address():
    """Render terminates TLS at a proxy, so request.client is the proxy."""
    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.9, 70.41.3.18")],
        "client": ("10.0.0.1", 5000),
    }
    assert client_ip(Request(scope)) == "203.0.113.9"


def test_falls_back_to_peer_address_without_the_header():
    scope = {"type": "http", "headers": [], "client": ("10.0.0.1", 5000)}
    assert client_ip(Request(scope)) == "10.0.0.1"


def _client_with_limit() -> TestClient:
    app = FastAPI()

    @app.post("/paid")
    async def paid(request: Request):
        await llm_rate_limit(request)
        return {"ok": True}

    return TestClient(app)


def test_per_ip_limit_returns_429_with_retry_after(monkeypatch):
    monkeypatch.setattr(rate_limit._per_ip, "limit", 2)
    client = _client_with_limit()
    headers = {"x-forwarded-for": "198.51.100.7"}

    for _ in range(2):
        assert client.post("/paid", headers=headers).status_code == 200

    blocked = client.post("/paid", headers=headers)
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_a_throttled_visitor_does_not_block_everyone_else(monkeypatch):
    monkeypatch.setattr(rate_limit._per_ip, "limit", 1)
    client = _client_with_limit()

    assert client.post("/paid", headers={"x-forwarded-for": "198.51.100.7"}).status_code == 200
    assert client.post("/paid", headers={"x-forwarded-for": "198.51.100.7"}).status_code == 429
    assert client.post("/paid", headers={"x-forwarded-for": "203.0.113.4"}).status_code == 200


def test_global_ceiling_applies_across_different_ips(monkeypatch):
    """The wallet backstop: rotating IPs must not bypass the daily cap."""
    monkeypatch.setattr(rate_limit._global, "limit", 2)
    client = _client_with_limit()

    assert client.post("/paid", headers={"x-forwarded-for": "198.51.100.1"}).status_code == 200
    assert client.post("/paid", headers={"x-forwarded-for": "198.51.100.2"}).status_code == 200

    blocked = client.post("/paid", headers={"x-forwarded-for": "198.51.100.3"})
    assert blocked.status_code == 429


def test_disabling_the_limiter_is_honored(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "rate_limit_enabled", False)
    monkeypatch.setattr(rate_limit._per_ip, "limit", 1)
    client = _client_with_limit()
    headers = {"x-forwarded-for": "198.51.100.7"}

    for _ in range(4):
        assert client.post("/paid", headers=headers).status_code == 200
