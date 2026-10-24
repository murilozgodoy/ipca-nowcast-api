"""Base HTTP client with retry, backoff and (optional) response cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ipca_nowcast.config import get_settings
from ipca_nowcast.logging import get_logger

_logger = get_logger(__name__)


class HttpClient:
    """Thin wrapper around httpx with tenacity-powered retries."""

    def __init__(
        self,
        base_url: str = "",
        timeout: float | None = None,
        cache_dir: Path | None = None,
        max_retries: int | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = base_url
        self.timeout = timeout or settings.http_timeout_seconds
        self.cache_dir = cache_dir
        self.max_retries = max_retries or settings.http_max_retries
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, method: str, url: str, params: dict[str, Any] | None) -> Path | None:
        if self.cache_dir is None:
            return None
        key = json.dumps(
            {"method": method, "url": url, "params": params},
            sort_keys=True,
            default=str,
        ).encode()
        digest = hashlib.sha256(key).hexdigest()[:24]
        return self.cache_dir / f"{digest}.json"

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        use_cache: bool = False,
    ) -> Any:
        """GET a URL and parse JSON. Returns `None` on 404.

        `use_cache=True` writes the raw JSON to `cache_dir` and short-circuits
        on cache hit (useful for development; tests disable this).
        """
        full_url = url if url.startswith("http") else f"{self.base_url}{url}"
        cache_path = self._cache_path("GET", full_url, params) if use_cache else None
        if cache_path is not None and cache_path.exists():
            _logger.debug("http_cache_hit", url=full_url, cache=str(cache_path))
            return json.loads(cache_path.read_text(encoding="utf-8"))

        payload = self._do_get(full_url, params)
        if cache_path is not None and payload is not None:
            cache_path.write_text(
                json.dumps(payload, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        return payload

    def _do_get(self, url: str, params: dict[str, Any] | None) -> Any:
        import logging as _stdlogging

        bound = _logger.bind(url=url, params=params)
        stdlogger = _stdlogging.getLogger(__name__)

        @retry(
            reraise=True,
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=15),
            retry=retry_if_exception_type(
                (httpx.TransportError, httpx.HTTPStatusError, httpx.ReadTimeout)
            ),
            before_sleep=before_sleep_log(stdlogger, _stdlogging.WARNING),
        )
        def _call() -> Any:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
                if response.status_code == 404:
                    bound.info("http_404", status=404)
                    return None
                response.raise_for_status()
                return response.json()

        return _call()
