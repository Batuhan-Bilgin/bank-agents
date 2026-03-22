
import random
import hashlib
from datetime import datetime

_NOW = lambda: datetime.utcnow().isoformat() + "Z"

try:
    from integrations.masak_client import (
        screen_aml as _masak_screen,
        check_sanctions as _masak_sanctions,
        submit_str_report as _masak_str,
    )
    _MASAK_AVAILABLE = True
except ImportError:
    _MASAK_AVAILABLE = False


TOOL_FRAUD_DETECTION = {
    "name": "fraud_detection_api",
    "description": "Query the real-time fraud detection engine for transaction and behavioral risk scores.",
    "input_schema": {
        "type": "object",
        "properties": {
            "event_type": {
                "type": "string",
                "enum": ["transaction", "login", "account_change", "new_beneficiary"]
            },
            "transaction_id": {"type": "string"},
            "customer_id": {"type": "string"},
            "amount": {"type": "number"},
            "channel": {"type": "string"},
            "device_fingerprint": {"type": "string"},
            "ip_address": {"type": "string"},
            "merchant_category": {"type": "string"},
            "geolocation": {
                "type": "object",
                "properties": {
                    "country": {"type": "string"},
                    "city": {"type": "string"}
                }
            }
        },
        "required": ["event_type", "customer_id"]
    }
}


def execute_fraud_detection(event_type: str, customer_id: str, **kwargs) -> dict:
    score = round(random.uniform(0.01, 0.99), 4)
    action = "BLOCK" if score > 0.85 else ("CHALLENGE" if score > 0.60 else "ALLOW")
    rules_fired = []
    if score > 0.5:
        rules_fired = random.sample([
            "HIGH_RISK_COUNTRY", "UNUSUAL_AMOUNT", "NEW_DEVICE",
            "VELOCITY_BREACH", "IMPOSSIBLE_TRAVEL", "MULE_ACCOUNT_INDICATOR"
        ], k=random.randint(1, 3))
    return {
        "event_type": event_type,
        "customer_id": customer_id,
        "fraud_score": score,
        "risk_level": "Critical" if score > 0.85 else ("High" if score > 0.65 else "Low"),
        "recommended_action": action,
        "rules_fired": rules_fired,
        "model_version": "FraudNet-v5.1",
        "response_ms": random.randint(8, 45),
        "evaluated_at": _NOW()
    }


TOOL_AML_SCREENING = {
    "name": "aml_screening",
    "description": "Screen transactions and customer behaviors for AML typologies and generate alerts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "screening_type": {
                "type": "string",
                "enum": ["transaction_monitoring", "customer_behavior",
                         "wire_transfer", "cash_transaction"]
            },
            "customer_id": {"type": "string"},
            "transaction_data": {
                "type": "object",
                "description": "Transaction details for screening"
            },
            "lookback_days": {
                "type": "integer",
                "default": 90,
                "description": "Days of history to analyze"
            }
        },
        "required": ["screening_type", "customer_id"]
    }
}


def execute_aml_screening(screening_type: str, customer_id: str,
                          transaction_data: dict | None = None,
                          lookback_days: int = 90) -> dict:
    if _MASAK_AVAILABLE:
        return _masak_screen(screening_type, customer_id, transaction_data, lookback_days)
    typologies_detected = []
    alert_score = round(random.uniform(0, 1), 3)
    if alert_score > 0.6:
        typologies_detected = random.sample([
            "STRUCTURING", "LAYERING_MULTIPLE_ACCOUNTS",
            "RAPID_FUND_MOVEMENT", "HIGH_RISK_JURISDICTION",
            "ROUND_AMOUNT_PATTERN", "CASH_INTENSIVE_BUSINESS"
        ], k=random.randint(1, 2))
    return {
        "screening_type": screening_type,
        "customer_id": customer_id,
        "lookback_days": lookback_days,
        "source": "MOCK",
        "alert_score": alert_score,
        "alert_generated": alert_score > 0.6,
        "typologies_detected": typologies_detected,
        "str_candidate": alert_score > 0.8,
        "case_id": f"AML-{random.randint(100000, 999999)}" if alert_score > 0.6 else None,
        "screened_at": _NOW(),
    }


TOOL_SANCTIONS = {
    "name": "sanctions_check",
    "description": "Screen names, entities, and accounts against OFAC, UN, EU, HMT, and Turkish sanctions lists.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of individual or entity to screen"},
            "entity_type": {
                "type": "string",
                "enum": ["individual", "entity", "vessel", "aircraft"],
                "default": "individual"
            },
            "date_of_birth": {"type": "string"},
            "nationality": {"type": "string"},
            "account_number": {"type": "string"},
            "lists_to_check": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["OFAC_SDN", "UN_CONSOLIDATED", "EU_SANCTIONS",
                             "HMT_UK", "TR_OFFICIAL", "FATF_HIGH_RISK"]
                },
                "default": ["OFAC_SDN", "UN_CONSOLIDATED", "EU_SANCTIONS", "TR_OFFICIAL"]
            }
        },
        "required": ["name"]
    }
}


