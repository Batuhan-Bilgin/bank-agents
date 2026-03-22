
import json
import os
from typing import Any

import groq as groq_sdk
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from core.tool_registry import get_schemas_for_agent, execute_tool

console = Console()

GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 4096
MAX_TOOL_LOOPS = 15


class GroqBaseAgent:

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

        self._client: groq_sdk.Groq | None = None
        self._anthropic_schemas = get_schemas_for_agent(self.tool_names)
        self._tool_schemas = self._to_openai_tools(self._anthropic_schemas)
        self._conversation: list[dict] = []

    @staticmethod
    def _to_openai_tools(anthropic_schemas: list[dict]) -> list[dict]:
        tools = []
        for s in anthropic_schemas:
            tools.append({
                "type": "function",
                "function": {
                    "name": s["name"],
                    "description": s.get("description", ""),
                    "parameters": s.get("input_schema", {
                        "type": "object", "properties": {}
                    }),
                },
            })
        return tools

    def _build_system_prompt(self) -> str:
        compliance_str = ", ".join(self.compliance_flags) if self.compliance_flags else "Standard"
        escalation = self.escalation_path or "Department Manager"
        auth_desc = {
            1: "Read-only; provide analysis and recommendations only.",
            2: "Recommend actions; require approval for execution.",
            3: "Execute standard operations within approved parameters.",
            4: f"Approve transactions up to {self.max_auto_approval:,.0f} TRY.",
            5: "Full executive authority within regulatory bounds.",
        }.get(self.authority_level, "Standard authority.")

        return f"""You are {self.role}, a specialised AI banking agent in the {self.department} department at BankAI.

## Your Identity
- Agent ID: {self.id}
- Department: {self.department}
- Specialization: {self.specialization}
- Authority Level: {self.authority_level}/5

## Core Instructions
{self.base_instructions}

## Operational Constraints
- Authority Level {self.authority_level}: {auth_desc}
- Max Auto-Approval: {f"{self.max_auto_approval:,.0f} TRY" if self.max_auto_approval > 0 else "Not applicable."}
- Escalation Path: {escalation}
- Audit Required: {"Yes — every action must be logged." if self.audit_required else "Recommended."}

## Compliance Framework
You operate under: {compliance_str}
Always apply relevant regulatory requirements in every decision.

## Tool Usage Rules
1. Only use the tools explicitly provided to you.
2. Always log significant actions using audit_logger.
3. For actions above your authority level, use approval_request or alert_manager.
4. Present results in a clear, professional manner.
5. If a tool returns an error, handle it gracefully.

## Communication Standards
- Be precise, professional, and concise.
- Use structured output (tables, bullet points) for complex information.
- Support both Turkish (tr) and English (en) — respond in the language the user writes in.
- Never disclose sensitive customer data beyond what is necessary."""

    def chat(self, user_message: str, verbose: bool = True) -> str:
        self._conversation.append({"role": "user", "content": user_message})

        if verbose:
            console.print(Panel(
                f"[bold cyan]{self.role}[/bold cyan]\n[dim]{self.department}[/dim]",
                title="[green]Agent Active (Groq)[/green]", border_style="green"
            ))

        loop_count = 0
        while loop_count < MAX_TOOL_LOOPS:
            loop_count += 1
            try:
                response = self._call_api()
            except groq_sdk.BadRequestError as e:
                err_msg = str(e)
                if verbose:
                    console.print(f"  [red]Model error:[/red] [dim]{err_msg[:200]}[/dim]")
                try:
                    fallback = self._get_client().chat.completions.create(
                        model=GROQ_MODEL,
                        max_tokens=MAX_TOKENS,
                        messages=[
                            {"role": "system", "content": self._build_system_prompt()},
                            *[m for m in self._conversation if m["role"] in ("user", "assistant") and not m.get("tool_calls")],
                            {"role": "user", "content": "Summarize your findings so far and provide a final answer based on the information you have gathered."},
                        ],
                    )
                    final_text = (fallback.choices[0].message.content or "").strip()
                    if verbose and final_text:
                        console.print(Panel(Markdown(final_text), title="[blue]Response[/blue]", border_style="blue"))
                    return final_text
                except Exception:
                    return "Analysis partially complete. Tool execution encountered an error — please retry."
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            self._conversation.append({
                "role": "assistant",
                "content": message.content or "",
                **({"tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    }
                    for tc in message.tool_calls
                ]} if message.tool_calls else {})
            })

            if finish_reason != "tool_calls" or not message.tool_calls:
                final_text = (message.content or "").strip()
                if verbose and final_text:
                    console.print(Panel(
                        Markdown(final_text),
                        title="[blue]Response[/blue]", border_style="blue"
                    ))
                return final_text

            for tc in message.tool_calls:
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                if verbose:
                    console.print(f"  [yellow]>> Tool:[/yellow] [bold]{tc.function.name}[/bold] "
                                  f"[dim]{tc.function.arguments[:120]}[/dim]")

                result = execute_tool(tc.function.name, arguments)

                if verbose:
                    console.print(f"  [green]<< Result:[/green] [dim]{str(result)[:200]}[/dim]")

                self._conversation.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

        return "Maximum tool loop iterations reached. Please refine your request."

    def _get_client(self) -> groq_sdk.Groq:
        if self._client is None:
            api_key = os.environ.get("GROQ_API_KEY", "")
            if not api_key:
                raise EnvironmentError(
                    "GROQ_API_KEY is not set. Add it to .env file."
                )
            self._client = groq_sdk.Groq(api_key=api_key)
        return self._client

    def _call_api(self):
        kwargs: dict[str, Any] = {
            "model": GROQ_MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": [
                {"role": "system", "content": self._build_system_prompt()}
            ] + self._conversation,
        }
        if self._tool_schemas:
            kwargs["tools"] = self._tool_schemas
            kwargs["tool_choice"] = "auto"

        return self._get_client().chat.completions.create(**kwargs)

    def reset(self):
        self._conversation = []

    def get_history(self) -> list[dict]:
        return self._conversation.copy()

    def __repr__(self):
        return f"<GroqAgent {self.id} | {self.role} | L{self.authority_level}>"
