import time
import logging
import random
import hashlib
from datetime import datetime

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


class KKBClient(BaseIntegrationClient):

    TOKEN_PATH = "oauth/token"

    def __init__(self):
        cfg = get_config()
        super().__init__(base_url=cfg.kkb_base_url, timeout=cfg.http_timeout,
                         max_retries=cfg.http_retries)
        self._client_id = cfg.kkb_client_id
        self._client_secret = cfg.kkb_client_secret
        self._member_code = cfg.kkb_member_code

    def _refresh_token(self) -> None:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/{self.TOKEN_PATH}",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "scope": "risk_report score",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                resp.raise_for_status()
                data = resp.json()
                self._token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self._token_expires_at = time.time() + expires_in - 60
        except Exception as exc:
            logger.error("KKB token refresh failed: %s", exc)
            raise

    def _ensure_token(self) -> None:
        if not self._token or time.time() >= self._token_expires_at:
            self._refresh_token()

    def get_credit_score(self, national_id: str) -> dict:
        self._ensure_token()
        payload = {
            "memberCode": self._member_code,
            "nationalId": national_id,
            "reportType": "SCORE_ONLY",
            "consentConfirmed": True,
        }
        return self._post("score/inquiry", body=payload)

    def get_risk_report(self, national_id: str, report_type: str = "standard") -> dict:
        self._ensure_token()
        kkb_report_type = {
            "standard": "STANDARD",
            "detailed": "DETAILED",
            "score_only": "SCORE_ONLY",
        }.get(report_type, "STANDARD")

        payload = {
            "memberCode": self._member_code,
            "nationalId": national_id,
            "reportType": kkb_report_type,
            "consentConfirmed": True,
            "requestId": f"REQ-{int(time.time())}-{national_id[-4:]}",
        }
        return self._post("risk-report/query", body=payload)

    def _parse_risk_report(self, raw: dict, national_id: str,
                           report_type: str) -> dict:
        score_info = raw.get("scoreInfo", {})
        credit_info = raw.get("creditInfo", {})
        payment_info = raw.get("paymentHistory", {})

        return {
            "bureau": "KKB",
            "source": "LIVE",
            "national_id": _mask(national_id),
            "credit_score": score_info.get("score", 0),
            "risk_grade": score_info.get("grade", "N/A"),
            "active_credits": {
                "total_count": credit_info.get("totalCreditCount", 0),
                "total_outstanding_try": credit_info.get("totalOutstandingAmount", 0),
                "mortgage_count": credit_info.get("mortgageCount", 0),
                "consumer_loan_count": credit_info.get("consumerLoanCount", 0),
                "credit_card_count": credit_info.get("creditCardCount", 0),
            },
            "payment_history": {
                "on_time_payments_pct": payment_info.get("onTimePaymentRate", 0),
                "max_days_past_due_24m": payment_info.get("maxDPD24M", 0),
                "defaults_last_5y": payment_info.get("defaults5Y", 0),
            },
            "inquiries_last_6m": raw.get("inquiryCount6M", 0),
            "report_date": _now(),
            "report_type": report_type,
        }


def _mock_credit_bureau(national_id: str, report_type: str = "standard") -> dict:
    seed = int(national_id[-4:]) if national_id[-4:].isdigit() else 500
    random.seed(seed)
    score = random.randint(400, 900)
    return {
        "bureau": "KKB",
        "source": "MOCK",
        "national_id": _mask(national_id),
        "credit_score": score,
        "risk_grade": "A" if score > 750 else ("B" if score > 650 else ("C" if score > 550 else "D")),
        "active_credits": {
            "total_count": random.randint(0, 8),
            "total_outstanding_try": round(random.uniform(0, 800000), 2),
            "mortgage_count": random.randint(0, 1),
            "consumer_loan_count": random.randint(0, 3),
            "credit_card_count": random.randint(0, 4),
        },
        "payment_history": {
            "on_time_payments_pct": round(random.uniform(70, 100), 1),
            "max_days_past_due_24m": random.randint(0, 90),
            "defaults_last_5y": random.randint(0, 2),
        },
        "inquiries_last_6m": random.randint(0, 5),
        "report_date": _now(),
        "report_type": report_type,
    }


_client: KKBClient | None = None


def query_credit_bureau(national_id: str, report_type: str = "standard") -> dict:
    cfg = get_config()
    if not cfg.is_kkb_configured():
        logger.debug("KKB not configured — using mock data")
        return _mock_credit_bureau(national_id, report_type)

    global _client
    if _client is None:
        _client = KKBClient()

    try:
        raw = _client.get_risk_report(national_id, report_type)
        return _client._parse_risk_report(raw, national_id, report_type)
    except Exception as exc:
        logger.warning("KKB live call failed (%s) — falling back to mock", exc)
        result = _mock_credit_bureau(national_id, report_type)
        result["fallback_reason"] = str(exc)
        return result
