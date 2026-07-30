"""Read-only k-anonymous blocklist client used by Detection overrides."""

from __future__ import annotations

import httpx

from chan_ml.indicators import hash_prefix
from chan_ml.redact import RedactionResult

from .config import DetectionConfig


class IntelLookupClient:
    def __init__(self, config: DetectionConfig) -> None:
        self._base_url = config.intel_api_url
        self._timeout = config.request_timeout_seconds

    def contains(self, redaction: RedactionResult) -> bool:
        groups = (
            ("account", redaction.account_hashes),
            ("phone", redaction.phone_hashes),
            ("url", redaction.url_hashes),
        )
        try:
            with httpx.Client(timeout=self._timeout) as client:
                for kind, digests in groups:
                    for digest in digests:
                        prefix = hash_prefix(digest)
                        response = client.get(
                            f"{self._base_url}/v1/lookup/{kind}",
                            params={"prefix": prefix},
                        )
                        response.raise_for_status()
                        for item in response.json().get("items", []):
                            if prefix + str(item.get("suffix", "")) == digest:
                                return True
        except (httpx.HTTPError, AttributeError, ValueError):
            # Threat-intel availability must not turn inference into an outage.
            return False
        return False
