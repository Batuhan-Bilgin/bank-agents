
import hashlib
import json
import os
from typing import Any
from datetime import datetime

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from core.tool_registry import get_schemas_for_agent, execute_tool
from core.metrics import AgentCallMetric, record_tool
from core.hitl import needs_review, queue_for_review
from core.memory import save_turn, build_context_block
from training.decision_logger import log_decision
from core.tool_guard import guard_execute

load_dotenv()
console = Console()


def _extract_decision(text: str) -> str:
    for keyword in ("APPROVE", "DECLINE", "REFER", "ESCALATE", "ALERT", "ONAY", "RED", "İNCELE"):
        if keyword in text.upper():
            return keyword
    return ""

MODEL = "claude-opus-4-6"
MAX_TOKENS = 8192
MAX_TOOL_LOOPS = 15


class BaseAgent:

    def __init__(self, config: dict):
        self.id: str = config["id"]
        self.role: str = config["role"]
        self.department: str = config["department"]
        self.specialization: str = config["specialization"]
        self.authority_level: int = config["authority_level"]
        self.base_instructions: str = config["base_instructions"]
        self.tool_names: list[str] = config.get("tools", [])
        self.data_access: list[str] = config.get("data_access", [])
        self.escalation_path: str = config.get("escalation_path", "")
        self.compliance_flags: list[str] = config.get("compliance_flags", [])
        self.languages: list[str] = config.get("languages", ["tr", "en"])
        self.max_auto_approval: float = config.get("max_auto_approval_amount", 0)
        self.audit_required: bool = config.get("audit_required", True)
        self.hitl_threshold: float = config.get("hitl_threshold", 0.6)

        self.knowledge_domains: list[str] = config.get("knowledge_domains", [])

        self._client: anthropic.Anthropic | None = None
        self._tool_schemas = get_schemas_for_agent(self.tool_names)
        self._conversation: list[dict] = []
        self._customer_id: str = ""
        self._dry_run: bool = config.get("dry_run", False)

    def _get_rag_context(self, query: str) -> str:
        try:
            from training.retriever import retrieve, is_ready
            if not is_ready():
                return ""
            domains = self.knowledge_domains if self.knowledge_domains else None
            return retrieve(query, domains=domains, top_k=5)
        except Exception:
            return ""

    def _build_system_prompt(self, rag_context: str = "",
                             memory_context: str = "") -> str:
        compliance_str = ", ".join(self.compliance_flags) if self.compliance_flags else "Standard"
        escalation = self.escalation_path or "Department Manager"
        auth_desc = (
            "Read-only; provide analysis and recommendations only." if self.authority_level == 1
            else "Recommend actions; require approval for execution." if self.authority_level == 2
            else "Execute standard operations within approved parameters." if self.authority_level == 3
            else f"Approve transactions up to {self.max_auto_approval:,.0f} TRY." if self.authority_level == 4
            else "Full executive authority within regulatory bounds."
        )
        rag_section = f"""
## Bank Policy & Workflow Context
The following is retrieved from official bank documents. Apply these rules with priority:

{rag_context}
""" if rag_context else ""
        memory_section = f"""
## Müşteri Geçmişi
{memory_context}
""" if memory_context else ""
        return f"""You are {self.role}, a specialised AI banking agent operating within the {self.department} department at BankAI.

## Your Identity
- Agent ID: {self.id}
- Role: {self.role}
- Department: {self.department}
- Specialization: {self.specialization}
- Authority Level: {self.authority_level}/5

## Core Instructions
{self.base_instructions}

## Operational Constraints
- **Authority Level {self.authority_level}**: {auth_desc}
- **Max Auto-Approval**: {f"{self.max_auto_approval:,.0f} TRY" if self.max_auto_approval > 0 else "Not applicable — refer all actions for approval."}
- **Escalation Path**: {escalation}
- **Audit Required**: {"Yes — every action must be logged." if self.audit_required else "Logging recommended but not mandatory."}

## Compliance Framework
You operate under: {compliance_str}
Always apply relevant regulatory requirements in every decision.

## Data Access
You may access the following data categories: {", ".join(self.data_access) if self.data_access else "As granted by tool permissions."}.

## Tool Usage Rules
1. Only use the tools explicitly provided to you.
2. Always log significant actions using audit_logger.
3. For any action above your authority level, use approval_request or alert_manager.
4. Present tool results in a clear, professional manner.
5. If a tool returns an error, handle it gracefully and inform the user.

## Communication Standards
- Be precise, professional, and concise.
- Use structured output (tables, bullet points) for complex information.
- Support both Turkish (tr) and English (en) — respond in the language the user writes in.
- Never disclose sensitive customer data beyond what is necessary for the task.
- For ambiguous requests, ask clarifying questions before acting.
{memory_section}{rag_section}"""

    def chat(self, user_message: str, verbose: bool = True,
             customer_id: str = "") -> str:
        if customer_id:
            self._customer_id = customer_id
        self._rag_context = self._get_rag_context(user_message)
        if self._customer_id:
            save_turn(self._customer_id, self.id, "user", user_message)
        self._conversation.append({"role": "user", "content": user_message})

        metric = AgentCallMetric(self.id, self.department, "anthropic")
        metric.task_hash = hashlib.md5(user_message.encode()).hexdigest()[:8]

        if verbose:
            console.print(Panel(
                f"[bold cyan]{self.role}[/bold cyan]\n[dim]{self.department}[/dim]",
                title="[green]Agent Active[/green]", border_style="green"
            ))

        loop_count = 0
        while loop_count < MAX_TOOL_LOOPS:
            loop_count += 1
            try:
                response = self._call_api()
            except Exception as exc:
                metric.error = str(exc)[:200]
                metric.loop_count = loop_count
                metric.stop()
                metric.save()
                raise

            if hasattr(response, "usage") and response.usage:
                metric.input_tokens += getattr(response.usage, "input_tokens", 0)
                metric.output_tokens += getattr(response.usage, "output_tokens", 0)

            text_blocks = []
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    text_blocks.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(block)

            self._conversation.append({
                "role": "assistant",
                "content": response.content
            })

            if response.stop_reason == "end_turn" or not tool_calls:
                final_text = "\n".join(text_blocks).strip()
                metric.loop_count = loop_count
                metric.decision = _extract_decision(final_text)
                metric.stop()
                metric.save()
                review_needed, conf, reason = needs_review(final_text, self.hitl_threshold)
                if review_needed:
                    qid = queue_for_review(
                        self.id, self.department,
                        user_message, final_text, conf, reason
                    )
                    if verbose:
                        console.print(f"  [yellow]⚠ HITL:[/yellow] Yanıt inceleme kuyruğuna alındı "
                                      f"(#[bold]{qid}[/bold], güven: {conf:.2f})")
                if self._customer_id and final_text:
                    save_turn(self._customer_id, self.id, "assistant", final_text)
                if final_text:
                    try:
                        log_decision(
                            self.id, self.department, user_message, final_text,
                            metric.decision, getattr(self, "_rag_context", "")
                        )
                    except Exception:
                        pass
                if verbose and final_text:
                    console.print(Panel(Markdown(final_text), title="[blue]Response[/blue]",
                                        border_style="blue"))
                return final_text

            tool_results = []
            for tc in tool_calls:
                metric.tool_calls += 1
                if verbose:
                    console.print(f"  [yellow]>> Tool:[/yellow] [bold]{tc.name}[/bold] "
                                  f"[dim]{json.dumps(tc.input)[:120]}[/dim]")
                with record_tool(self.id, tc.name):
                    result = guard_execute(
                        self.id, tc.name, tc.input,
                        self.authority_level, self._dry_run
                    )
                if verbose:
                    console.print(f"  [green]<< Result:[/green] [dim]{str(result)[:200]}[/dim]")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str)
                })

            self._conversation.append({"role": "user", "content": tool_results})

        metric.loop_count = MAX_TOOL_LOOPS
        metric.stop()
        metric.save()
        return "Maximum tool loop iterations reached. Please refine your request."

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                raise EnvironmentError(
                    "ANTHROPIC_API_KEY is not set. "
                    "Copy .env.example to .env and add your API key."
                )
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def _call_api(self) -> anthropic.types.Message:
        mem_ctx = build_context_block(self._customer_id) if self._customer_id else ""
        kwargs: dict[str, Any] = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "system": self._build_system_prompt(
                getattr(self, "_rag_context", ""), mem_ctx
            ),
            "messages": self._conversation,
            "thinking": {"type": "adaptive"},
        }
        if self._tool_schemas:
            kwargs["tools"] = self._tool_schemas

        return self._get_client().messages.create(**kwargs)

    def reset(self):
        self._conversation = []

    def get_history(self) -> list[dict]:
        return self._conversation.copy()

    def __repr__(self):
        return f"<Agent {self.id} | {self.role} | L{self.authority_level}>"
