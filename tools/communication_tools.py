"""
Communication & operational tools — email, SMS, alerts, audit logging,
workflow triggers, approvals, CRM, HR, calendar.
"""

import random
import json
from datetime import datetime

_NOW = lambda: datetime.utcnow().isoformat() + "Z"

# ---------------------------------------------------------------------------
# Tool: email_sender
# ---------------------------------------------------------------------------

TOOL_EMAIL = {
    "name": "email_sender",
    "description": "Send email notifications to customers or internal staff.",
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {"type": "array", "items": {"type": "string"}, "description": "Recipient email(s)"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "template_id": {"type": "string", "description": "Optional: use a predefined template"},
            "template_vars": {"type": "object"},
            "priority": {"type": "string", "enum": ["normal", "high", "urgent"], "default": "normal"},
            "cc": {"type": "array", "items": {"type": "string"}},
            "attachments": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["to", "subject", "body"]
    }
}


def execute_email_sender(to: list, subject: str, body: str, **kwargs) -> dict:
    return {
        "success": True,
        "message_id": f"MSG-{random.randint(10000000, 99999999)}",
        "recipients": len(to),
        "subject": subject,
        "priority": kwargs.get("priority", "normal"),
        "status": "QUEUED",
        "estimated_delivery_seconds": random.randint(5, 30),
        "sent_at": _NOW()
    }


# ---------------------------------------------------------------------------
# Tool: sms_sender
# ---------------------------------------------------------------------------

TOOL_SMS = {
    "name": "sms_sender",
    "description": "Send SMS notifications to customers via approved channels.",
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient phone number (E.164 format)"},
            "message": {"type": "string", "description": "SMS text (max 160 chars per segment)"},
            "sender_id": {"type": "string", "description": "Approved sender ID", "default": "BankAI"},
            "customer_id": {"type": "string"},
            "sms_type": {
                "type": "string",
                "enum": ["alert", "otp", "marketing", "notification"],
                "default": "notification"
            }
        },
        "required": ["to", "message"]
    }
}


def execute_sms_sender(to: str, message: str, **kwargs) -> dict:
    return {
        "success": True,
        "sms_id": f"SMS-{random.randint(1000000, 9999999)}",
        "to": to[-4:].rjust(len(to), "*"),
        "message_length": len(message),
        "segments": max(1, len(message) // 160 + 1),
        "sms_type": kwargs.get("sms_type", "notification"),
        "status": "SENT",
        "sent_at": _NOW()
    }


# ---------------------------------------------------------------------------
# Tool: alert_manager
# ---------------------------------------------------------------------------

TOOL_ALERT = {
    "name": "alert_manager",
    "description": "Create, escalate, or resolve operational and risk alerts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "escalate", "resolve", "list", "get"],
                "description": "Alert action"
            },
            "alert_type": {
                "type": "string",
                "enum": ["fraud", "aml", "credit_risk", "liquidity", "cyber",
                         "operational", "compliance", "market_risk", "data_quality"]
            },
            "severity": {
                "type": "string",
                "enum": ["info", "warning", "high", "critical"],
                "default": "warning"
            },
            "title": {"type": "string"},
            "description": {"type": "string"},
            "entity_id": {"type": "string", "description": "Customer/account/transaction ID"},
            "alert_id": {"type": "string", "description": "Existing alert ID (for get/escalate/resolve)"},
            "assignee": {"type": "string", "description": "Team or user to assign the alert"}
        },
        "required": ["action"]
    }
}


