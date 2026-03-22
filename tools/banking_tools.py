
import json
import random
import hashlib
from datetime import datetime, timedelta
from typing import Any

try:
    from integrations.kkb_client import query_credit_bureau as _kkb_query
    from integrations.boa_client import (
        query_core_banking as _boa_query,
        get_customer_360 as _boa_customer_360,
        get_transaction_history as _boa_transactions,
    )
    from integrations.tcmb_client import get_fx_rate as _tcmb_fx, get_market_data as _tcmb_market
    _INTEGRATIONS_AVAILABLE = True
except ImportError:
    _INTEGRATIONS_AVAILABLE = False


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _mask(value: str, visible: int = 4) -> str:
    if len(value) <= visible:
        return "*" * len(value)
    return "*" * (len(value) - visible) + value[-visible:]


TOOL_DATABASE_QUERY = {
    "name": "database_query",
    "description": (
        "Execute a read-only SQL query against the core banking database. "
        "Returns up to 500 rows. Only SELECT statements are allowed."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "SQL SELECT statement to execute"
            },
            "database": {
                "type": "string",
                "enum": ["core_banking", "risk", "compliance", "reporting", "hr"],
                "description": "Target database schema"
            },
            "limit": {
                "type": "integer",
                "description": "Max rows to return (default 100, max 500)",
                "default": 100
            }
        },
        "required": ["query", "database"]
    }
}


def execute_database_query(query: str, database: str, limit: int = 100) -> dict:
    if _INTEGRATIONS_AVAILABLE:
        return _boa_query(query, database, limit)

    query_lower = query.lower()
    rows = []
    if "customer" in query_lower:
        rows = [
            {"customer_id": f"C{10000+i}", "name": f"Test Customer {i}",
             "segment": random.choice(["Retail", "SME", "Corporate"]),
             "risk_rating": random.choice(["Low", "Medium", "High"]),
             "kyc_status": "Verified", "onboarded": "2022-03-15"}
            for i in range(min(limit, 5))
        ]
    elif "loan" in query_lower or "credit" in query_lower:
        rows = [
            {"loan_id": f"L{20000+i}", "customer_id": f"C{10000+i}",
             "outstanding": round(random.uniform(10000, 500000), 2),
             "status": random.choice(["Performing", "Watch", "NPL"]),
             "days_past_due": random.randint(0, 180),
             "product": random.choice(["Mortgage", "Personal", "SME", "Corporate"])}
            for i in range(min(limit, 5))
        ]
    elif "transaction" in query_lower:
        rows = [
            {"txn_id": f"T{30000+i}", "amount": round(random.uniform(100, 50000), 2),
             "currency": random.choice(["TRY", "USD", "EUR"]),
             "channel": random.choice(["ATM", "Internet", "Mobile", "Branch"]),
             "status": "Completed", "created_at": _now()}
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


TOOL_CUSTOMER_360 = {
    "name": "customer_360_lookup",
    "description": (
        "Retrieve a comprehensive 360-degree view of a customer including "
        "products, balances, risk profile, KYC status, and interaction history."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "string",
                "description": "Unique customer identifier"
            },
            "include_sections": {
                "type": "array",
                "items": {"type": "string",
                          "enum": ["products", "balances", "risk", "kyc",
                                   "interactions", "alerts", "relationship"]},
                "description": "Data sections to include (default: all)"
            }
        },
        "required": ["customer_id"]
    }
}


