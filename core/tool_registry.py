
from tools.banking_tools import (
    TOOL_DATABASE_QUERY,   execute_database_query,
    TOOL_CUSTOMER_360,     execute_customer_360,
    TOOL_TRANSACTION_HISTORY, execute_transaction_history,
    TOOL_CREDIT_BUREAU,    execute_credit_bureau,
    TOOL_RISK_SCORING,     execute_risk_scoring,
    TOOL_PAYMENT_GATEWAY,  execute_payment_gateway,
    TOOL_SWIFT,            execute_swift_api,
    TOOL_COLLATERAL_VALUATION, execute_collateral_valuation,
    TOOL_STRESS_TEST,      execute_stress_test,
    TOOL_PORTFOLIO_ANALYTICS, execute_portfolio_analytics,
    TOOL_ML_INFERENCE,     execute_ml_inference,
    TOOL_MARKET_DATA,      execute_market_data,
    TOOL_FX_RATE,          execute_fx_rate,
)

from tools.compliance_tools import (
    TOOL_FRAUD_DETECTION,  execute_fraud_detection,
    TOOL_AML_SCREENING,    execute_aml_screening,
    TOOL_SANCTIONS,        execute_sanctions_check,
    TOOL_KYC,              execute_kyc_verification,
    TOOL_DOCUMENT_OCR,     execute_document_ocr,
    TOOL_DATA_QUALITY,     execute_data_quality,
    TOOL_DATA_LINEAGE,     execute_data_lineage,
    TOOL_REG_REPORTING,    execute_regulatory_reporting,
)

from tools.communication_tools import (
    TOOL_EMAIL,            execute_email_sender,
    TOOL_SMS,              execute_sms_sender,
    TOOL_ALERT,            execute_alert_manager,
    TOOL_AUDIT,            execute_audit_logger,
    TOOL_WORKFLOW,         execute_workflow_trigger,
    TOOL_APPROVAL,         execute_approval_request,
    TOOL_REPORT,           execute_report_generator,
    TOOL_DASHBOARD,        execute_dashboard_writer,
    TOOL_SENTIMENT,        execute_sentiment_analyzer,
    TOOL_CRM,              execute_crm_api,
    TOOL_PRODUCTS,         execute_product_catalog,
    TOOL_HR,               execute_hr_system,
    TOOL_CALENDAR,         execute_calendar_api,
)

_REGISTRY: dict[str, tuple[dict, callable]] = {
    "database_query":          (TOOL_DATABASE_QUERY,          execute_database_query),
    "customer_360_lookup":     (TOOL_CUSTOMER_360,            execute_customer_360),
    "transaction_history":     (TOOL_TRANSACTION_HISTORY,     execute_transaction_history),
    "credit_bureau_api":       (TOOL_CREDIT_BUREAU,           execute_credit_bureau),
    "risk_scoring_engine":     (TOOL_RISK_SCORING,            execute_risk_scoring),
    "payment_gateway":         (TOOL_PAYMENT_GATEWAY,         execute_payment_gateway),
    "swift_api":               (TOOL_SWIFT,                   execute_swift_api),
    "collateral_valuation":    (TOOL_COLLATERAL_VALUATION,    execute_collateral_valuation),
    "stress_test_engine":      (TOOL_STRESS_TEST,             execute_stress_test),
    "portfolio_analytics":     (TOOL_PORTFOLIO_ANALYTICS,     execute_portfolio_analytics),
    "ml_model_inference":      (TOOL_ML_INFERENCE,            execute_ml_inference),
    "market_data_feed":        (TOOL_MARKET_DATA,             execute_market_data),
    "fx_rate_api":             (TOOL_FX_RATE,                 execute_fx_rate),
    "fraud_detection_api":     (TOOL_FRAUD_DETECTION,         execute_fraud_detection),
    "aml_screening":           (TOOL_AML_SCREENING,           execute_aml_screening),
    "sanctions_check":         (TOOL_SANCTIONS,               execute_sanctions_check),
    "kyc_verification":        (TOOL_KYC,                     execute_kyc_verification),
    "document_ocr":            (TOOL_DOCUMENT_OCR,            execute_document_ocr),
    "data_quality_checker":    (TOOL_DATA_QUALITY,            execute_data_quality),
    "data_lineage_api":        (TOOL_DATA_LINEAGE,            execute_data_lineage),
    "regulatory_reporting_api":(TOOL_REG_REPORTING,           execute_regulatory_reporting),
    "email_sender":            (TOOL_EMAIL,                   execute_email_sender),
    "sms_sender":              (TOOL_SMS,                     execute_sms_sender),
    "alert_manager":           (TOOL_ALERT,                   execute_alert_manager),
    "audit_logger":            (TOOL_AUDIT,                   execute_audit_logger),
    "workflow_trigger":        (TOOL_WORKFLOW,                execute_workflow_trigger),
    "approval_request":        (TOOL_APPROVAL,                execute_approval_request),
    "report_generator":        (TOOL_REPORT,                  execute_report_generator),
    "dashboard_writer":        (TOOL_DASHBOARD,               execute_dashboard_writer),
    "sentiment_analyzer":      (TOOL_SENTIMENT,               execute_sentiment_analyzer),
    "crm_api":                 (TOOL_CRM,                     execute_crm_api),
    "product_catalog":         (TOOL_PRODUCTS,                execute_product_catalog),
    "hr_system_api":           (TOOL_HR,                      execute_hr_system),
    "calendar_api":            (TOOL_CALENDAR,                execute_calendar_api),
    "limit_override_request":  (TOOL_APPROVAL,                execute_approval_request),
}


def get_tool_schema(name: str) -> dict | None:
    entry = _REGISTRY.get(name)
    return entry[0] if entry else None


def execute_tool(name: str, arguments: dict, mask_pii: bool = True) -> dict:
    entry = _REGISTRY.get(name)
    if not entry:
        return {"error": f"Tool '{name}' not found in registry", "available": list(_REGISTRY.keys())}
    _, handler = entry
    try:
        result = handler(**arguments)
        if mask_pii:
            from core.pii_guard import guard_tool_result
            result = guard_tool_result(name, result)
        return result
    except Exception as exc:
        return {"error": f"Tool execution failed: {exc}", "tool": name}


def get_schemas_for_agent(tool_names: list[str]) -> list[dict]:
    schemas = []
    for name in tool_names:
        schema = get_tool_schema(name)
        if schema:
            schemas.append(schema)
    return schemas


def list_all_tools() -> list[str]:
    return sorted(_REGISTRY.keys())