def execute_sanctions_check(name: str, entity_type: str = "individual",
                            lists_to_check: list | None = None, **kwargs) -> dict:
    if _MASAK_AVAILABLE:
        return _masak_sanctions(name, entity_type, lists_to_check, **kwargs)
    lists = lists_to_check or ["OFAC_SDN", "UN_CONSOLIDATED", "EU_SANCTIONS", "TR_OFFICIAL"]
    is_hit = random.random() < 0.02
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
        "screened_at": _NOW(),
    }


TOOL_KYC = {
    "name": "kyc_verification",
    "description": "Verify customer identity and perform KYC due diligence checks.",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string"},
            "verification_type": {
                "type": "string",
                "enum": ["initial_onboarding", "periodic_review", "enhanced_due_diligence",
                         "id_document_check", "liveness_check"]
            },
            "document_type": {
                "type": "string",
                "enum": ["national_id", "passport", "driving_license", "residence_permit"]
            },
            "document_number": {"type": "string"}
        },
        "required": ["customer_id", "verification_type"]
    }
}


def execute_kyc_verification(customer_id: str, verification_type: str,
                             document_type: str | None = None,
                             document_number: str | None = None) -> dict:
    passed = random.random() > 0.05
    return {
        "customer_id": customer_id,
        "verification_type": verification_type,
        "status": "PASSED" if passed else "FAILED",
        "checks": {
            "identity_confirmed": passed,
            "liveness_confirmed": passed if verification_type == "liveness_check" else None,
            "document_authentic": passed,
            "nvi_match": passed,
            "address_verified": random.random() > 0.1,
            "pep_check": "Clear",
            "sanctions_check": "Clear"
        },
        "risk_rating_assigned": random.choice(["Low", "Medium"]) if passed else "High",
        "verification_id": f"KYC-{random.randint(1000000, 9999999)}",
        "verified_at": _NOW(),
        "next_review_date": "2026-03-20"
    }


TOOL_DOCUMENT_OCR = {
    "name": "document_ocr",
    "description": "Extract structured data from banking documents using OCR and NLP.",
    "input_schema": {
        "type": "object",
        "properties": {
            "document_id": {"type": "string", "description": "Reference ID of uploaded document"},
            "document_type": {
                "type": "string",
                "enum": ["national_id", "financial_statement", "tax_return",
                         "salary_slip", "bank_statement", "invoice", "contract",
                         "collateral_deed", "corporate_registry"]
            },
            "language": {"type": "string", "enum": ["tr", "en"], "default": "tr"},
            "extract_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific fields to extract"
            }
        },
        "required": ["document_id", "document_type"]
    }
}


def execute_document_ocr(document_id: str, document_type: str,
                         language: str = "tr", extract_fields: list | None = None) -> dict:
    templates = {
        "national_id": {
            "tc_no": f"{random.randint(10000000000, 99999999999)}",
            "name": "Test Person",
            "birth_date": "1985-03-15",
            "expiry": "2030-03-14"
        },
        "salary_slip": {
            "gross_salary": round(random.uniform(15000, 80000), 2),
            "net_salary": round(random.uniform(10000, 60000), 2),
            "employer": "Sample Company A.Ş.",
            "period": "2025-02"
        },
        "financial_statement": {
            "total_assets": round(random.uniform(1e6, 1e9), 2),
            "total_liabilities": round(random.uniform(5e5, 8e8), 2),
            "net_revenue": round(random.uniform(1e5, 5e8), 2),
            "ebitda": round(random.uniform(5e4, 1e8), 2),
            "period": "2024-12-31"
        }
    }
    extracted = templates.get(document_type, {"raw_text_extracted": True})
    return {
        "document_id": document_id,
        "document_type": document_type,
        "confidence_score": round(random.uniform(0.82, 0.99), 3),
        "extraction_status": "SUCCESS",
        "extracted_data": extracted,
        "tamper_detected": False,
        "processed_at": _NOW()
    }


