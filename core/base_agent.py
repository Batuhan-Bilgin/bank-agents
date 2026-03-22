"""
BaseAgent — core agentic loop using the Anthropic API with tool use.
All 100 banking agents inherit from this class.
"""

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

load_dotenv()
console = Console()

MODEL = "claude-opus-4-6"
MAX_TOKENS = 8192
MAX_TOOL_LOOPS = 15          # safety cap on agentic loops


class BaseAgent:
    """
    Banking AI Agent powered by Claude Opus 4.6 with adaptive thinking.

    Each agent is configured via agents_config.json and has:
    - A rich system prompt (base_instructions)
    - A specific set of permitted tools
    - Authority level constraints
    - Compliance framework awareness
    """

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

        self._client: anthropic.Anthropic | None = None  # lazy init on first call
        self._tool_schemas = get_schemas_for_agent(self.tool_names)
        self._conversation: list[dict] = []

    # ------------------------------------------------------------------
    # System prompt construction
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        compliance_str = ", ".join(self.compliance_flags) if self.compliance_flags else "Standard"
        escalation = self.escalation_path or "Department Manager"
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
- **Authority Level {self.authority_level}**: {"Read-only; provide analysis and recommendations only." if self.authority_level == 1 else "Recommend actions; require approval for execution." if self.authority_level == 2 else "Execute standard operations within approved parameters." if self.authority_level == 3 else "Approve transactions up to {self.max_auto_approval:,.0f} TRY." if self.authority_level == 4 else "Full executive authority within regulatory bounds."}
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
"""

    # ------------------------------------------------------------------
    # Core agentic loop
    # ------------------------------------------------------------------

    def chat(self, user_message: str, verbose: bool = True) -> str:
        """
        Process a user message through the full agentic loop.
        Returns the final text response.
        """
        self._conversation.append({"role": "user", "content": user_message})

        if verbose:
            console.print(Panel(
                f"[bold cyan]{self.role}[/bold cyan]\n[dim]{self.department}[/dim]",
                title="[green]Agent Active[/green]", border_style="green"
            ))

        loop_count = 0
        while loop_count < MAX_TOOL_LOOPS:
            loop_count += 1
            response = self._call_api()

            # Collect text and tool calls from the response
            text_blocks = []
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    text_blocks.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(block)

            # Append assistant turn to conversation history
            self._conversation.append({
                "role": "assistant",
                "content": response.content
            })

            # If no tool calls — we're done
            if response.stop_reason == "end_turn" or not tool_calls:
                final_text = "\n".join(text_blocks).strip()
                if verbose and final_text:
                    console.print(Panel(Markdown(final_text), title="[blue]Response[/blue]",
                                        border_style="blue"))
                return final_text

            # Execute all tool calls
            tool_results = []
            for tc in tool_calls:
                if verbose:
                    console.print(f"  [yellow]>> Tool:[/yellow] [bold]{tc.name}[/bold] "
                                  f"[dim]{json.dumps(tc.input)[:120]}[/dim]")
                result = execute_tool(tc.name, tc.input)
                if verbose:
                    console.print(f"  [green]<< Result:[/green] [dim]{str(result)[:200]}[/dim]")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str)
                })

            # Feed tool results back
            self._conversation.append({"role": "user", "content": tool_results})

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
        """Single API call with adaptive thinking."""
        kwargs: dict[str, Any] = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "system": self._build_system_prompt(),
            "messages": self._conversation,
            "thinking": {"type": "adaptive"},
        }
        if self._tool_schemas:
            kwargs["tools"] = self._tool_schemas

        return self._get_client().messages.create(**kwargs)

    # ------------------------------------------------------------------
    # Conversation management
    # ------------------------------------------------------------------

    def reset(self):
        """Clear conversation history (start fresh session)."""
        self._conversation = []

    def get_history(self) -> list[dict]:
        return self._conversation.copy()

    def __repr__(self):
        return f"<Agent {self.id} | {self.role} | L{self.authority_level}>"