def execute_customer_360(customer_id: str, include_sections: list | None = None) -> dict:
    if _INTEGRATIONS_AVAILABLE:
        return _boa_customer_360(customer_id, include_sections)
    seed = int(hashlib.md5(customer_id.encode()).hexdigest(), 16) % 1000
    random.seed(seed)
    return {
        "customer_id": customer_id,
        "name": f"Customer {customer_id[-4:]}",
        "segment": random.choice(["Retail", "SME", "Corporate", "VIP"]),
        "since": "2019-06-01",
        "products": {
            "current_accounts": random.randint(1, 3),
            "savings_accounts": random.randint(0, 2),
            "loans": random.randint(0, 3),
            "credit_cards": random.randint(0, 2),
            "investments": random.randint(0, 1)
        },
        "balances": {
            "total_deposits_try": round(random.uniform(5000, 500000), 2),
            "total_loans_try": round(random.uniform(0, 1000000), 2),
            "net_position_try": round(random.uniform(-200000, 300000), 2)
        },
        "risk": {
            "credit_score": random.randint(500, 900),
            "risk_rating": random.choice(["Low", "Medium", "High"]),
            "aml_risk": random.choice(["Low", "Medium"]),
            "pep_flag": False,
            "sanctions_flag": False
        },
        "kyc": {
            "status": "Verified",
            "last_review": "2024-11-01",
            "next_review_due": "2025-11-01",
            "documents": ["National ID", "Proof of Address", "Tax Certificate"]
        },
        "relationship": {
            "relationship_manager": f"RM-{random.randint(100, 999)}",
            "nps_score": random.randint(6, 10),
            "last_contact": "2025-02-15"
        },
        "retrieved_at": _now()
    }


TOOL_TRANSACTION_HISTORY = {
    "name": "transaction_history",
    "description": "Retrieve transaction history for a customer or account with filtering options.",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string"},
            "account_id": {"type": "string", "description": "Optional: filter by specific account"},
            "date_from": {"type": "string", "description": "ISO date YYYY-MM-DD"},
            "date_to": {"type": "string", "description": "ISO date YYYY-MM-DD"},
            "min_amount": {"type": "number"},
            "max_amount": {"type": "number"},
            "channel": {"type": "string",
                        "enum": ["ATM", "Internet", "Mobile", "Branch", "POS", "Wire", "all"],
                        "default": "all"},
            "limit": {"type": "integer", "default": 50}
        },
        "required": ["customer_id"]
    }
}


def execute_transaction_history(customer_id: str, **kwargs) -> dict:
    if _INTEGRATIONS_AVAILABLE:
        return _boa_transactions(customer_id, **kwargs)
    limit = kwargs.get("limit", 50)
    channel = kwargs.get("channel", "all")
    channels = ["ATM", "Internet", "Mobile", "Branch", "POS", "Wire"]
    txns = []
    for i in range(min(limit, 20)):
        ch = random.choice(channels) if channel == "all" else channel
        txns.append({
            "txn_id": f"T{random.randint(1000000, 9999999)}",
            "date": (datetime.utcnow() - timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d"),
            "amount": round(random.uniform(50, 25000), 2),
            "currency": random.choice(["TRY", "TRY", "TRY", "USD", "EUR"]),
            "type": random.choice(["Debit", "Credit"]),
            "channel": ch,
            "description": f"Transaction via {ch}",
            "counterparty": f"Counterparty-{random.randint(100, 999)}",
            "status": "Completed"
        })
    return {
        "customer_id": customer_id,
        "transaction_count": len(txns),
        "transactions": txns,
        "retrieved_at": _now()
    }


TOOL_CREDIT_BUREAU = {
    "name": "credit_bureau_api",
    "description": "Query KKB (Credit Bureau) for customer credit history, score, and existing credit obligations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "national_id": {"type": "string", "description": "Turkish national ID (TC Kimlik No)"},
            "customer_name": {"type": "string"},
            "report_type": {
                "type": "string",
                "enum": ["standard", "detailed", "score_only"],
                "default": "standard"
            }
        },
        "required": ["national_id"]
    }
}


def execute_credit_bureau(national_id: str, report_type: str = "standard", **kwargs) -> dict:
    if _INTEGRATIONS_AVAILABLE:
        return _kkb_query(national_id, report_type)
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


