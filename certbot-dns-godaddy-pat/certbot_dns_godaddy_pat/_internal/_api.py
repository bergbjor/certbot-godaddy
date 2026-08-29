"""
GoDaddy API client using Personal Access Token (PAT).

Uses:
  - API v1 for creating TXT records (PUT /v1/domains/{zone}/records/TXT/{name})
  - API v3 for listing + deleting records via recordId
"""

import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

GODADDY_API_BASE = "https://api.godaddy.com"


class GoDaddyClient:
    """Minimal GoDaddy DNS client that authenticates with a PAT (Bearer token)."""

    def __init__(self, pat: str, propagation_seconds: int = 60) -> None:
        self.pat = pat
        self.propagation_seconds = propagation_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {pat}",
                "Accept": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Zone detection
    # ------------------------------------------------------------------

    def find_zone(self, domain: str) -> str:
        """
        Find the registered zone (zone apex) for *domain* by probing GoDaddy API.

        Iterates from the most-specific to least-specific candidate, returning
        the first one that the authenticated account recognises as a registered
        domain.

        Raises ``ValueError`` if no matching zone is found.
        """
        domain = domain.rstrip(".").lower()
        parts = domain.split(".")
        for i in range(len(parts) - 1):
            candidate = ".".join(parts[i:])
            try:
                resp = self.session.get(
                    f"{GODADDY_API_BASE}/v1/domains/{candidate}",
                    timeout=15,
                )
                if resp.status_code == 200:
                    logger.debug("Resolved zone: %s", candidate)
                    return candidate
            except requests.RequestException as exc:
                logger.warning("Error probing zone %s: %s", candidate, exc)

        raise ValueError(
            f"Could not find a registered GoDaddy zone for domain: {domain}"
        )

    # ------------------------------------------------------------------
    # TXT record helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _record_name(domain: str, zone: str) -> str:
        """Return the relative record name (e.g. '_acme-challenge.sub')."""
        if domain == zone:
            return "_acme-challenge"
        sub = domain[: -(len(zone) + 1)]  # strip '.<zone>'
        return f"_acme-challenge.{sub}"

    def add_txt_record(
        self, zone: str, record_name: str, value: str, ttl: int = 600
    ) -> None:
        """
        Create or replace a TXT record via GoDaddy API v1 (PUT).

        GoDaddy v1 PUT replaces all records of that type+name, which is fine
        for ACME challenges (only one value needed at a time).
        """
        url = f"{GODADDY_API_BASE}/v1/domains/{zone}/records/TXT/{record_name}"
        payload = [{"data": value, "ttl": ttl}]
        resp = self.session.put(url, json=payload, timeout=15)
        if resp.status_code not in (200, 204):
            raise RuntimeError(
                f"Failed to create TXT record {record_name}.{zone} "
                f"(HTTP {resp.status_code}): {resp.text}"
            )
        logger.info(
            "Created TXT %s.%s = %r (TTL %d)", record_name, zone, value, ttl
        )
        logger.info(
            "Waiting %d seconds for DNS propagation…", self.propagation_seconds
        )
        time.sleep(self.propagation_seconds)

    def del_txt_record(self, zone: str, record_name: str, value: str) -> None:
        """
        Delete the specific TXT record by finding its recordId via API v3 and then
        issuing DELETE.  Silently succeeds if the record no longer exists.
        """
        # 1. Find the recordId
        list_url = (
            f"{GODADDY_API_BASE}/v3/domains/zones/{zone}/dns-records"
            f"?type=TXT&name={record_name}"
        )
        resp = self.session.get(list_url, timeout=15)
        if resp.status_code != 200:
            logger.warning(
                "Could not list TXT records for %s.%s (HTTP %d) – skipping cleanup",
                record_name,
                zone,
                resp.status_code,
            )
            return

        data = resp.json()
        items = data.get("items", [])
        record_id: Optional[str] = None
        for item in items:
            if item.get("data") == value:
                record_id = item.get("recordId")
                break
        # Fall back to first matching name if exact value not found
        if record_id is None and items:
            record_id = items[0].get("recordId")

        if not record_id:
            logger.info(
                "No TXT record found for %s.%s – nothing to clean up",
                record_name,
                zone,
            )
            return

        # 2. Delete by recordId
        delete_url = (
            f"{GODADDY_API_BASE}/v3/domains/zones/{zone}/dns-records/{record_id}"
        )
        del_resp = self.session.delete(delete_url, timeout=15)
        if del_resp.status_code not in (200, 204):
            logger.warning(
                "Failed to delete record %s (HTTP %d): %s",
                record_id,
                del_resp.status_code,
                del_resp.text,
            )
        else:
            logger.info(
                "Deleted TXT record %s.%s (recordId: %s)",
                record_name,
                zone,
                record_id,
            )
