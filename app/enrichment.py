from __future__ import annotations

from io import BytesIO
from typing import Protocol

import pandas as pd

from app.lusha_client import EnrichedCompany


class CompanyEnricher(Protocol):
    def enrich_company(self, company_name: str) -> EnrichedCompany: ...


REQUIRED_COLUMNS = {"company_name", "amount_lost"}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [str(c).strip().lower().replace(" ", "_") for c in normalized.columns]
    return normalized


def validate_creditor_sheet(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        formatted = ", ".join(sorted(missing))
        raise ValueError(
            "Spreadsheet is missing required columns: "
            f"{formatted}. Expected at least: company_name, amount_lost"
        )


def enrich_creditor_sheet(df: pd.DataFrame, enricher: CompanyEnricher) -> pd.DataFrame:
    working = normalize_columns(df)
    validate_creditor_sheet(working)

    addresses: list[str] = []
    contact_names: list[str] = []
    contact_emails: list[str] = []
    contact_phones: list[str] = []

    for company in working["company_name"].fillna("").astype(str):
        result = enricher.enrich_company(company)
        addresses.append(result.address)
        contact_names.append(result.finance_contact_name)
        contact_emails.append(result.finance_contact_email)
        contact_phones.append(result.finance_contact_phone)

    working["business_address"] = addresses
    working["finance_contact_name"] = contact_names
    working["finance_contact_email"] = contact_emails
    working["finance_contact_phone"] = contact_phones

    return working


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    with BytesIO() as output:
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="enriched_creditor_list")
        return output.getvalue()
