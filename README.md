# Creditor List Portal

A lightweight web portal for uploading a creditor list spreadsheet, enriching each business with address + finance contact data from Lusha, and downloading an enriched Excel file.

## What it does

1. Upload `.csv` or `.xlsx` with at least:
   - `company_name`
   - `amount_lost`
2. Uses Lusha's official endpoints:
   - `GET /v2/company` for company details/address
   - `POST /prospecting/contact/search` for a finance contact
3. Returns an `.xlsx` file with extra columns:
   - `business_address`
   - `finance_contact_name`
   - `finance_contact_email`
   - `finance_contact_phone`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set API key one of two ways:

- At runtime via the UI field, or
- Environment variable:

```bash
export LUSHA_API_KEY="your_api_key_here"
```

Optional endpoint tuning (if your account uses custom routing):

```bash
export LUSHA_BASE_URL="https://api.lusha.com"
export LUSHA_COMPANY_ENDPOINT="/v2/company"
export LUSHA_CONTACT_SEARCH_ENDPOINT="/prospecting/contact/search"
```

## Run locally

```bash
python -m app.main
```

Open: `http://localhost:8000`

## Notes on payloads and permissions

- Response field names can vary across plans and products. The parser checks common variants for both address and contact fields.
- If your account does not have access to Contact Search, the app still returns company address data and leaves contact columns blank.
