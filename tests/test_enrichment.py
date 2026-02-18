import pytest

pd = pytest.importorskip("pandas")

from app.enrichment import enrich_creditor_sheet, validate_creditor_sheet
from app.lusha_client import EnrichedCompany


class FakeEnricher:
    def enrich_company(self, company_name: str) -> EnrichedCompany:
        return EnrichedCompany(
            address=f"{company_name} Address",
            finance_contact_name=f"{company_name} Finance",
            finance_contact_email=f"finance@{company_name.lower().replace(' ', '')}.com",
            finance_contact_phone="+44 20 1234 5678",
        )


def test_enrich_creditor_sheet_adds_expected_columns():
    source = pd.DataFrame(
        {
            "Company Name": ["Acme Ltd", "Globex"],
            "Amount Lost": [1000, 2500],
        }
    )

    enriched = enrich_creditor_sheet(source, FakeEnricher())

    assert "business_address" in enriched.columns
    assert "finance_contact_name" in enriched.columns
    assert enriched.loc[0, "business_address"] == "Acme Ltd Address"


def test_validate_creditor_sheet_requires_columns():
    invalid = pd.DataFrame({"company": ["Only Name"]})
    with pytest.raises(ValueError, match="missing required columns"):
        validate_creditor_sheet(invalid)