TOOL_RISK_SCORING = {
    "name": "risk_scoring_engine",
    "description": "Run the bank's internal risk scoring model for credit, fraud, or AML risk assessment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "model_type": {
                "type": "string",
                "enum": ["credit_retail", "credit_sme", "credit_corporate",
                         "fraud_transaction", "aml_behavior", "churn"],
                "description": "Which risk model to run"
            },
            "input_features": {
                "type": "object",
                "description": "Feature dictionary for model input"
            },
            "explain": {
                "type": "boolean",
                "default": True,
                "description": "Return feature importance explanation"
            }
        },
        "required": ["model_type", "input_features"]
    }
}


def execute_risk_scoring(model_type: str, input_features: dict, explain: bool = True) -> dict:
    score = round(random.uniform(0.1, 0.95), 4)
    result = {
        "model_type": model_type,
        "model_version": "v3.2.1",
        "score": score,
        "risk_label": "High" if score > 0.7 else ("Medium" if score > 0.4 else "Low"),
        "recommendation": "DECLINE" if score > 0.75 else ("REFER" if score > 0.5 else "APPROVE"),
        "scored_at": _now()
    }
    if explain:
        result["top_drivers"] = {
            "positive": [
                {"feature": "payment_history_score", "impact": round(random.uniform(0.05, 0.2), 3)},
                {"feature": "income_stability", "impact": round(random.uniform(0.03, 0.15), 3)},
                {"feature": "relationship_tenure_years", "impact": round(random.uniform(0.02, 0.1), 3)}
            ],
            "negative": [
                {"feature": "current_utilization_ratio", "impact": -round(random.uniform(0.05, 0.2), 3)},
                {"feature": "recent_inquiries_count", "impact": -round(random.uniform(0.02, 0.1), 3)},
                {"feature": "dti_ratio", "impact": -round(random.uniform(0.03, 0.15), 3)}
            ]
        }
    return result


TOOL_PAYMENT_GATEWAY = {
    "name": "payment_gateway",
    "description": (
        "Process domestic and international payments via TCMB EFT/FAST or SWIFT. "
        "Requires dual-authorization for amounts above configured thresholds."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "payment_type": {
                "type": "string",
                "enum": ["EFT", "FAST", "HAVALE", "SWIFT", "INTERNAL"],
                "description": "Payment rail to use"
            },
            "amount": {"type": "number", "description": "Payment amount"},
            "currency": {"type": "string", "default": "TRY"},
            "debtor_iban": {"type": "string"},
            "creditor_iban": {"type": "string"},
            "creditor_name": {"type": "string"},
            "reference": {"type": "string", "description": "Payment reference/description"},
            "value_date": {"type": "string", "description": "ISO date YYYY-MM-DD"}
        },
        "required": ["payment_type", "amount", "currency", "debtor_iban", "creditor_iban"]
    }
}


def execute_payment_gateway(payment_type: str, amount: float, currency: str,
                            debtor_iban: str, creditor_iban: str, **kwargs) -> dict:
    if amount > 1_000_000:
        return {
            "success": False,
            "error": "Amount exceeds single-transaction limit. Dual authorization required.",
            "requires_approval": True,
            "approval_reference": f"APR-{random.randint(100000, 999999)}"
        }
    txn_ref = f"{payment_type}-{random.randint(10000000, 99999999)}"
    return {
        "success": True,
        "transaction_reference": txn_ref,
        "payment_type": payment_type,
        "amount": amount,
        "currency": currency,
        "debtor_iban": _mask(debtor_iban, 6),
        "creditor_iban": _mask(creditor_iban, 6),
        "status": "ACCEPTED",
        "settlement_expected": (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
        "processed_at": _now()
    }


TOOL_SWIFT = {
    "name": "swift_api",
    "description": "Send, receive, and track SWIFT messages (MT103, MT202, MT700, MT940 etc.).",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["send", "retrieve", "status", "list_pending"],
                "description": "Action to perform"
            },
            "message_type": {
                "type": "string",
                "description": "SWIFT message type (e.g. MT103, MT202, MT700)",
                "enum": ["MT103", "MT202", "MT700", "MT760", "MT940", "MT950", "MT910"]
            },
            "message_ref": {"type": "string", "description": "Message reference (for retrieve/status)"},
            "payload": {"type": "object", "description": "Message fields for send action"}
        },
        "required": ["action"]
    }
}


