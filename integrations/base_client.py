import time
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BaseIntegrationClient:

    def __init__(
        self,
        base_url: str,
        timeout: float = 15.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        if extra:
            h.update(extra)
        return h

    def _get(self, path: str, params: dict | None = None,
             extra_headers: dict | None = None) -> dict:
        return self._request("GET", path, params=params, extra_headers=extra_headers)

    def _post(self, path: str, body: dict | None = None,
              extra_headers: dict | None = None) -> dict:
        return self._request("POST", path, body=body, extra_headers=extra_headers)

    def _request(self, method: str, path: str, params: dict | None = None,
                 body: dict | None = None, extra_headers: dict | None = None) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = self._headers(extra_headers)
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=body,
                    )

                logger.debug(
                    "%s %s → %d (attempt %d/%d)",
                    method, url, response.status_code, attempt, self.max_retries
                )

                if response.status_code == 401:
                    self._token = None
                    self._refresh_token()
                    headers = self._headers(extra_headers)
                    continue

                if response.status_code >= 500:
                    last_exc = RuntimeError(f"Server error {response.status_code}")
                    _backoff(attempt)
                    continue

                response.raise_for_status()

                try:
                    return response.json()
                except Exception:
                    return {"raw": response.text, "status_code": response.status_code}

            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning("Timeout on attempt %d/%d: %s", attempt, self.max_retries, url)
                _backoff(attempt)
            except httpx.ConnectError as exc:
                last_exc = exc
                logger.warning("Connection error on attempt %d/%d: %s", attempt, self.max_retries, url)
                _backoff(attempt)

        raise ConnectionError(
            f"Integration request failed after {self.max_retries} attempts: {url}"
        ) from last_exc

    def _refresh_token(self) -> None:
        pass


def _backoff(attempt: int, base: float = 0.5) -> None:
    time.sleep(base * (2 ** (attempt - 1)))