def execute_alert_manager(action: str, **kwargs) -> dict:
    if action == "create":
        alert_id = f"ALT-{random.randint(100000, 999999)}"
        return {
            "success": True,
            "alert_id": alert_id,
            "severity": kwargs.get("severity", "warning"),
            "alert_type": kwargs.get("alert_type", "operational"),
            "status": "OPEN",
            "sla_deadline": _NOW(),
            "created_at": _NOW()
        }
    elif action == "list":
        return {
            "open_alerts": random.randint(5, 50),
            "by_severity": {
                "critical": random.randint(0, 5),
                "high": random.randint(2, 15),
                "warning": random.randint(3, 20),
                "info": random.randint(0, 10)
            }
        }
    elif action in ["resolve", "escalate"]:
        return {
            "success": True,
            "alert_id": kwargs.get("alert_id"),
            "action": action,
            "updated_at": _NOW()
        }
    return {"action": action, "status": "PROCESSED"}


# ---------------------------------------------------------------------------
# Tool: audit_logger
# ---------------------------------------------------------------------------

TOOL_AUDIT = {
    "name": "audit_logger",
    "description": "Write an immutable audit log entry for compliance and forensic purposes.",
    "input_schema": {
        "type": "object",
        "properties": {
            "event_type": {"type": "string", "description": "Category of the event"},
            "actor_id": {"type": "string", "description": "Agent or user performing the action"},
            "action": {"type": "string", "description": "Action performed"},
            "entity_type": {"type": "string", "description": "Type of entity acted upon"},
            "entity_id": {"type": "string"},
            "details": {"type": "object", "description": "Additional context"},
            "outcome": {"type": "string", "description": "Result of the action (e.g. success, failure, approved, declined, pending, escalated)"},
            "risk_level": {"type": "string", "description": "Risk level (e.g. low, medium, high, critical)"}
        },
        "required": ["event_type", "actor_id", "action", "outcome"]
    }
}


def execute_audit_logger(event_type: str, actor_id: str, action: str,
                         outcome: str, **kwargs) -> dict:
    log_id = f"AUD-{random.randint(10000000, 99999999)}"
    return {
        "success": True,
        "log_id": log_id,
        "event_type": event_type,
        "actor_id": actor_id,
        "action": action,
        "outcome": outcome,
        "tamper_hash": f"{log_id}-{hash(action) % 0xFFFF:04x}",
        "retention_years": 8,
        "logged_at": _NOW()
    }


# ---------------------------------------------------------------------------
# Tool: workflow_trigger
# ---------------------------------------------------------------------------

TOOL_WORKFLOW = {
    "name": "workflow_trigger",
    "description": "Trigger a business workflow or process in the workflow management system.",
    "input_schema": {
        "type": "object",
        "properties": {
            "workflow_name": {
                "type": "string",
                "enum": ["credit_application_review", "kyc_remediation",
                         "account_closure", "limit_change", "complaint_resolution",
                         "onboarding", "loan_disbursement", "card_replacement",
                         "fraud_investigation", "aml_case_open"]
            },
            "entity_id": {"type": "string", "description": "Customer/case/application ID"},
            "priority": {"type": "string", "enum": ["normal", "high", "urgent"], "default": "normal"},
            "assigned_to": {"type": "string"},
            "payload": {"type": "object", "description": "Workflow-specific input data"},
            "due_date": {"type": "string", "description": "Required completion date (ISO)"}
        },
        "required": ["workflow_name", "entity_id"]
    }
}


def execute_workflow_trigger(workflow_name: str, entity_id: str, **kwargs) -> dict:
    wf_id = f"WF-{random.randint(100000, 999999)}"
    return {
        "success": True,
        "workflow_id": wf_id,
        "workflow_name": workflow_name,
        "entity_id": entity_id,
        "status": "INITIATED",
        "priority": kwargs.get("priority", "normal"),
        "assigned_to": kwargs.get("assigned_to", "Auto-assigned"),
        "sla_hours": random.choice([2, 4, 8, 24, 48]),
        "triggered_at": _NOW()
    }


# ---------------------------------------------------------------------------
# Tool: approval_request
# ---------------------------------------------------------------------------