def execute_swift_api(action: str, message_type: str | None = None,
                      message_ref: str | None = None, payload: dict | None = None) -> dict:
    if action == "send":
        ref = f"SWIFT-{message_type}-{random.randint(100000, 999999)}"
        return {
            "success": True,
            "reference": ref,
            "message_type": message_type,
            "status": "QUEUED",
            "network_ack_expected_by": (datetime.utcnow() + timedelta(minutes=30)).isoformat() + "Z",
            "submitted_at": _now()
        }
    elif action == "status":
        return {
            "reference": message_ref,
            "status": random.choice(["DELIVERED", "PENDING", "ACKNOWLEDGED"]),
            "last_updated": _now()
        }
    elif action == "list_pending":
        return {
            "pending_count": random.randint(0, 15),
            "messages": [
                {"ref": f"SWIFT-{random.randint(100000, 999999)}", "type": "MT103",
                 "age_minutes": random.randint(1, 120)}
                for _ in range(3)
            ]
        }
    return {"success": False, "error": f"Unknown action: {action}"}


TOOL_COLLATERAL_VALUATION = {
    "name": "collateral_valuation",
    "description": "Retrieve or request valuation of collateral assets pledged against credit facilities.",
    "input_schema": {
        "type": "object",
        "properties": {
            "collateral_id": {"type": "string"},
            "collateral_type": {
                "type": "string",
                "enum": ["real_estate", "vehicle", "financial_instruments",
                         "commercial_property", "guarantee"]
            },
            "action": {
                "type": "string",
                "enum": ["get_current", "request_revaluation", "get_history"],
                "default": "get_current"
            }
        },
        "required": ["collateral_id", "collateral_type"]
    }
}


def execute_collateral_valuation(collateral_id: str, collateral_type: str,
                                 action: str = "get_current") -> dict:
    base_value = random.uniform(100000, 5000000)
    haircut = {"real_estate": 0.2, "vehicle": 0.3, "financial_instruments": 0.15,
               "commercial_property": 0.25, "guarantee": 0.0}.get(collateral_type, 0.2)
    return {
        "collateral_id": collateral_id,
        "collateral_type": collateral_type,
        "market_value_try": round(base_value, 2),
        "haircut_pct": haircut * 100,
        "eligible_value_try": round(base_value * (1 - haircut), 2),
        "last_valuation_date": "2025-01-15",
        "valuation_age_days": random.randint(30, 400),
        "eligible": random.choice([True, True, True, False]),
        "lien_registered": True,
        "lien_rank": random.randint(1, 2),
        "action": action,
        "retrieved_at": _now()
    }


TOOL_STRESS_TEST = {
    "name": "stress_test_engine",
    "description": "Execute stress test scenarios on the loan portfolio or capital position.",
    "input_schema": {
        "type": "object",
        "properties": {
            "scenario_type": {
                "type": "string",
                "enum": ["base", "adverse", "severe_adverse", "reverse_stress",
                         "gdp_shock", "fx_depreciation", "interest_rate_shock"]
            },
            "portfolio_scope": {
                "type": "string",
                "enum": ["total", "retail", "sme", "corporate", "mortgage"],
                "default": "total"
            },
            "horizon_years": {
                "type": "integer",
                "default": 3,
                "description": "Projection horizon in years"
            }
        },
        "required": ["scenario_type"]
    }
}


