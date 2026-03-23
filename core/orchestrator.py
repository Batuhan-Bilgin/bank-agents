import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.agent_factory import get_factory
from core.metrics import summary as metrics_summary
from core.hitl import stats as hitl_stats, get_pending

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

    def parallel(self, agent_ids: list[str], task: str,
                 verbose: bool = True, max_workers: int = 4) -> dict[str, str]:
        results: dict[str, str] = {}

        if verbose:
            console.print(f"\n[bold green]Paralel çalıştırma:[/bold green] "
                          f"{len(agent_ids)} ajan aynı anda başlıyor...")

        agents = {aid: self._factory.get(aid) for aid in agent_ids}

        with ThreadPoolExecutor(max_workers=min(max_workers, len(agent_ids))) as executor:
            future_to_id = {
                executor.submit(agent.chat, task, verbose): aid
                for aid, agent in agents.items()
            }
            for future in as_completed(future_to_id):
                aid = future_to_id[future]
                try:
                    results[aid] = future.result()
                except Exception as exc:
                    results[aid] = f"[HATA] {exc}"
                finally:
                    agents[aid].reset()

        return results

    def parallel_then_merge(self, parallel_ids: list[str], merge_id: str,
                            task: str, verbose: bool = True) -> str:
        if verbose:
            console.rule("[cyan]Aşama 1: Paralel Analiz[/cyan]")
        parallel_results = self.parallel(parallel_ids, task, verbose=verbose)

        merge_input = (
            f"Orijinal görev:\n{task}\n\n"
            f"Paralel ajan analizleri:\n"
            + json.dumps(parallel_results, ensure_ascii=False, indent=2)
        )

        merge_agent = self._factory.get(merge_id)
        if verbose:
            console.rule(f"[cyan]Aşama 2: Sentez — {merge_agent.role}[/cyan]")
        result = merge_agent.chat(merge_input, verbose=verbose)
        merge_agent.reset()
        return result

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

    def metrics(self, hours: int = 24) -> None:
        data = metrics_summary(hours)
        table = Table(title=f"Agent Metrikleri (son {hours} saat)")
        table.add_column("Agent", style="cyan")
        table.add_column("Çağrı", justify="right")
        table.add_column("Ort. Süre (ms)", justify="right")
        table.add_column("Token", justify="right")
        table.add_column("Tool", justify="right")
        table.add_column("Hata", justify="right", style="red")
        for r in data["agents"]:
            table.add_row(
                r["agent_id"],
                str(r["calls"]),
                f"{r['avg_latency']:.0f}",
                str(r["total_tokens"] or 0),
                str(r["total_tools"] or 0),
                str(r["errors"] or 0),
            )
        console.print(table)

        hs = hitl_stats()
        console.print(Panel(
            f"Toplam: {hs['total']}  |  "
            f"Bekleyen: [yellow]{hs['pending']}[/yellow]  |  "
            f"Çözümlendi: [green]{hs['resolved']}[/green]",
            title="[yellow]HITL Kuyruğu[/yellow]", border_style="yellow"
        ))

    def departments(self) -> list[str]:
        return self._factory.list_departments()
