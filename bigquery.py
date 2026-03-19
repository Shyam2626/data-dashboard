"""
BigQuery client and query utilities.

Table helpers:  silver("table_name")  →  `project.silver_dataset.table_name`
                gold("table_name")    →  `project.gold_dataset.table_name`

QueryContext handles the dual-path strategy:
  - is_filtered=False  → caller uses gold tables directly (fast, pre-aggregated)
  - is_filtered=True   → caller uses silver tables + msp_cte to filter by product_type
"""

import os
import pandas as pd
import streamlit as st
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

_PROJECT = os.environ.get("BQ_PROJECT") or st.secrets.get("BQ_PROJECT")
_GOLD_DS = os.environ.get("BQ_GOLD_DATASET") or st.secrets.get("BQ_GOLD_DATASET", "gold")


def gold(table: str) -> str:
    return f"`{_PROJECT}.{_GOLD_DS}.{table}`"


_bq_client: bigquery.Client | None = None


def _get_sa_info() -> dict | None:
    try:
        return st.secrets.get("gcp_service_account")
    except Exception:
        return None


def get_bq_client() -> bigquery.Client:
    global _bq_client
    if _bq_client is None:
        sa_info = _get_sa_info()
        if sa_info:
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_info(
                sa_info,
                scopes=["https://www.googleapis.com/auth/bigquery"],
            )
            _bq_client = bigquery.Client(project=_PROJECT, credentials=creds)
        else:
            # Local: use GOOGLE_APPLICATION_CREDENTIALS or ADC
            _bq_client = bigquery.Client(project=_PROJECT)
    return _bq_client


def run_query(sql: str) -> pd.DataFrame:
    return get_bq_client().query(sql).to_dataframe()