def execute_stress_test(scenario_type: str, portfolio_scope: str = "total",
                        horizon_years: int = 3) -> dict:
    severity = {"base": 0.05, "adverse": 0.15, "severe_adverse": 0.30,
                "gdp_shock": 0.25, "fx_depreciation": 0.20,
                "interest_rate_shock": 0.18, "reverse_stress": 0.40}.get(scenario_type, 0.10)
    cet1_impact = round(severity * random.uniform(0.8, 1.2), 2)
    return {
        "scenario_type": scenario_type,
        "portfolio_scope": portfolio_scope,
        "horizon_years": horizon_years,
        "macro_assumptions": {
            "gdp_growth_pct": round(-severity * 10 + random.uniform(-1, 1), 2),
            "unemployment_rate_pct": round(10 + severity * 15, 1),
            "fx_depreciation_pct": round(severity * 40, 1),
            "policy_rate_pct": round(30 + severity * 20, 1)
        },
        "credit_impact": {
            "pd_multiplier": round(1 + severity * 3, 2),
            "lgd_increase_pp": round(severity * 20, 1),
            "npl_ratio_end_pct": round(5 + severity * 20, 1),
            "additional_provisions_bn_try": round(severity * 10, 2)
        },
        "capital_impact": {
            "cet1_ratio_current_pct": 14.5,
            "cet1_ratio_stressed_pct": round(14.5 - cet1_impact * 100, 1),
            "capital_shortfall_bn_try": max(0, round((8 - (14.5 - cet1_impact * 100)) * 0.5, 2))
        },
        "breaches_regulatory_minimum": (14.5 - cet1_impact * 100) < 8.0,
        "run_at": _now()
    }


TOOL_PORTFOLIO_ANALYTICS = {
    "name": "portfolio_analytics",
    "description": "Calculate portfolio-level analytics including performance, risk metrics, and attribution.",
    "input_schema": {
        "type": "object",
        "properties": {
            "portfolio_id": {"type": "string", "description": "Client portfolio or internal portfolio ID"},
            "metric": {
                "type": "string",
                "enum": ["performance", "risk", "attribution", "holdings", "var", "concentration"],
                "description": "Analytics metric to calculate"
            },
            "period": {
                "type": "string",
                "enum": ["1d", "1w", "1m", "3m", "6m", "1y", "ytd", "inception"],
                "default": "1m"
            },
            "benchmark": {"type": "string", "description": "Benchmark index ID for comparison"}
        },
        "required": ["portfolio_id", "metric"]
    }
}


def execute_portfolio_analytics(portfolio_id: str, metric: str,
                                period: str = "1m", benchmark: str | None = None) -> dict:
    base = {
        "portfolio_id": portfolio_id,
        "metric": metric,
        "period": period,
        "calculated_at": _now()
    }
    if metric == "performance":
        base.update({
            "return_pct": round(random.uniform(-5, 20), 2),
            "benchmark_return_pct": round(random.uniform(-3, 15), 2),
            "alpha_pct": round(random.uniform(-2, 5), 2),
            "sharpe_ratio": round(random.uniform(0.5, 2.5), 2)
        })
    elif metric == "risk":
        base.update({
            "volatility_annualized_pct": round(random.uniform(5, 25), 2),
            "var_95_1d_pct": round(random.uniform(0.5, 3), 2),
            "max_drawdown_pct": round(random.uniform(-15, -1), 2),
            "beta": round(random.uniform(0.6, 1.4), 2)
        })
    elif metric == "holdings":
        base["top_holdings"] = [
            {"asset": f"Asset-{i}", "weight_pct": round(random.uniform(2, 15), 1),
             "return_pct": round(random.uniform(-10, 30), 1)}
            for i in range(5)
        ]
    return base


TOOL_ML_INFERENCE = {
    "name": "ml_model_inference",
    "description": "Run inference against deployed ML models in the model registry.",
    "input_schema": {
        "type": "object",
        "properties": {
            "model_name": {"type": "string", "description": "Registered model name"},
            "model_version": {"type": "string", "default": "latest"},
            "features": {"type": "object", "description": "Input feature dictionary"},
            "return_probabilities": {"type": "boolean", "default": False}
        },
        "required": ["model_name", "features"]
    }
}


