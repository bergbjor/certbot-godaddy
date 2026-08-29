"""
Certbot DNS authenticator plugin for GoDaddy using Personal Access Token (PAT).

Usage:
    certbot certonly \\
        --authenticator dns-godaddy-pat \\
        --dns-godaddy-pat-credentials /etc/letsencrypt/godaddy-pat.ini \\
        -d example.com
"""

import logging
from typing import Any, Optional

from certbot import errors
from certbot.plugins import dns_common

from certbot_dns_godaddy_pat._internal._api import GoDaddyClient

logger = logging.getLogger(__name__)


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for GoDaddy using a Personal Access Token (PAT)."""

    description = (
        "Obtain certificates using a DNS TXT record via the GoDaddy API "
        "(Personal Access Token authentication)."
    )

    # CLI argument prefix (certbot builds --dns-godaddy-pat-credentials etc.)
    _OPTION_PREFIX = "dns_godaddy_pat"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client: Optional[GoDaddyClient] = None

    @classmethod
    def add_parser_arguments(
        cls, add: Any, default_propagation_seconds: int = 60
    ) -> None:
        super().add_parser_arguments(add, default_propagation_seconds)
        add(
            "credentials",
            help="Path to GoDaddy PAT credentials INI file.",
        )

    def more_info(self) -> str:  # pragma: no cover
        return (
            "This plugin configures a DNS TXT record via the GoDaddy API. "
            "Authentication is performed using a GoDaddy Personal Access Token (PAT). "
            "See: https://developer.godaddy.com/keys"
        )

    def _setup_credentials(self) -> None:
        self.credentials = self._configure_credentials(
            "credentials",
            "GoDaddy PAT credentials INI file",
            {"pat": "GoDaddy Personal Access Token (PAT)"},
        )

    def _get_client(self) -> GoDaddyClient:
        if self._client is None:
            pat = self.credentials.conf("pat")
            propagation = self.conf("propagation_seconds")
            self._client = GoDaddyClient(
                pat=pat,
                propagation_seconds=int(propagation),
            )
        return self._client

    def _perform(self, domain: str, validation_name: str, validation: str) -> None:
        """Create the required TXT DNS record."""
        client = self._get_client()
        try:
            zone = client.find_zone(domain)
        except ValueError as exc:
            raise errors.PluginError(str(exc)) from exc

        record_name = client._record_name(domain, zone)
        logger.info(
            "Creating TXT record: %s.%s = %r", record_name, zone, validation
        )
        try:
            client.add_txt_record(zone, record_name, validation)
        except RuntimeError as exc:
            raise errors.PluginError(str(exc)) from exc

    def _cleanup(self, domain: str, validation_name: str, validation: str) -> None:
        """Delete the TXT DNS record."""
        client = self._get_client()
        try:
            zone = client.find_zone(domain)
        except ValueError:
            logger.warning("Could not find zone for %s during cleanup – skipping", domain)
            return

        record_name = client._record_name(domain, zone)
        logger.info("Cleaning up TXT record: %s.%s", record_name, zone)
        client.del_txt_record(zone, record_name, validation)