TOOL_DATA_QUALITY = {
    "name": "data_quality_checker",
    "description": "Run data quality checks on datasets or data domains and return DQ scores.",
    "input_schema": {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "enum": ["customer", "account", "transaction", "loan",
                         "collateral", "counterparty", "market_data"]
            },
            "check_type": {
                "type": "string",
                "enum": ["completeness", "accuracy", "consistency",
                         "timeliness", "validity", "all"],
                "default": "all"
            },
            "sample_size": {"type": "integer", "default": 1000}
        },
        "required": ["domain"]
    }
}


def execute_data_quality(domain: str, check_type: str = "all", sample_size: int = 1000) -> dict:
    dimensions = ["completeness", "accuracy", "consistency", "timeliness", "validity"]
    scores = {d: round(random.uniform(85, 99.5), 1) for d in dimensions}
    overall = round(sum(scores.values()) / len(scores), 1)
    issues = []
    for dim, score in scores.items():
        if score < 92:
            issues.append({
                "dimension": dim,
                "score": score,
                "affected_records": random.randint(10, 500),
                "severity": "Warning" if score > 88 else "Critical"
            })
    return {
        "domain": domain,
        "sample_size": sample_size,
        "overall_dq_score": overall,
        "dimension_scores": scores,
        "issues_found": len(issues),
        "issues": issues,
        "check_passed": overall >= 90,
        "checked_at": _NOW()
    }


TOOL_DATA_LINEAGE = {
    "name": "data_lineage_api",
    "description": "Query data lineage information to trace data elements from source to consumption.",
    "input_schema": {
        "type": "object",
        "properties": {
            "data_element": {"type": "string", "description": "Name of the data field or table"},
            "direction": {
                "type": "string",
                "enum": ["upstream", "downstream", "both"],
                "default": "both"
            },
            "depth": {
                "type": "integer",
                "default": 3,
                "description": "Number of hops to trace"
            }
        },
        "required": ["data_element"]
    }
}


def execute_data_lineage(data_element: str, direction: str = "both", depth: int = 3) -> dict:
    upstream = [
        {"system": "Core Banking (BOA)", "table": f"BOA_{data_element.upper()}", "hop": 1},
        {"system": "ETL Layer", "table": f"STG_{data_element.upper()}", "hop": 2}
    ]
    downstream = [
        {"system": "Data Warehouse", "table": f"DWH_{data_element.upper()}", "hop": 1},
        {"system": "Regulatory Reporting", "report": f"COREP_{data_element.upper()}", "hop": 2},
        {"system": "MIS Dashboard", "view": f"DASH_{data_element.upper()}", "hop": 3}
    ]
    return {
        "data_element": data_element,
        "direction": direction,
        "upstream_sources": upstream if direction in ["upstream", "both"] else [],
        "downstream_consumers": downstream if direction in ["downstream", "both"] else [],
        "total_impacted_reports": random.randint(3, 15),
        "last_updated": _NOW()
    }


TOOL_REG_REPORTING = {
    "name": "regulatory_reporting_api",
    "description": "Submit or retrieve regulatory reports (BDDK, TCMB, MASAK, SPK).",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["submit", "retrieve", "validate", "list_pending", "get_deadlines"]
            },
            "report_type": {
                "type": "string",
                "enum": ["COREP", "FINREP", "LCR", "NSFR", "LARGE_EXPOSURE",
                         "STR", "CTR", "FX_POSITION", "CAPITAL_ADEQUACY"]
            },
            "period": {"type": "string", "description": "Reporting period (e.g. 2025-02)"},
            "report_data": {"type": "object", "description": "Report payload for submission"}
        },
        "required": ["action"]
    }
}


def execute_regulatory_reporting(action: str, report_type: str | None = None,
                                 period: str | None = None, report_data: dict | None = None) -> dict:
    if action == "submit":
        return {
            "success": True,
            "submission_id": f"REG-{random.randint(1000000, 9999999)}",
            "report_type": report_type,
            "period": period,
            "status": "SUBMITTED",
            "regulator_acknowledgment_expected": "2025-03-21T08:00:00Z",
            "submitted_at": _NOW()
        }
    elif action == "get_deadlines":
        return {
            "upcoming_deadlines": [
                {"report": "COREP", "deadline": "2025-03-31", "days_remaining": 11},
                {"report": "LCR", "deadline": "2025-03-25", "days_remaining": 5},
                {"report": "STR", "deadline": "2025-03-28", "days_remaining": 8}
            ]
        }
    elif action == "validate":
        errors = random.randint(0, 3)
        return {
            "report_type": report_type,
            "validation_passed": errors == 0,
            "error_count": errors,
            "errors": [{"field": f"field_{i}", "rule": "REQUIRED", "message": "Missing value"}
                       for i in range(errors)],
            "validated_at": _NOW()
        }
    return {"action": action, "status": "PROCESSED", "timestamp": _NOW()}
