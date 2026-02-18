import pytest

pytest.importorskip("requests")

from app.lusha_client import LushaClient


class DummyResponse:
    def __init__(self, status_code: int, payload: dict, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


def test_enrich_company_uses_company_and_contact_endpoints(monkeypatch):
    client = LushaClient(api_key="secret", base_url="https://api.lusha.com")

    def fake_get(url, params, headers, timeout):
        assert url.endswith("/v2/company")
        assert params == {"company_name": "Acme Ltd"}
        assert headers["api_key"] == "secret"
        return DummyResponse(
            200,
            {
                "company": {
                    "address": {
                        "line1": "1 King St",
                        "city": "London",
                        "country": "UK",
                    }
                }
            },
        )

    def fake_post(url, json, headers, timeout):
        assert url.endswith("/prospecting/contact/search")
        assert json["company_name"] == "Acme Ltd"
        return DummyResponse(
            200,
            {
                "results": [
                    {
                        "name": "Jane Finance",
                        "title": "Finance Director",
                        "email": "jane@example.com",
                        "phone": "+44 20 1111 2222",
                    }
                ]
            },
        )

    monkeypatch.setattr("app.lusha_client.requests.get", fake_get)
    monkeypatch.setattr("app.lusha_client.requests.post", fake_post)

    result = client.enrich_company("Acme Ltd")

    assert result.address == "1 King St, London, UK"
    assert result.finance_contact_name == "Jane Finance"
    assert result.finance_contact_email == "jane@example.com"


def test_enrich_company_keeps_address_when_contact_endpoint_forbidden(monkeypatch):
    client = LushaClient(api_key="secret", base_url="https://api.lusha.com")

    monkeypatch.setattr(
        "app.lusha_client.requests.get",
        lambda *args, **kwargs: DummyResponse(200, {"company": {"address": "10 Main Rd"}}),
    )
    monkeypatch.setattr(
        "app.lusha_client.requests.post",
        lambda *args, **kwargs: DummyResponse(403, {}, "forbidden"),
    )

    result = client.enrich_company("No Contact Co")

    assert result.address == "10 Main Rd"
    assert result.finance_contact_name == ""
