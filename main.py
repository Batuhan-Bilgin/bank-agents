
import argparse
import sys
import os

from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt, Confirm

load_dotenv()
console = Console()


def check_env():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key or key == "your_api_key_here":
        console.print("[red]ERROR:[/red] ANTHROPIC_API_KEY not set.")
        console.print("Copy .env.example to .env and add your API key.")
        sys.exit(1)


def demo_mode(orchestrator):
    demos = [
        {
            "title": "Credit Risk — Loan Application Review",
            "agent": "credit_risk_analyst_001",
            "task": (
                "Müşteri C12345 için 500,000 TRY tutarında 60 ay vadeli konut kredisi "
                "başvurusu geldi. Aylık net geliri 25,000 TRY. Kredi bürosundaki "
                "sicil durumunu değerlendir ve bir risk görüşü oluştur."
            )
        },
        {
            "title": "Fraud Detection — Suspicious Transaction",
            "agent": "transaction_fraud_detector_011",
            "task": (
                "Customer C98765 just initiated a TRY 85,000 wire transfer to a new "
                "beneficiary registered 2 hours ago, via mobile banking from a new "
                "device with an IP geolocated in Romania. The customer's usual "
                "transaction limit is TRY 5,000. Assess this transaction."
            )
        },
        {
            "title": "AML/KYC — Sanctions Screening",
            "agent": "sanctions_screening_agent_023",
            "task": (
                "Incoming SWIFT MT103 payment: USD 250,000 from 'Al Baraka Trading "
                "LLC' via a correspondent bank in UAE. Please screen the sender and "
                "all payment parties against relevant sanctions lists."
            )
        },
        {
            "title": "Customer Service — VIP Client Query",
            "agent": "vip_customer_service_agent_034",
            "task": (
                "VIP müşterimiz Müşteri C10001, mevduat hesabındaki son 3 aydaki "
                "faiz ödemelerini ve döviz mevduat bakiyelerini sorguluyor. "
                "Ayrıca yatırım portföyü performansı hakkında bilgi istiyor."
            )
        },
        {
            "title": "Multi-Agent Pipeline — NPL Recovery",
            "pipeline": ["npl_manager_007", "collateral_evaluator_005", "suspicious_activity_reporter_021"],
            "task": (
                "Corporate customer C55000 has been 95 days past due on a TRY 2.5M "
                "loan. Collateral is a commercial property in Istanbul. Review the "
                "account, assess collateral coverage, and determine if any AML "
                "concerns exist that should be reported."
            )
        }
    ]

    console.print("\n[bold green]━━━ BankAI Demo Mode ━━━[/bold green]\n")

    for i, demo in enumerate(demos, 1):
        console.print(f"\n[bold yellow]Demo {i}/{len(demos)}: {demo['title']}[/bold yellow]")
        if not Confirm.ask("Run this demo?", default=True):
            continue

        if "pipeline" in demo:
            results = orchestrator.pipeline(demo["pipeline"], demo["task"])
            console.print(f"\n[green]Pipeline complete.[/green] {len(results)} agents responded.")
        else:
            orchestrator.run(demo["agent"], demo["task"])

        console.print()

    console.print("[bold green]Demo complete![/bold green]")


def interactive_cli(orchestrator):
    console.print("\n[bold green]BankAI Interactive Mode[/bold green]")
    console.print("[dim]Commands: /list, /list <dept>, /stats, /agent <id>, /auto, /quit[/dim]\n")

    current_agent = None

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]BankAI[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue

        if user_input == "/quit" or user_input == "/exit":
            console.print("[dim]Goodbye.[/dim]")
            break

        elif user_input == "/list":
            orchestrator.list_agents()

        elif user_input.startswith("/list "):
            dept = user_input[6:].strip()
            orchestrator.list_agents(department=dept)

        elif user_input == "/stats":
            orchestrator.stats()

        elif user_input.startswith("/agent "):
            agent_id = user_input[7:].strip()
            try:
                current_agent = orchestrator._factory.get(agent_id)
                console.print(f"[green]Switched to:[/green] {current_agent.role}")
            except ValueError as e:
                console.print(f"[red]{e}[/red]")

        elif user_input == "/auto":
            current_agent = None
            console.print("[dim]Auto-routing mode active.[/dim]")

        elif user_input == "/reset":
            if current_agent:
                current_agent.reset()
                console.print("[dim]Conversation reset.[/dim]")

        elif user_input.startswith("/"):
            console.print(f"[red]Unknown command:[/red] {user_input}")

        else:
            if current_agent:
                current_agent.chat(user_input)
            else:
                orchestrator.auto(user_input)


def main():
    parser = argparse.ArgumentParser(description="BankAI — 100 Specialised Banking AI Agents")
    parser.add_argument("--demo",   action="store_true", help="Run built-in demos")
    parser.add_argument("--list",   action="store_true", help="List agents")
    parser.add_argument("--dept",   type=str, default=None, help="Filter by department")
    parser.add_argument("--stats",  action="store_true", help="Show network statistics")
    parser.add_argument("--agent",  type=str, default=None, help="Agent ID to use")
    parser.add_argument("--auto",   action="store_true", help="Auto-route task")
    parser.add_argument("--task",   type=str, default=None, help="Task string")
    args = parser.parse_args()

    check_env()

    from core.orchestrator import Orchestrator
    orchestrator = Orchestrator()

    if args.list:
        orchestrator.list_agents(department=args.dept)
        return

    if args.stats:
        orchestrator.stats()
        return

    if args.agent and args.task:
        orchestrator.run(args.agent, args.task)
        return

    if args.auto and args.task:
        orchestrator.auto(args.task)
        return

    if args.demo:
        demo_mode(orchestrator)
        return

    interactive_cli(orchestrator)


if __name__ == "__main__":
    main()
