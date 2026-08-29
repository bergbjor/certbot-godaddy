import unittest
from unittest.mock import patch

from certbot_dns_godaddy_pat._internal._api import GoDaddyClient


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, timeout):
        self.calls.append(("GET", url))
        if "/v1/domains/example.com" in url:
            return FakeResponse(200)
        return FakeResponse(404)

    def put(self, url, json, timeout):
        self.calls.append(("PUT", url, json))
        return FakeResponse(200)

    def delete(self, url, timeout):
        self.calls.append(("DELETE", url))
        return FakeResponse(204)


class GoDaddyClientTests(unittest.TestCase):
    def setUp(self):
        self.client = GoDaddyClient("test-pat", propagation_seconds=0)
        self.session = FakeSession()
        self.client.session = self.session

    def test_find_zone_and_record_name(self):
        self.assertEqual(self.client.find_zone("WWW.Example.com."), "example.com")
        self.assertEqual(
            self.client._record_name("www.example.com", "example.com"),
            "_acme-challenge.www",
        )

    @patch("certbot_dns_godaddy_pat._internal._api.time.sleep")
    def test_add_txt_record(self, sleep):
        self.client.add_txt_record("example.com", "_acme-challenge", "token")
        method, url, payload = self.session.calls[-1]
        self.assertEqual(method, "PUT")
        self.assertIn("/records/TXT/_acme-challenge", url)
        self.assertEqual(payload[0]["data"], "token")
        sleep.assert_called_once_with(0)

    def test_delete_txt_record_uses_matching_record(self):
        self.session.get = lambda url, timeout: FakeResponse(
            200,
            {"items": [
                {"recordId": "wrong", "data": "other"},
                {"recordId": "right", "data": "token"},
            ]},
        )
        self.client.del_txt_record("example.com", "_acme-challenge", "token")
        self.assertEqual(self.session.calls[-1], (
            "DELETE",
            "https://api.godaddy.com/v3/domains/zones/example.com/dns-records/right",
        ))


if __name__ == "__main__":
    unittest.main()
