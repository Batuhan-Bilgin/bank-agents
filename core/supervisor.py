import json
import os
from typing import Any

from rich.console import Console
from rich.panel import Panel

console = Console()

_SUPERVISOR_SYSTEM = """You are the BankAI Supervisor — the central routing intelligence of a multi-agent banking system.

You have access to 80 specialized agents across 11 departments. Your job is to:
1. Analyze the incoming task.
2. Select the most appropriate agent(s) to handle it.
3. Determine whether agents should run sequentially (pipeline) or in parallel.
4. After receiving agent results, decide whether to accept them or request further analysis.

Available departments and their first-line agents:
- Credit Risk → credit_risk_analyst_001
- Fraud Detection → transaction_fraud_detector_011
- AML/KYC → aml_transaction_monitor_019
- Customer Service → customer_inquiry_agent_027
- Data Quality → data_quality_monitor_037
- Treasury & Liquidity → liquidity_risk_manager_043
- Regulatory Compliance → regulatory_reporting_agent_049
- Retail Banking → retail_loan_officer_057
- Corporate & SME Banking → corporate_relationship_manager_063
- Operations & Process → payment_operations_agent_069
- IT & Cybersecurity → cybersecurity_analyst_075

Respond ONLY in valid JSON with this structure:
{
  "mode": "single" | "pipeline" | "parallel" | "parallel_then_merge",
  "agents": ["agent_id_1", "agent_id_2"],
  "merge_agent": "agent_id" (only for parallel_then_merge),
  "reasoning": "brief explanation"
}"""


def _get_llm_client():
    provider = os.environ.get("PROVIDER", "anthropic").lower()
    if provider == "groq":
        import groq as groq_sdk
        return "groq", groq_sdk.Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    import anthropic
    return "anthropic", anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def _route(task: str) -> dict:
    provider, client = _get_llm_client()

    if provider == "groq":
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=512,
            messages=[
                {"role": "system", "content": _SUPERVISOR_SYSTEM},
                {"role": "user", "content": f"Görev: {task}"},
            ],
        )
        raw = resp.choices[0].message.content or ""
    else:
        resp = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            system=_SUPERVISOR_SYSTEM,
            messages=[{"role": "user", "content": f"Görev: {task}"}],
        )
        raw = resp.content[0].text if resp.content else ""

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return {"mode": "single", "agents": ["customer_inquiry_agent_027"],
                "reasoning": "JSON parse error — fallback"}
    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError:
        return {"mode": "single", "agents": ["customer_inquiry_agent_027"],
                "reasoning": "JSON decode error — fallback"}


class Supervisor:

    def __init__(self, orchestrator=None):
        if orchestrator is None:
            from core.orchestrator import Orchestrator
            self._orch = Orchestrator()
        else:
            self._orch = orchestrator

    def run(self, task: str, verbose: bool = True) -> dict:
        if verbose:
            console.print(Panel(
                f"[dim]{task[:200]}[/dim]",
                title="[magenta]Supervisor: Görev Analizi[/magenta]",
                border_style="magenta"
            ))

        routing = _route(task)

        if verbose:
            console.print(
                f"  [magenta]Mod:[/magenta] [bold]{routing.get('mode')}[/bold]  "
                f"[magenta]Ajanlar:[/magenta] {routing.get('agents')}  "
                f"[dim]{routing.get('reasoning', '')}[/dim]"
            )

        mode = routing.get("mode", "single")
        agents = routing.get("agents", ["customer_inquiry_agent_027"])

        if mode == "single":
            result = self._orch.run(agents[0], task, verbose=verbose)
            return {"mode": mode, "routing": routing, "result": result}

        elif mode == "pipeline":
            result = self._orch.pipeline(agents, task, verbose=verbose)
            return {"mode": mode, "routing": routing, "result": result}

        elif mode == "parallel":
            result = self._orch.parallel(agents, task, verbose=verbose)
            return {"mode": mode, "routing": routing, "result": result}

        elif mode == "parallel_then_merge":
            merge_id = routing.get("merge_agent", agents[-1])
            parallel_ids = [a for a in agents if a != merge_id]
            result = self._orch.parallel_then_merge(parallel_ids, merge_id, task, verbose=verbose)
            return {"mode": mode, "routing": routing, "result": result}

        result = self._orch.run(agents[0], task, verbose=verbose)
        return {"mode": "single_fallback", "routing": routing, "result": result}
