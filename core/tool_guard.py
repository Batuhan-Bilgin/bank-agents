import time
from collections import defaultdict
from threading import Lock

_rate_store: dict[str, list[float]] = defaultdict(list)
_rate_lock = Lock()

WRITE_TOOLS = {
    "payment_gateway", "swift_api", "email_sender", "sms_sender",
    "alert_manager", "audit_logger", "workflow_trigger", "approval_request",
    "report_generator", "dashboard_writer", "crm_api", "hr_system_api",
    "regulatory_reporting_api", "limit_override_request",
}

HIGH_RISK_TOOLS = {
    "payment_gateway", "swift_api", "limit_override_request",
}

RATE_LIMITS: dict[str, tuple[int, int]] = {
    "payment_gateway":    (5, 60),
    "swift_api":          (3, 60),
    "email_sender":       (20, 60),
    "sms_sender":         (10, 60),
    "alert_manager":      (30, 60),
    "audit_logger":       (100, 60),
    "approval_request":   (10, 60),
    "_default":           (50, 60),
}


class ToolGuardError(Exception):
    pass


class RateLimitError(ToolGuardError):
    pass


class PermissionError(ToolGuardError):
    pass


def check_rate_limit(agent_id: str, tool_name: str) -> None:
    key = f"{agent_id}:{tool_name}"
    max_calls, window = RATE_LIMITS.get(tool_name, RATE_LIMITS["_default"])
    now = time.monotonic()

    with _rate_lock:
        calls = _rate_store[key]
        cutoff = now - window
        _rate_store[key] = [t for t in calls if t > cutoff]
        if len(_rate_store[key]) >= max_calls:
            raise RateLimitError(
                f"Rate limit: {tool_name} için {window}s içinde {max_calls} çağrı limiti aşıldı "
                f"(agent: {agent_id})"
            )
        _rate_store[key].append(now)


def check_permission(agent_id: str, tool_name: str,
                     authority_level: int, dry_run: bool = False) -> None:
    if tool_name in HIGH_RISK_TOOLS and authority_level < 3:
        raise PermissionError(
            f"{tool_name} yüksek riskli bir tool. "
            f"Minimum yetki seviyesi 3 gerekli, mevcut: {authority_level}."
        )
    if tool_name in WRITE_TOOLS and dry_run:
        raise ToolGuardError(
            f"DRY-RUN modu: {tool_name} yazma işlemi simüle edildi (gerçekte çalıştırılmadı)."
        )


def guard_execute(agent_id: str, tool_name: str, arguments: dict,
                  authority_level: int = 3, dry_run: bool = False) -> dict:
    try:
        check_rate_limit(agent_id, tool_name)
    except RateLimitError as e:
        return {"error": str(e), "tool": tool_name, "guard": "rate_limit"}

    try:
        check_permission(agent_id, tool_name, authority_level, dry_run)
    except PermissionError as e:
        return {"error": str(e), "tool": tool_name, "guard": "permission"}
    except ToolGuardError as e:
        return {"simulated": True, "tool": tool_name, "note": str(e),
                "arguments": arguments}

    from core.tool_registry import execute_tool
    return execute_tool(tool_name, arguments)


def rate_stats(agent_id: str | None = None) -> dict:
    with _rate_lock:
        now = time.monotonic()
        result = {}
        for key, calls in _rate_store.items():
            a_id, tool = key.split(":", 1)
            if agent_id and a_id != agent_id:
                continue
            _, window = RATE_LIMITS.get(tool, RATE_LIMITS["_default"])
            recent = [t for t in calls if t > now - window]
            result[key] = {"recent_calls": len(recent), "window_s": window}
    return result
