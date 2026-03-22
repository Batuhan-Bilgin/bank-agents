"""
MASAK (Mali Suçları Araştırma Kurulu) Integration Client
Turkish Financial Intelligence Unit — AML Reporting & STR Submission

Real API: https://www.masak.gov.tr (institutional access only)
Requires: MASAK_API_KEY, MASAK_INSTITUTION_CODE env vars

This client handles:
  1. Suspicious Transaction Report (STR / ŞİT) submission
  2. Customer risk screening against MASAK watchlists
  3. CTR (Cash Transaction Report / NBF) submission
  4. Politically Exposed Persons (PEP) database query
"""
import time
import uuid
import logging
import random
from datetime import datetime

from integrations.base_client import BaseIntegrationClient
from integrations.config import get_config

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


class MASAKClient(BaseIntegrationClient):
    """
    MASAK e-Bildirim / AML API client.

    Endpoints:
      POST /auth/token           — API key → JWT
      POST /str/submit           — STR (Şüpheli İşlem Bildirimi)
      POST /ctr/submit           — CTR (Nakit Bildirim Formu)
      POST /screening/customer   — AML customer risk screening
      GET  /pep/query            — PEP database query
      GET  /watchlist/check      — MASAK izleme listesi
    """

    def __init__(self):
        cfg = get_config()
        super().__init__(base_url=cfg.masak_base_url, timeout=cfg.http_timeout,
                         max_retries=cfg.http_retries)
        self._api_key = cfg.masak_api_key
        self._institution_code = cfg.masak_institution_code

    def _headers(self, extra: dict | None = None) -> dict:
        h = super()._headers(extra)
        h["X-Institution-Code"] = self._institution_code or ""
        h["X-API-Key"] = self._api_key or ""
        return h

    def submit_str(self, customer_id: str, transaction_data: dict,
                   typologies: list[str], alert_score: float) -> dict:
        """Submit Suspicious Transaction Report to MASAK."""
        payload = {
            "reportId": f"STR-{uuid.uuid4().hex[:12].upper()}",
            "institutionCode": self._institution_code,
            "reportDate": _now(),
            "subject": {
                "customerId": customer_id,
                "reportBasis": typologies,
            },
            "transactionDetails": transaction_data,
            "riskScore": alert_score,
            "reporterUserId": "AML_AGENT_SYSTEM",
        }
        return self._post("str/submit", body=payload)

    def screen_customer(self, customer_id: str, screening_type: str,
                        transaction_data: dict | None = None,
                        lookback_days: int = 90) -> dict:
        """AML behavioral screening."""
        payload = {
            "customerId": customer_id,
            "screeningType": screening_type.upper(),
            "lookbackDays": lookback_days,
            "transactionData": transaction_data or {},
            "requestId": f"SCR-{int(time.time())}",
        }
        return self._post("screening/customer", body=payload)

    def check_pep(self, name: str, nationality: str | None = None,
                  date_of_birth: str | None = None) -> dict:
        """PEP (Politically Exposed Person) database query."""
        params: dict = {"name": name}
        if nationality:
            params["nationality"] = nationality
        if date_of_birth:
            params["dateOfBirth"] = date_of_birth
        return self._get("pep/query", params=params)

    def check_watchlist(self, name: str, entity_type: str = "individual") -> dict:
        """MASAK izleme listesi kontrolü."""
        params = {"name": name, "entityType": entity_type.upper()}
        return self._get("watchlist/check", params=params)

    def _parse_screening(self, raw: dict, customer_id: str,
                         screening_type: str, lookback_days: int) -> dict:
        """Normalize MASAK response."""
        alert_score = raw.get("riskScore", 0.0)
        typologies = raw.get("typologiesDetected", [])
        return {
            "screening_type": screening_type,
            "customer_id": customer_id,
            "lookback_days": lookback_days,
            "source": "LIVE",
            "alert_score": alert_score,
            "alert_generated": raw.get("alertGenerated", False),
            "typologies_detected": typologies,
            "str_candidate": raw.get("strCandidate", False),
            "case_id": raw.get("caseId"),
            "screened_at": _now(),
        }


# ---------------------------------------------------------------------------
# Mock fallback
# ---------------------------------------------------------------------------

_AML_TYPOLOGIES = [
    "STRUCTURING", "LAYERING_MULTIPLE_ACCOUNTS",
    "RAPID_FUND_MOVEMENT", "HIGH_RISK_JURISDICTION",
    "ROUND_AMOUNT_PATTERN", "CASH_INTENSIVE_BUSINESS",
    "SUSPICIOUS_WIRE_TRANSFER", "SMURFING",
]