TOOL_APPROVAL = {
    "name": "approval_request",
    "description": "Submit an action for human approval before execution.",
    "input_schema": {
        "type": "object",
        "properties": {
            "request_type": {
                "type": "string",
                "enum": ["credit_approval", "limit_override", "exception_approval",
                         "transaction_release", "account_action", "policy_exception"]
            },
            "requested_by": {"type": "string"},
            "approver_role": {"type": "string", "description": "Role required to approve"},
            "subject": {"type": "string"},
            "details": {"type": "object"},
            "amount": {"type": "number", "description": "Financial amount if applicable"},
            "urgency": {"type": "string", "enum": ["routine", "urgent", "emergency"], "default": "routine"}
        },
        "required": ["request_type", "requested_by", "subject"]
    }
}


def execute_approval_request(request_type: str, requested_by: str, subject: str, **kwargs) -> dict:
    req_id = f"APR-{random.randint(100000, 999999)}"
    return {
        "success": True,
        "approval_request_id": req_id,
        "request_type": request_type,
        "requested_by": requested_by,
        "subject": subject,
        "status": "PENDING_APPROVAL",
        "approver_notified": True,
        "urgency": kwargs.get("urgency", "routine"),
        "sla_hours": 2 if kwargs.get("urgency") == "emergency" else (8 if kwargs.get("urgency") == "urgent" else 24),
        "submitted_at": _NOW()
    }


# ---------------------------------------------------------------------------
# Tool: report_generator
# ---------------------------------------------------------------------------

TOOL_REPORT = {
    "name": "report_generator",
    "description": "Generate structured reports in PDF, Excel, or JSON format.",
    "input_schema": {
        "type": "object",
        "properties": {
            "report_name": {"type": "string"},
            "report_type": {
                "type": "string",
                "enum": ["credit_memo", "portfolio_summary", "aml_case",
                         "customer_profile", "risk_dashboard", "regulatory_pack",
                         "npl_vintage", "stress_test_result", "audit_report"]
            },
            "format": {
                "type": "string",
                "enum": ["pdf", "excel", "json", "html"],
                "default": "pdf"
            },
            "data": {"type": "object", "description": "Report data payload"},
            "recipient": {"type": "string", "description": "Email or system to deliver report to"}
        },
        "required": ["report_name", "report_type"]
    }
}


def execute_report_generator(report_name: str, report_type: str,
                             format: str = "pdf", **kwargs) -> dict:
    report_id = f"RPT-{random.randint(100000, 999999)}"
    return {
        "success": True,
        "report_id": report_id,
        "report_name": report_name,
        "report_type": report_type,
        "format": format,
        "file_size_kb": random.randint(50, 2000),
        "storage_url": f"s3://bank-reports/{report_id}.{format}",
        "generated_at": _NOW(),
        "expires_at": "2025-06-20T00:00:00Z"
    }


# ---------------------------------------------------------------------------
# Tool: dashboard_writer
# ---------------------------------------------------------------------------

TOOL_DASHBOARD = {
    "name": "dashboard_writer",
    "description": "Write or update KPI metrics to management dashboards.",
    "input_schema": {
        "type": "object",
        "properties": {
            "dashboard_id": {"type": "string"},
            "dashboard_name": {"type": "string"},
            "metrics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "value": {},
                        "unit": {"type": "string"},
                        "trend": {"type": "string", "enum": ["up", "down", "flat"]},
                        "rag_status": {"type": "string", "enum": ["green", "amber", "red"]}
                    },
                    "required": ["name", "value"]
                }
            }
        },
        "required": ["dashboard_id", "metrics"]
    }
}


def execute_dashboard_writer(dashboard_id: str, metrics: list, **kwargs) -> dict:
    return {
        "success": True,
        "dashboard_id": dashboard_id,
        "metrics_updated": len(metrics),
        "status": "PUBLISHED",
        "viewers_notified": random.randint(3, 25),
        "updated_at": _NOW()
    }