def execute_ml_inference(model_name: str, features: dict,
                         model_version: str = "latest",
                         return_probabilities: bool = False) -> dict:
    prediction = random.choice([0, 1]) if "classifier" in model_name.lower() else round(random.uniform(0, 1), 4)
    result = {
        "model_name": model_name,
        "model_version": model_version,
        "prediction": prediction,
        "confidence": round(random.uniform(0.6, 0.99), 3),
        "inference_ms": random.randint(10, 150),
        "features_used": len(features),
        "inferred_at": _now()
    }
    if return_probabilities:
        result["probabilities"] = {"class_0": round(1 - prediction, 3),
                                   "class_1": round(prediction, 3)}
    return result


TOOL_MARKET_DATA = {
    "name": "market_data_feed",
    "description": "Retrieve real-time or historical market data including equity prices, bond yields, and indices.",
    "input_schema": {
        "type": "object",
        "properties": {
            "symbols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of market symbols (e.g. BIST100, USDTRY, XAUUSD)"
            },
            "data_type": {
                "type": "string",
                "enum": ["realtime", "eod", "historical"],
                "default": "realtime"
            },
            "period": {"type": "string", "description": "Historical period (e.g. 30d, 1y)"}
        },
        "required": ["symbols"]
    }
}


def execute_market_data(symbols: list, data_type: str = "realtime", period: str | None = None) -> dict:
    if _INTEGRATIONS_AVAILABLE:
        return _tcmb_market(symbols, data_type, period)
    base_prices = {"BIST100": 9500, "USDTRY": 38.5, "EURTRY": 41.2,
                   "XAUUSD": 3100, "BRENTOIL": 72.5, "VIOP30": 9480}
    data = {}
    for sym in symbols:
        base = base_prices.get(sym, 100)
        change_pct = round(random.uniform(-3, 3), 2)
        data[sym] = {
            "price": round(base * (1 + change_pct / 100), 4),
            "change_pct": change_pct,
            "source": "MOCK",
            "volume": random.randint(100000, 50000000),
            "timestamp": _now(),
        }
    return {"data_type": data_type, "quotes": data, "source": "MOCK"}


TOOL_FX_RATE = {
    "name": "fx_rate_api",
    "description": "Retrieve FX spot, forward rates and execute FX conversions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "base_currency": {"type": "string", "description": "e.g. USD"},
            "quote_currency": {"type": "string", "description": "e.g. TRY"},
            "amount": {"type": "number", "description": "Amount to convert (optional)"},
            "tenor": {
                "type": "string",
                "enum": ["spot", "1w", "1m", "3m", "6m", "1y"],
                "default": "spot"
            }
        },
        "required": ["base_currency", "quote_currency"]
    }
}


def execute_fx_rate(base_currency: str, quote_currency: str,
                    amount: float | None = None, tenor: str = "spot") -> dict:
    if _INTEGRATIONS_AVAILABLE:
        return _tcmb_fx(base_currency, quote_currency, amount, tenor)
    rates = {("USD", "TRY"): 38.50, ("EUR", "TRY"): 41.20,
             ("GBP", "TRY"): 48.30, ("USD", "EUR"): 0.937}
    key = (base_currency.upper(), quote_currency.upper())
    rate = rates.get(key, round(random.uniform(0.5, 50), 4))
    spread = round(rate * 0.003, 4)
    result: dict = {
        "base": base_currency,
        "quote": quote_currency,
        "tenor": tenor,
        "source": "MOCK",
        "mid_rate": rate,
        "bid": round(rate - spread, 4),
        "ask": round(rate + spread, 4),
        "timestamp": _now(),
    }
    if amount:
        result["converted_amount"] = round(amount * rate, 2)
        result["base_amount"] = amount
    return result
