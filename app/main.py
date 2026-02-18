from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO

import pandas as pd
from flask import Flask, render_template, request, send_file

from app.enrichment import dataframe_to_excel_bytes, enrich_creditor_sheet
from app.lusha_client import LushaClient, LushaClientError


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def _read_spreadsheet(file_storage) -> pd.DataFrame:
    filename = (file_storage.filename or "").lower()
    if filename.endswith(".csv"):
        return pd.read_csv(file_storage)
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        return pd.read_excel(file_storage)
    raise ValueError("Unsupported file type. Upload a .csv or .xlsx file.")


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/enrich")
def enrich():
    upload = request.files.get("spreadsheet")
    api_key = request.form.get("lusha_api_key", "").strip() or os.getenv("LUSHA_API_KEY", "")

    if not upload or not upload.filename:
        return render_template("index.html", error="Please upload a spreadsheet file.")
    if not api_key:
        return render_template(
            "index.html",
            error="Please provide your Lusha API key or set LUSHA_API_KEY environment variable.",
        )

    try:
        source_df = _read_spreadsheet(upload)
        client = LushaClient(api_key=api_key)
        enriched = enrich_creditor_sheet(source_df, client)
        file_bytes = dataframe_to_excel_bytes(enriched)
    except (ValueError, LushaClientError) as exc:
        return render_template("index.html", error=str(exc))
    except Exception as exc:  # pragma: no cover
        return render_template(
            "index.html",
            error=f"Unexpected error while processing file: {exc}",
        )

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_name = f"enriched_creditor_list_{timestamp}.xlsx"
    return send_file(
        BytesIO(file_bytes),
        as_attachment=True,
        download_name=output_name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
