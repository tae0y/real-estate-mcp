from __future__ import annotations

import sys
from typing import Any

from real_estate.mcp_server import server


def test_main_http_defaults_to_localhost(monkeypatch: Any) -> None:
    monkeypatch.setattr(sys, "argv", ["server", "--transport", "http"])
    monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)

    calls: list[dict[str, Any]] = []

    def _fake_uvicorn_run(app: Any, **kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr("uvicorn.run", _fake_uvicorn_run)

    server.main()

    assert server.mcp.settings.host == "127.0.0.1"
    assert server.mcp.settings.port == 8000
    assert calls == [
        {
            "host": "127.0.0.1",
            "port": 8000,
            "proxy_headers": True,
            "forwarded_allow_ips": "127.0.0.1",
        }
    ]
