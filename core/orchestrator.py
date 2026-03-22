"""
Orchestrator — routes tasks to the appropriate agent(s) and
supports multi-agent collaboration patterns.
"""

import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.agent_factory import get_factory
from core.base_agent import BaseAgent

console = Console()


class Orchestrator:
    """
    Central coordinator for the bank's AI agent network.

    Routing strategies:
    1. Direct by ID  — orchestrator.run("fraud_alert_manager_017", task)
    2. Auto-route    — orchestrator.auto(task)   [keyword-based]
    3. Multi-agent   — orchestrator.pipeline([id1, id2], task)  [sequential]
    """

    def __init__(self):
        self._factory = get_factory()

    # ------------------------------------------------------------------
    # Single-agent execution
    # ------------------------------------------------------------------

    def run(self, agent_id: str, task: str, verbose: bool = True) -> str:
        """Run a task with a specific agent identified by ID."""
        agent = self._factory.get(agent_id)
        if verbose:
            console.print(f"\n[bold]Routing to:[/bold] {agent.role} ({agent.department})")
        return agent.chat(task, verbose=verbose)

    # ------------------------------------------------------------------
    # Auto-routing
    # ------------------------------------------------------------------

    def auto(self, task: str, verbose: bool = True) -> str:
        """
        Automatically select the best agent for the task and run it.
        Uses keyword-based routing with department fallback.
        """
        agent = self._factory.best_agent_for(task)
        if verbose:
            console.print(
                f"\n[dim]Auto-selected:[/dim] [bold cyan]{agent.role}[/bold cyan] "
                f"[dim]({agent.department})[/dim]"
            )
        return agent.chat(task, verbose=verbose)

    # ------------------------------------------------------------------
    # Multi-agent pipeline
    # ------------------------------------------------------------------

    def pipeline(self, agent_ids: list[str], task: str,
                 verbose: bool = True) -> dict[str, str]:
        """
        Run a task sequentially through multiple agents.
        Each agent receives the original task + outputs of previous agents.
        Returns a dict of {agent_id: response}.
        """
        results: dict[str, str] = {}
        context = task

        for agent_id in agent_ids:
            agent = self._factory.get(agent_id)
            if verbose:
                console.rule(f"[cyan]{agent.role}[/cyan]")
            full_input = (
                f"{context}\n\n---\nPrevious agent outputs:\n"
                + json.dumps(results, ensure_ascii=False, indent=2)
                if results else context
            )
            response = agent.chat(full_input, verbose=verbose)
            results[agent_id] = response
            agent.reset()  # fresh conversation for next agent

        return results

    # ------------------------------------------------------------------
    # Broadcast (same task to all agents in a department)
    # ------------------------------------------------------------------

    def broadcast(self, department: str, task: str,
                  verbose: bool = False) -> dict[str, str]:
        """Send the same task to all agents in a department."""
        agents = self._factory.get_by_department(department)
        results = {}
        for agent in agents:
            if verbose:
                console.print(f"[dim]Running:[/dim] {agent.role}")
            results[agent.id] = agent.chat(task, verbose=verbose)
            agent.reset()
        return results

    # ------------------------------------------------------------------
    # Discovery helpers (no API calls)
    # ------------------------------------------------------------------

    def list_agents(self, department: str | None = None) -> None:
        """Print a formatted table of available agents."""
        agents = self._factory.list_agents(department=department)
        table = Table(title=f"BankAI Agents{' — ' + department if department else ''}")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Role", style="white")
        table.add_column("Department", style="yellow")
        table.add_column("Level", justify="center")
        table.add_column("Tools", justify="center")
        for a in agents:
            table.add_row(
                a["id"],
                a["role"],
                a["department"],
                str(a["authority_level"]),
                str(a["tool_count"])
            )
        console.print(table)

    def stats(self) -> None:
        """Print agent network statistics."""
        s = self._factory.stats()
        console.print(Panel(
            "\n".join([
                f"[bold]Total Agents:[/bold] {s['total_agents']}",
                f"[bold]Departments:[/bold] {s['departments']}",
                "",
                "[bold]By Department:[/bold]",
                *[f"  {dept}: {count}" for dept, count in s['by_department'].items()],
                "",
                "[bold]By Authority Level:[/bold]",
                *[f"  Level {lvl}: {count} agents" for lvl, count in s['by_authority_level'].items()],
            ]),
            title="[green]BankAI Agent Network[/green]",
            border_style="green"
        ))

    def departments(self) -> list[str]:
        return self._factory.list_departments()
