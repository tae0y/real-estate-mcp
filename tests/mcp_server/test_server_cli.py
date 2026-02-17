from __future__ import annotations

import sys
from typing import Any

from real_estate.mcp_server import server


def test_main_http_defaults_to_localhost(monkeypatch: Any) -> None:
    monkeypatch.setattr(sys, "argv", ["server", "--transport", "http"])

    calls: list[str] = []

    def _fake_run(*, transport: str | None = None) -> None:
        calls.append(transport or "stdio")

    monkeypatch.setattr(server.mcp, "run", _fake_run)

    server.main()

    assert server.mcp.settings.host == "127.0.0.1"
    assert server.mcp.settings.port == 8000
    assert calls == ["streamable-http"]
