from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes
    headers: dict[str, str]
    final_url: str

    def json(self) -> dict:
        value = json.loads(self.body.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("expected a JSON object response")
        return value


class Transport(Protocol):
    def get(self, url: str, query: dict[str, str], timeout: float) -> HttpResponse: ...


class UrlLibTransport:
    """Small dependency-free HTTPS transport with a fixed user agent."""

    def get(self, url: str, query: dict[str, str], timeout: float) -> HttpResponse:
        if not url.startswith("https://"):
            raise ValueError("public data requests require HTTPS")
        encoded = urllib.parse.urlencode(query)
        request_url = f"{url}?{encoded}" if encoded else url
        request = urllib.request.Request(
            request_url,
            headers={"Accept": "application/json", "User-Agent": "FarmTact-data-foundation/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return HttpResponse(
                    status=response.status,
                    body=response.read(),
                    headers={key.lower(): value for key, value in response.headers.items()},
                    final_url=response.geturl(),
                )
        except urllib.error.HTTPError as error:
            return HttpResponse(
                status=error.code,
                body=error.read(),
                headers={key.lower(): value for key, value in error.headers.items()},
                final_url=error.geturl(),
            )