# ---------------------------------------------------------------------------
# Tool: sentiment_analyzer
# ---------------------------------------------------------------------------

TOOL_SENTIMENT = {
    "name": "sentiment_analyzer",
    "description": "Analyze sentiment and extract themes from customer feedback, calls, or text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to analyze"},
            "source": {
                "type": "string",
                "enum": ["call_transcript", "chat_log", "app_review",
                         "survey", "complaint", "email"],
                "default": "chat_log"
            },
            "language": {"type": "string", "enum": ["tr", "en"], "default": "tr"},
            "extract_themes": {"type": "boolean", "default": True}
        },
        "required": ["text"]
    }
}


def execute_sentiment_analyzer(text: str, source: str = "chat_log",
                               language: str = "tr", extract_themes: bool = True) -> dict:
    sentiment = random.choice(["positive", "neutral", "negative"])
    score = {"positive": round(random.uniform(0.6, 1.0), 3),
             "neutral": round(random.uniform(0.4, 0.6), 3),
             "negative": round(random.uniform(0.0, 0.4), 3)}[sentiment]
    result = {
        "sentiment": sentiment,
        "confidence": round(random.uniform(0.75, 0.98), 3),
        "score": score,
        "source": source,
        "language": language,
        "word_count": len(text.split())
    }
    if extract_themes:
        themes = random.sample(["wait_time", "product_feature", "pricing", "staff",
                                "digital_experience", "resolution_speed"], k=random.randint(1, 3))
        result["themes"] = themes
    return result


# ---------------------------------------------------------------------------
# Tool: crm_api
# ---------------------------------------------------------------------------

TOOL_CRM = {
    "name": "crm_api",
    "description": "Read or write customer relationship management data including interactions and opportunities.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get_customer", "log_interaction", "update_opportunity",
                         "add_task", "get_opportunities", "update_segment"]
            },
            "customer_id": {"type": "string"},
            "interaction_type": {
                "type": "string",
                "enum": ["call", "email", "visit", "chat", "complaint", "application"]
            },
            "notes": {"type": "string"},
            "opportunity": {"type": "object"},
            "task": {"type": "object"}
        },
        "required": ["action", "customer_id"]
    }
}


def execute_crm_api(action: str, customer_id: str, **kwargs) -> dict:
    if action == "get_customer":
        return {
            "customer_id": customer_id,
            "crm_status": "Active",
            "last_interaction": "2025-03-10",
            "open_opportunities": random.randint(0, 3),
            "open_tasks": random.randint(0, 5),
            "nps": random.randint(6, 10),
            "lifetime_value_try": round(random.uniform(10000, 500000), 2)
        }
    elif action == "log_interaction":
        return {
            "success": True,
            "interaction_id": f"INT-{random.randint(100000, 999999)}",
            "customer_id": customer_id,
            "type": kwargs.get("interaction_type", "call"),
            "logged_at": _NOW()
        }
    return {"success": True, "action": action, "customer_id": customer_id, "updated_at": _NOW()}


# ---------------------------------------------------------------------------
# Tool: product_catalog
# ---------------------------------------------------------------------------

TOOL_PRODUCTS = {
    "name": "product_catalog",
    "description": "Query the bank's product catalog for eligibility, rates, and product details.",
    "input_schema": {
        "type": "object",
        "properties": {
            "product_type": {
                "type": "string",
                "enum": ["mortgage", "personal_loan", "sme_loan", "credit_card",
                         "time_deposit", "demand_deposit", "mutual_fund",
                         "fx_account", "gold_account", "insurance"]
            },
            "customer_segment": {
                "type": "string",
                "enum": ["retail", "sme", "corporate", "vip", "all"],
                "default": "all"
            },
            "action": {
                "type": "string",
                "enum": ["list", "get_rates", "check_eligibility"],
                "default": "list"
            },
            "customer_id": {"type": "string", "description": "Required for eligibility check"}
        },
        "required": ["product_type"]
    }
}