def _mock_aml_screening(screening_type: str, customer_id: str,
                        transaction_data: dict | None = None,
                        lookback_days: int = 90) -> dict:
    alert_score = round(random.uniform(0, 1), 3)
    typologies = []
    if alert_score > 0.6:
        typologies = random.sample(_AML_TYPOLOGIES, k=random.randint(1, 2))
    return {
        "screening_type": screening_type,
        "customer_id": customer_id,
        "lookback_days": lookback_days,
        "source": "MOCK",
        "alert_score": alert_score,
        "alert_generated": alert_score > 0.6,
        "typologies_detected": typologies,
        "str_candidate": alert_score > 0.8,
        "case_id": f"AML-{random.randint(100000, 999999)}" if alert_score > 0.6 else None,
        "screened_at": _now(),
    }


def _mock_sanctions_check(name: str, entity_type: str = "individual",
                           lists_to_check: list | None = None) -> dict:
    lists = lists_to_check or ["OFAC_SDN", "UN_CONSOLIDATED", "EU_SANCTIONS", "TR_OFFICIAL"]
    is_hit = random.random() < 0.02  # 2% hit rate
    matches = []
    if is_hit:
        matches = [{
            "list": random.choice(lists),
            "matched_name": name,
            "similarity_score": round(random.uniform(0.85, 1.0), 3),
            "list_entry_id": f"SDN-{random.randint(10000, 99999)}",
            "match_type": "exact",
        }]
    return {
        "screened_name": name,
        "entity_type": entity_type,
        "lists_checked": lists,
        "source": "MOCK",
        "hit": is_hit,
        "match_count": len(matches),
        "matches": matches,
        "action_required": "BLOCK_AND_REPORT" if is_hit else "CLEAR",
        "screened_at": _now(),
    }


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

_client: MASAKClient | None = None


def screen_aml(screening_type: str, customer_id: str,
               transaction_data: dict | None = None,
               lookback_days: int = 90) -> dict:
    """
    AML screening — MASAK live API or mock fallback.
    """
    cfg = get_config()
    if not cfg.is_masak_configured():
        logger.debug("MASAK not configured — using mock data")
        return _mock_aml_screening(screening_type, customer_id, transaction_data, lookback_days)

    global _client
    if _client is None:
        _client = MASAKClient()

    try:
        raw = _client.screen_customer(customer_id, screening_type, transaction_data, lookback_days)
        return _client._parse_screening(raw, customer_id, screening_type, lookback_days)
    except Exception as exc:
        logger.warning("MASAK live call failed (%s) — falling back to mock", exc)
        result = _mock_aml_screening(screening_type, customer_id, transaction_data, lookback_days)
        result["fallback_reason"] = str(exc)
        return result


def check_sanctions(name: str, entity_type: str = "individual",
                    lists_to_check: list | None = None, **kwargs) -> dict:
    """
    Sanctions screening — MASAK watchlist + international lists.
    Falls back to mock if not configured.
    """
    cfg = get_config()
    if not cfg.is_masak_configured():
        return _mock_sanctions_check(name, entity_type, lists_to_check)

    global _client
    if _client is None:
        _client = MASAKClient()

    try:
        raw = _client.check_watchlist(name, entity_type)
        is_hit = raw.get("hit", False)
        return {
            "screened_name": name,
            "entity_type": entity_type,
            "lists_checked": lists_to_check or ["OFAC_SDN", "UN_CONSOLIDATED",
                                                 "EU_SANCTIONS", "TR_OFFICIAL"],
            "source": "LIVE",
            "hit": is_hit,
            "match_count": len(raw.get("matches", [])),
            "matches": raw.get("matches", []),
            "action_required": "BLOCK_AND_REPORT" if is_hit else "CLEAR",
            "screened_at": _now(),
        }
    except Exception as exc:
        logger.warning("MASAK sanctions check failed (%s) — falling back to mock", exc)
        result = _mock_sanctions_check(name, entity_type, lists_to_check)
        result["fallback_reason"] = str(exc)
        return result


def submit_str_report(customer_id: str, transaction_data: dict,
                      typologies: list[str], alert_score: float) -> dict:
    """Submit STR to MASAK. Returns submission confirmation or error."""
    cfg = get_config()
    if not cfg.is_masak_configured():
        ref = f"STR-MOCK-{random.randint(100000, 999999)}"
        return {
            "success": True,
            "source": "MOCK",
            "submission_id": ref,
            "status": "MOCK_SUBMITTED",
            "note": "MASAK not configured — STR not actually submitted",
            "submitted_at": _now(),
        }

    global _client
    if _client is None:
        _client = MASAKClient()

    try:
        raw = _client.submit_str(customer_id, transaction_data, typologies, alert_score)
        return {
            "success": True,
            "source": "LIVE",
            "submission_id": raw.get("reportId"),
            "status": raw.get("status", "SUBMITTED"),
            "submitted_at": _now(),
        }
    except Exception as exc:
        logger.error("STR submission failed: %s", exc)
        return {
            "success": False,
            "source": "LIVE",
            "error": str(exc),
            "submitted_at": _now(),
        }
