from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


class LushaClientError(RuntimeError):
    """Raised when Lusha enrichment fails."""


@dataclass
class EnrichedCompany:
    address: str = ""
    finance_contact_name: str = ""
    finance_contact_email: str = ""
    finance_contact_phone: str = ""


class LushaClient:
    """Client for enriching company + finance contacts from official Lusha endpoints."""

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout_seconds: int = 20,
    ) -> None:
        self.api_key = api_key
        self.base_url = (base_url or os.getenv("LUSHA_BASE_URL", "https://api.lusha.com")).rstrip("/")
        self.timeout_seconds = timeout_seconds

        self.company_lookup_endpoint = os.getenv("LUSHA_COMPANY_ENDPOINT", "/v2/company")
        self.contact_search_endpoint = os.getenv(
            "LUSHA_CONTACT_SEARCH_ENDPOINT", "/prospecting/contact/search"
        )

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "api_key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def enrich_company(self, company_name: str) -> EnrichedCompany:
        """Returns company details from GET /v2/company and finance contact from contact search."""
        if not company_name.strip():
            return EnrichedCompany()

        company_payload = self._fetch_company(company_name)
        company = company_payload.get("company") or company_payload.get("data") or company_payload

        address = self._extract_address(company)

        # Contact can arrive in either company payload or a dedicated contact-search endpoint.
        contact = self._extract_finance_contact(company, company_payload)
        if not contact:
            contact_payload = self._search_finance_contact(company_name)
            contact = self._extract_finance_contact(contact_payload, contact_payload)

        if not contact:
            return EnrichedCompany(address=address)

        return EnrichedCompany(
            address=address,
            finance_contact_name=contact.get("name", ""),
            finance_contact_email=contact.get("email", ""),
            finance_contact_phone=contact.get("phone", ""),
        )

    def _fetch_company(self, company_name: str) -> Dict[str, Any]:
        url = f"{self.base_url}{self.company_lookup_endpoint}"
        params = {"company_name": company_name}

        try:
            response = requests.get(
                url,
                params=params,
                headers=self._headers,
                timeout=self.timeout_seconds,
            )
            if response.status_code >= 400:
                raise LushaClientError(
                    f"Lusha company lookup failed ({response.status_code}): {response.text[:300]}"
                )
            return response.json()
        except requests.RequestException as exc:
            raise LushaClientError(f"Unable to reach Lusha company endpoint: {exc}") from exc

    def _search_finance_contact(self, company_name: str) -> Dict[str, Any]:
        url = f"{self.base_url}{self.contact_search_endpoint}"
        payload = {
            "company_name": company_name,
            "departments": ["Finance"],
            "limit": 1,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._headers,
                timeout=self.timeout_seconds,
            )
            # Contact search can be blocked by account permission while company lookup still succeeds.
            if response.status_code in {401, 403, 404}:
                return {}
            if response.status_code >= 400:
                raise LushaClientError(
                    f"Lusha contact search failed ({response.status_code}): {response.text[:300]}"
                )
            return response.json()
        except requests.RequestException as exc:
            raise LushaClientError(f"Unable to reach Lusha contact search endpoint: {exc}") from exc

    @staticmethod
    def _pick_first(data: Dict[str, Any], keys: list[str]) -> Any:
        for key in keys:
            if key in data and data[key]:
                return data[key]
        return None

    def _extract_address(self, company: Dict[str, Any]) -> str:
        address_block = self._pick_first(
            company,
            ["address", "hq_address", "headquarters", "primary_address", "office_address"],
        ) or {}

        if isinstance(address_block, str):
            return address_block

        line1 = self._pick_first(address_block, ["line1", "street", "address1", "address"])
        city = self._pick_first(address_block, ["city", "town"])
        state = self._pick_first(address_block, ["state", "region", "province"])
        postcode = self._pick_first(address_block, ["postal_code", "zip", "postcode"])
        country = self._pick_first(address_block, ["country", "country_name"])

        full = [line1, city, state, postcode, country]
        return ", ".join(str(part).strip() for part in full if part)

    def _extract_finance_contact(
        self, company_payload: Dict[str, Any], raw_payload: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        contacts = (
            raw_payload.get("contacts")
            or raw_payload.get("items")
            or raw_payload.get("results")
            or company_payload.get("contacts")
            or company_payload.get("people")
            or []
        )

        finance_candidates: list[dict[str, Any]] = []
        for contact in contacts:
            title = str(self._pick_first(contact, ["title", "job_title", "position"]) or "").lower()
            department = str(self._pick_first(contact, ["department", "team"]) or "").lower()
            if "finance" in title or "finance" in department or "cfo" in title:
                finance_candidates.append(contact)

        target = finance_candidates[0] if finance_candidates else (contacts[0] if contacts else None)
        if not target:
            return None

        first_name = self._pick_first(target, ["first_name", "firstName", "fname"]) or ""
        last_name = self._pick_first(target, ["last_name", "lastName", "lname"]) or ""
        full_name = self._pick_first(target, ["name", "full_name"]) or f"{first_name} {last_name}".strip()
        email = self._pick_first(target, ["email", "work_email", "business_email"]) or ""
        phone = self._pick_first(target, ["phone", "mobile", "work_phone", "direct_phone"]) or ""

        return {
            "name": str(full_name).strip(),
            "email": str(email).strip(),
            "phone": str(phone).strip(),
        }