def execute_product_catalog(product_type: str, customer_segment: str = "all",
                            action: str = "list", customer_id: str | None = None) -> dict:
    rates = {
        "mortgage": {"min_rate": 3.99, "max_rate": 4.99, "max_tenor_months": 240},
        "personal_loan": {"min_rate": 4.50, "max_rate": 6.50, "max_tenor_months": 60},
        "time_deposit": {"min_rate": 45.0, "max_rate": 55.0, "min_amount_try": 1000},
        "credit_card": {"annual_fee_try": random.choice([0, 499, 999]),
                        "cashback_pct": random.choice([0.5, 1.0, 1.5])}
    }
    product_rates = rates.get(product_type, {"info": "Contact relationship manager for rates"})
    return {
        "product_type": product_type,
        "customer_segment": customer_segment,
        "action": action,
        "rates": product_rates,
        "eligible": random.random() > 0.15 if action == "check_eligibility" else None,
        "min_credit_score": 600,
        "retrieved_at": _NOW()
    }


# ---------------------------------------------------------------------------
# Tool: hr_system_api
# ---------------------------------------------------------------------------

TOOL_HR = {
    "name": "hr_system_api",
    "description": "Access HR data for workforce analytics, training records, and performance.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get_employee", "get_training_status", "get_performance",
                         "get_headcount", "log_training_completion"]
            },
            "employee_id": {"type": "string"},
            "department": {"type": "string"},
            "training_id": {"type": "string"}
        },
        "required": ["action"]
    }
}


def execute_hr_system(action: str, employee_id: str | None = None, **kwargs) -> dict:
    if action == "get_employee":
        return {
            "employee_id": employee_id,
            "department": random.choice(["Credit Risk", "Compliance", "Operations", "IT"]),
            "grade": random.choice(["Analyst", "Senior Analyst", "Manager", "Director"]),
            "tenure_years": random.randint(1, 15),
            "performance_rating": random.choice(["Exceeds", "Meets", "Below"])
        }
    elif action == "get_headcount":
        dept = kwargs.get("department", "All")
        return {
            "department": dept,
            "headcount": random.randint(10, 200),
            "open_positions": random.randint(0, 10),
            "attrition_rate_pct": round(random.uniform(5, 15), 1)
        }
    return {"action": action, "status": "PROCESSED", "timestamp": _NOW()}


# ---------------------------------------------------------------------------
# Tool: calendar_api
# ---------------------------------------------------------------------------

TOOL_CALENDAR = {
    "name": "calendar_api",
    "description": "Schedule meetings, check availability, and manage calendar events.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["schedule", "check_availability", "cancel", "list"]
            },
            "participant_ids": {
                "type": "array",
                "items": {"type": "string"}
            },
            "subject": {"type": "string"},
            "proposed_time": {"type": "string", "description": "ISO datetime"},
            "duration_minutes": {"type": "integer", "default": 30},
            "event_id": {"type": "string"}
        },
        "required": ["action"]
    }
}


def execute_calendar_api(action: str, **kwargs) -> dict:
    if action == "schedule":
        return {
            "success": True,
            "event_id": f"EVT-{random.randint(100000, 999999)}",
            "subject": kwargs.get("subject", "Meeting"),
            "status": "CONFIRMED",
            "invitations_sent": len(kwargs.get("participant_ids", [])),
            "scheduled_at": _NOW()
        }
    elif action == "check_availability":
        return {
            "available_slots": [
                {"start": "2025-03-21T10:00:00Z", "end": "2025-03-21T10:30:00Z"},
                {"start": "2025-03-21T14:00:00Z", "end": "2025-03-21T14:30:00Z"},
                {"start": "2025-03-22T09:00:00Z", "end": "2025-03-22T09:30:00Z"}
            ]
        }
    return {"action": action, "status": "PROCESSED"}
