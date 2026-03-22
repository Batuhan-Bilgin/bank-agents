
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.agent_factory import get_factory
from core.base_agent import BaseAgent

console = Console()


class Orchestrator:

    def __init__(self):
        self._factory = get_factory()

    def run(self, agent_id: str, task: str, verbose: bool = True) -> str:
        agent = self._factory.get(agent_id)
        if verbose:
            console.print(f"\n[bold]Routing to:[/bold] {agent.role} ({agent.department})")
        return agent.chat(task, verbose=verbose)

    def auto(self, task: str, verbose: bool = True) -> str:
        agent = self._factory.best_agent_for(task)
        if verbose:
            console.print(
                f"\n[dim]Auto-selected:[/dim] [bold cyan]{agent.role}[/bold cyan] "
                f"[dim]({agent.department})[/dim]"
            )
        return agent.chat(task, verbose=verbose)

    def pipeline(self, agent_ids: list[str], task: str,
                 verbose: bool = True) -> dict[str, str]:
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
            agent.reset()

        return results

    def broadcast(self, department: str, task: str,
                  verbose: bool = False) -> dict[str, str]:
        agents = self._factory.get_by_department(department)
        results = {}
        for agent in agents:
            if verbose:
                console.print(f"[dim]Running:[/dim] {agent.role}")
            results[agent.id] = agent.chat(task, verbose=verbose)
            agent.reset()
        return results

    def list_agents(self, department: str | None = None) -> None:
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
