import time
import base64
import logging
import random
import hashlib
from datetime import datetime, timedelta
from typing import Any

import httpx

from integrations.base_client import BaseIntegrationClient
from integrations.config import get_config

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _mask(value: str, visible: int = 4) -> str:
    if len(value) <= visible:
        return "*" * len(value)
    return "*" * (len(value) - visible) + value[-visible:]


class T24Client(BaseIntegrationClient):

    def __init__(self):
        cfg = get_config()
        super().__init__(
            base_url=cfg.t24_base_url,
            timeout=cfg.http_timeout,
            max_retries=cfg.http_retries,
        )
        self._username = cfg.t24_username
        self._password = cfg.t24_password
        self._company_id = cfg.t24_company_id

    def _headers(self, extra: dict | None = None) -> dict:
        credentials = base64.b64encode(
            f"{self._username}:{self._password}".encode()
        ).decode()
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Basic {credentials}",
            "X-T24-Company": self._company_id,
        }
        if extra:
            h.update(extra)
        return h

    def get_customer(self, customer_id: str) -> dict:
        return self._get(f"party/customers/{customer_id}")

    def search_customers(self, query_params: dict) -> dict:
        return self._post("party/customers/search", body=query_params)

    def get_account(self, account_id: str) -> dict:
        return self._get(f"holdings/accounts/{account_id}")

    def get_accounts_for_customer(self, customer_id: str) -> dict:
        return self._get("holdings/accounts", params={"customerId": customer_id})

    def get_transactions(self, account_id: str,
                         date_from: str | None = None,
                         date_to: str | None = None,
                         limit: int = 50) -> dict:
        params: dict[str, Any] = {"page_size": limit}
        if date_from:
            params["startDate"] = date_from
        if date_to:
            params["endDate"] = date_to
        return self._get(f"holdings/transactions/{account_id}", params=params)

    def get_loans_for_customer(self, customer_id: str) -> dict:
        return self._get("order/loans/arrangements",
                         params={"customerId": customer_id})

    def _normalize_customer(self, raw: dict, customer_id: str) -> dict:
        body = raw.get("body", [raw])[0] if isinstance(raw.get("body"), list) else raw
        return {
            "customer_id": customer_id,
            "source": "LIVE_T24",
            "name": body.get("customerName", ""),
            "segment": body.get("customerSegment", ""),
            "since": body.get("dateJoined", ""),
            "kyc": {
                "status": body.get("kycStatus", "Unknown"),
                "last_review": body.get("lastKycDate", ""),
            },
            "contact": {
                "phone": body.get("phoneNumber", ""),
                "email": body.get("emailAddress", ""),
                "address": body.get("address1", ""),
            },
            "retrieved_at": _now(),
        }

    def _normalize_transactions(self, raw: dict, customer_id: str,
                                 limit: int) -> dict:
        items = raw.get("body", [])
        txns = []
        for item in items[:limit]:
            txns.append({
                "txn_id": item.get("transactionId", ""),
                "date": item.get("bookingDate", ""),
                "amount": float(item.get("transactionAmount", 0)),
                "currency": item.get("currency", "TRY"),
                "type": item.get("creditDebitIndicator", ""),
                "channel": item.get("channel", ""),
                "description": item.get("narrative", ""),
                "counterparty": item.get("counterpartyName", ""),
                "status": item.get("status", ""),
            })
        return {
            "customer_id": customer_id,
            "source": "LIVE_T24",
            "transaction_count": len(txns),
            "transactions": txns,
            "retrieved_at": _now(),
        }

    def execute_sql_like_query(self, query: str, database: str,
                               limit: int = 100) -> dict:
        query_lower = query.lower()
        if "customer" in query_lower:
            raw = self._get("party/customers", params={"page_size": limit})
        elif "loan" in query_lower or "credit" in query_lower:
            raw = self._get("order/loans/arrangements", params={"page_size": limit})
        elif "transaction" in query_lower:
            raw = self._get("holdings/transactions/ALL",
                            params={"page_size": limit})
        elif "account" in query_lower:
            raw = self._get("holdings/accounts", params={"page_size": limit})
        else:
            return {"success": True, "source": "LIVE_T24",
                    "database": database, "rows": [],
                    "note": "Query type not mapped to T24 endpoint"}

        rows = raw.get("body", [])
        return {
            "success": True,
            "source": "LIVE_T24",
            "database": database,
            "row_count": len(rows),
            "rows": rows[:limit],
            "executed_at": _now(),
        }


def _mock_database_query(query: str, database: str, limit: int = 100) -> dict:
    query_lower = query.lower()
    rows = []
    if "customer" in query_lower:
        rows = [
            {"customer_id": f"C{10000+i}", "name": f"Test Customer {i}",
             "segment": random.choice(["Retail", "SME", "Corporate"]),
             "risk_rating": random.choice(["Low", "Medium", "High"]),
             "kyc_status": "Verified"}
            for i in range(min(limit, 5))
        ]
    elif "loan" in query_lower or "credit" in query_lower:
        rows = [
            {"loan_id": f"L{20000+i}", "customer_id": f"C{10000+i}",
             "outstanding": round(random.uniform(10000, 500000), 2),
             "status": random.choice(["Performing", "Watch", "NPL"]),
             "days_past_due": random.randint(0, 180)}
            for i in range(min(limit, 5))
        ]
    elif "transaction" in query_lower:
        rows = [
            {"txn_id": f"T{30000+i}", "amount": round(random.uniform(100, 50000), 2),
             "currency": random.choice(["TRY", "USD", "EUR"]),
             "channel": random.choice(["ATM", "Internet", "Mobile"]),
             "status": "Completed"}
            for i in range(min(limit, 10))
        ]
    else:
        rows = [{"result": "Query executed", "affected_rows": random.randint(0, 50)}]
    return {
        "success": True,
        "source": "MOCK",
        "database": database,
        "query_hash": hashlib.md5(query.encode()).hexdigest()[:8],
        "row_count": len(rows),
        "rows": rows,
        "executed_at": _now(),
    }


