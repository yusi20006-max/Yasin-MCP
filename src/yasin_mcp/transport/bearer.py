"""Bearer shared-secret TokenVerifier for remote MCP (Stage 12)."""

from __future__ import annotations

import hmac

from mcp.server.auth.provider import AccessToken

from yasin_mcp.config.config import SecretStr


class SharedSecretTokenVerifier:
    def __init__(
        self,
        *,
        auth_token: SecretStr,
        subject_id: str,
        client_id: str = "remote-client",
    ) -> None:
        self._secret = auth_token.get_secret_value()
        self._subject_id = subject_id
        self._client_id = client_id

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or not self._secret:
            return None
        if not hmac.compare_digest(token, self._secret):
            return None
        return AccessToken(
            token="***",
            client_id=self._client_id,
            scopes=["mcp"],
            expires_at=None,
            resource=None,
            claims={"sub": self._subject_id},
        )


def extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    parts = authorization_header.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None
