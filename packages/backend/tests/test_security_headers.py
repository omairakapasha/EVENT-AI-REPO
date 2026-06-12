"""
Tests for SecurityHeadersMiddleware.
Verifies all required security headers are present on every response.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EXPECTED_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "x-xss-protection": "1; mode=block",
    "referrer-policy": "strict-origin-when-cross-origin",
    "strict-transport-security": "max-age=31536000; includeSubDomains",
}


class TestSecurityHeaders:
    async def test_security_headers_on_public_route(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        for header, value in EXPECTED_HEADERS.items():
            assert resp.headers.get(header) == value, (
                f"Missing or wrong header {header!r}: got {resp.headers.get(header)!r}"
            )

    async def test_csp_header_present(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    async def test_permissions_policy_header_present(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        pp = resp.headers.get("permissions-policy", "")
        assert "geolocation=()" in pp

    async def test_security_headers_on_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/nonexistent-route-xyz")
        for header in EXPECTED_HEADERS:
            assert header in resp.headers, f"Missing header {header!r} on 404 response"

    async def test_security_headers_on_auth_route(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", data={"username": "x@x.com", "password": "wrong"})
        for header in EXPECTED_HEADERS:
            assert header in resp.headers, f"Missing header {header!r} on auth route"