def _mock_customer_360(customer_id: str) -> dict:
    seed = int(hashlib.md5(customer_id.encode()).hexdigest(), 16) % 1000
    random.seed(seed)
    return {
        "customer_id": customer_id,
        "source": "MOCK",
        "name": f"Customer {customer_id[-4:]}",
        "segment": random.choice(["Retail", "SME", "Corporate", "VIP"]),
        "since": "2019-06-01",
        "products": {
            "current_accounts": random.randint(1, 3),
            "savings_accounts": random.randint(0, 2),
            "loans": random.randint(0, 3),
            "credit_cards": random.randint(0, 2),
        },
        "balances": {
            "total_deposits_try": round(random.uniform(5000, 500000), 2),
            "total_loans_try": round(random.uniform(0, 1000000), 2),
            "net_position_try": round(random.uniform(-200000, 300000), 2),
        },
        "risk": {
            "credit_score": random.randint(500, 900),
            "risk_rating": random.choice(["Low", "Medium", "High"]),
            "aml_risk": random.choice(["Low", "Medium"]),
            "pep_flag": False,
            "sanctions_flag": False,
        },
        "kyc": {
            "status": "Verified",
            "last_review": "2024-11-01",
            "next_review_due": "2025-11-01",
            "documents": ["National ID", "Proof of Address", "Tax Certificate"],
        },
        "relationship": {
            "relationship_manager": f"RM-{random.randint(100, 999)}",
            "nps_score": random.randint(6, 10),
            "last_contact": "2025-02-15",
        },
        "retrieved_at": _now(),
    }


def _mock_transactions(customer_id: str, limit: int = 50,
                        channel: str = "all") -> dict:
    channels = ["ATM", "Internet", "Mobile", "Branch", "POS", "Wire"]
    txns = [
        {
            "txn_id": f"T{random.randint(1000000, 9999999)}",
            "date": (datetime.utcnow() - timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d"),
            "amount": round(random.uniform(50, 25000), 2),
            "currency": random.choice(["TRY", "TRY", "TRY", "USD", "EUR"]),
            "type": random.choice(["Debit", "Credit"]),
            "channel": random.choice(channels) if channel == "all" else channel,
            "description": "Transaction",
            "counterparty": f"Counterparty-{random.randint(100, 999)}",
            "status": "Completed",
        }
        for _ in range(min(limit, 20))
    ]
    return {
        "customer_id": customer_id,
        "source": "MOCK",
        "transaction_count": len(txns),
        "transactions": txns,
        "retrieved_at": _now(),
    }


_client: T24Client | None = None


def query_core_banking(query: str, database: str, limit: int = 100) -> dict:
    cfg = get_config()
    if not cfg.is_t24_configured():
        logger.debug("T24 not configured — using mock data")
        return _mock_database_query(query, database, limit)

    global _client
    if _client is None:
        _client = T24Client()

    try:
        return _client.execute_sql_like_query(query, database, limit)
    except Exception as exc:
        logger.warning("T24 live call failed (%s) — falling back to mock", exc)
        result = _mock_database_query(query, database, limit)
        result["fallback_reason"] = str(exc)
        return result


def get_customer_360(customer_id: str, include_sections: list | None = None) -> dict:
    cfg = get_config()
    if not cfg.is_t24_configured():
        return _mock_customer_360(customer_id)

    global _client
    if _client is None:
        _client = T24Client()

    try:
        raw = _client.get_customer(customer_id)
        base = _client._normalize_customer(raw, customer_id)

        if not include_sections or "products" in include_sections:
            accts = _client.get_accounts_for_customer(customer_id)
            base["products"] = {"accounts": accts.get("body", [])}

        return base
    except Exception as exc:
        logger.warning("T24 customer 360 failed (%s) — falling back to mock", exc)
        result = _mock_customer_360(customer_id)
        result["fallback_reason"] = str(exc)
        return result


def get_transaction_history(customer_id: str, **kwargs) -> dict:
    cfg = get_config()
    limit = kwargs.get("limit", 50)
    channel = kwargs.get("channel", "all")

    if not cfg.is_t24_configured():
        return _mock_transactions(customer_id, limit, channel)

    global _client
    if _client is None:
        _client = T24Client()

    try:
        accts = _client.get_accounts_for_customer(customer_id)
        accounts = accts.get("body", [])
        if not accounts:
            return _mock_transactions(customer_id, limit, channel)
        account_id = accounts[0].get("accountId", customer_id)
        raw = _client.get_transactions(
            account_id,
            date_from=kwargs.get("date_from"),
            date_to=kwargs.get("date_to"),
            limit=limit,
        )
        return _client._normalize_transactions(raw, customer_id, limit)
    except Exception as exc:
        logger.warning("T24 transactions failed (%s) — falling back to mock", exc)
        result = _mock_transactions(customer_id, limit, channel)
        result["fallback_reason"] = str(exc)
        return result
