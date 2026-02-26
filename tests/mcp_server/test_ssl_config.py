"""Tests for SSL verification configuration helpers."""

from real_estate.mcp_server import _helpers


def test_resolve_ssl_verify_returns_false_when_insecure_enabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("REAL_ESTATE_INSECURE_SSL", "1")
    monkeypatch.delenv("REAL_ESTATE_SSL_CA_BUNDLE", raising=False)
    assert _helpers._resolve_ssl_verify() is False


def test_resolve_ssl_verify_prefers_ca_bundle_env(monkeypatch) -> None:
    monkeypatch.delenv("REAL_ESTATE_INSECURE_SSL", raising=False)
    monkeypatch.setenv("REAL_ESTATE_SSL_CA_BUNDLE", "/tmp/company-ca.pem")
    monkeypatch.setattr(_helpers, "_create_ssl_context", lambda path: f"CTX::{path}")
    assert _helpers._resolve_ssl_verify() == "CTX::/tmp/company-ca.pem"


def test_resolve_ssl_verify_uses_macos_bundle_when_enabled(monkeypatch) -> None:
    monkeypatch.delenv("REAL_ESTATE_INSECURE_SSL", raising=False)
    monkeypatch.delenv("REAL_ESTATE_SSL_CA_BUNDLE", raising=False)
    monkeypatch.setenv("REAL_ESTATE_USE_MACOS_KEYCHAIN_CA", "1")
    monkeypatch.setattr(_helpers, "_create_ssl_context", lambda path: f"CTX::{path}")
    monkeypatch.setattr(
        _helpers,
        "_get_macos_keychain_ca_bundle",
        lambda: "/tmp/macos-keychain-ca.pem",
    )
    assert _helpers._resolve_ssl_verify() == "CTX::/tmp/macos-keychain-ca.pem"


def test_resolve_ssl_verify_returns_true_when_no_override(monkeypatch) -> None:
    monkeypatch.delenv("REAL_ESTATE_INSECURE_SSL", raising=False)
    monkeypatch.delenv("REAL_ESTATE_SSL_CA_BUNDLE", raising=False)
    monkeypatch.setenv("REAL_ESTATE_USE_MACOS_KEYCHAIN_CA", "0")
    assert _helpers._resolve_ssl_verify() is True
