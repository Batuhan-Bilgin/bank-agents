import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "hitl.db"

UNCERTAINTY_PHRASES = [
    "emin değilim", "net değil", "belirsiz", "açıklama gerekiyor",
    "daha fazla bilgi", "unclear", "not sure", "uncertain",
    "ambiguous", "requires clarification", "cannot determine",
    "yetersiz bilgi", "eksik bilgi", "doğrulama gerekli",
]

HIGH_RISK_KEYWORDS = [
    "yüksek risk", "kritik", "acil", "şüpheli", "suspicious",
    "fraud", "dolandırıcılık", "kara para", "money laundering",
    "yaptırım", "sanction", "escalate", "eskalasyon",
]


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS review_queue (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT NOT NULL,
            agent_id    TEXT NOT NULL,
            department  TEXT NOT NULL,
            task        TEXT NOT NULL,
            agent_output TEXT NOT NULL,
            confidence  REAL NOT NULL,
            reason      TEXT NOT NULL,
            status      TEXT DEFAULT 'pending',
            reviewer    TEXT DEFAULT '',
            reviewer_decision TEXT DEFAULT '',
            reviewer_note TEXT DEFAULT '',
            resolved_at TEXT DEFAULT ''
        )
    """)
    conn.commit()
    return conn


def score_confidence(text: str) -> tuple[float, str]:
    text_lower = text.lower()
    reasons = []

    uncertainty_count = sum(1 for p in UNCERTAINTY_PHRASES if p in text_lower)
    high_risk_count = sum(1 for p in HIGH_RISK_KEYWORDS if p in text_lower)

    score = 1.0
    if uncertainty_count > 0:
        score -= min(0.4, uncertainty_count * 0.15)
        reasons.append(f"belirsizlik ifadesi ({uncertainty_count})")
    if high_risk_count > 0:
        score -= min(0.3, high_risk_count * 0.1)
        reasons.append(f"yüksek risk göstergesi ({high_risk_count})")
    if len(text) < 100:
        score -= 0.2
        reasons.append("çok kısa yanıt")
    if "?" in text and text.count("?") > 2:
        score -= 0.1
        reasons.append("çok sayıda soru işareti")

    score = max(0.0, min(1.0, score))
    reason = "; ".join(reasons) if reasons else "normal"
    return round(score, 3), reason


def needs_review(text: str, threshold: float = 0.6) -> tuple[bool, float, str]:
    confidence, reason = score_confidence(text)
    return confidence < threshold, confidence, reason


def queue_for_review(agent_id: str, department: str, task: str,
                     agent_output: str, confidence: float, reason: str) -> int:
    conn = _get_conn()
    cursor = conn.execute("""
        INSERT INTO review_queue
        (ts, agent_id, department, task, agent_output, confidence, reason)
        VALUES (?,?,?,?,?,?,?)
    """, (datetime.utcnow().isoformat(), agent_id, department,
          task[:2000], agent_output[:4000], confidence, reason))
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id


def get_pending(limit: int = 50) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT * FROM review_queue WHERE status = 'pending'
        ORDER BY confidence ASC, ts ASC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def resolve(item_id: int, decision: str, reviewer: str = "human",
            note: str = "") -> bool:
    conn = _get_conn()
    conn.execute("""
        UPDATE review_queue
        SET status = 'resolved', reviewer = ?, reviewer_decision = ?,
            reviewer_note = ?, resolved_at = ?
        WHERE id = ?
    """, (reviewer, decision, note, datetime.utcnow().isoformat(), item_id))
    affected = conn.total_changes
    conn.commit()
    conn.close()
    return affected > 0


def stats() -> dict:
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM review_queue WHERE status='pending'").fetchone()[0]
    by_agent = conn.execute("""
        SELECT agent_id, COUNT(*) as cnt FROM review_queue
        GROUP BY agent_id ORDER BY cnt DESC LIMIT 10
    """).fetchall()
    conn.close()
    return {
        "total": total,
        "pending": pending,
        "resolved": total - pending,
        "by_agent": [dict(r) for r in by_agent],
    }


def review_cli():
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    console = Console()
    pending = get_pending()

    if not pending:
        console.print("[green]İnceleme kuyruğu boş.[/green]")
        return

    console.print(f"\n[bold yellow]{len(pending)} bekleyen inceleme var[/bold yellow]\n")

    for item in pending:
        console.print(Panel(
            f"[bold]Agent:[/bold] {item['agent_id']} ({item['department']})\n"
            f"[bold]Güven:[/bold] {item['confidence']:.2f} — {item['reason']}\n"
            f"[bold]Zaman:[/bold] {item['ts']}\n\n"
            f"[bold]Görev:[/bold]\n{item['task'][:300]}\n\n"
            f"[bold]Agent Çıktısı:[/bold]\n{item['agent_output'][:500]}",
            title=f"[yellow]#{item['id']} — İNCELEME BEKLİYOR[/yellow]",
            border_style="yellow"
        ))
        decision = input("Karar (approve/reject/escalate/skip): ").strip().lower()
        if decision == "skip":
            continue
        note = input("Not (boş bırakılabilir): ").strip()
        if resolve(item["id"], decision, note=note):
            console.print(f"[green]#{item['id']} çözümlendi: {decision}[/green]\n")


if __name__ == "__main__":
    review_cli()
