import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "memory.db"
MAX_HISTORY_TURNS = 20
SUMMARY_THRESHOLD = 30


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ts         TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            agent_id   TEXT NOT NULL,
            role       TEXT NOT NULL,
            content    TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            summary     TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conv_customer
        ON conversations(customer_id, ts)
    """)
    conn.commit()
    return conn


def save_turn(customer_id: str, agent_id: str, role: str, content: str):
    if isinstance(content, (dict, list)):
        content = json.dumps(content, ensure_ascii=False)
    conn = _get_conn()
    conn.execute("""
        INSERT INTO conversations (ts, customer_id, agent_id, role, content)
        VALUES (?,?,?,?,?)
    """, (datetime.utcnow().isoformat(), customer_id, agent_id, role, str(content)[:4000]))
    conn.commit()
    conn.close()


def get_history(customer_id: str, limit: int = MAX_HISTORY_TURNS) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT role, content, agent_id, ts FROM conversations
        WHERE customer_id = ?
        ORDER BY ts DESC LIMIT ?
    """, (customer_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_summary(customer_id: str) -> str:
    conn = _get_conn()
    row = conn.execute("""
        SELECT summary FROM summaries WHERE customer_id = ?
        ORDER BY ts DESC LIMIT 1
    """, (customer_id,)).fetchone()
    conn.close()
    return row["summary"] if row else ""


def save_summary(customer_id: str, summary: str):
    conn = _get_conn()
    conn.execute("""
        INSERT INTO summaries (ts, customer_id, summary) VALUES (?,?,?)
    """, (datetime.utcnow().isoformat(), customer_id, summary))
    conn.commit()
    conn.close()


def build_context_block(customer_id: str) -> str:
    if not customer_id:
        return ""

    summary = get_summary(customer_id)
    history = get_history(customer_id, limit=10)

    parts = []
    if summary:
        parts.append(f"## Müşteri Özeti\n{summary}")

    if history:
        lines = []
        for turn in history:
            prefix = "Müşteri" if turn["role"] == "user" else f"Ajan ({turn['agent_id']})"
            lines.append(f"[{turn['ts'][:16]}] {prefix}: {turn['content'][:200]}")
        parts.append("## Son Etkileşimler\n" + "\n".join(lines))

    return "\n\n".join(parts) if parts else ""


def auto_summarize(customer_id: str, llm_fn=None) -> str:
    history = get_history(customer_id, limit=SUMMARY_THRESHOLD)
    if len(history) < SUMMARY_THRESHOLD:
        return ""

    text = "\n".join(
        f"{t['role']}: {t['content'][:200]}"
        for t in history
    )

    if llm_fn:
        summary = llm_fn(
            f"Aşağıdaki bankacılık müşteri etkileşimini 3-5 cümleyle özetle. "
            f"Müşterinin talepleri, verilen kararlar ve açık işlemleri belirt:\n\n{text}"
        )
    else:
        summary = f"Son {len(history)} etkileşim özetlendi. İlk mesaj: {history[0]['content'][:100]}"

    save_summary(customer_id, summary)
    return summary


def delete_customer(customer_id: str):
    conn = _get_conn()
    conn.execute("DELETE FROM conversations WHERE customer_id = ?", (customer_id,))
    conn.execute("DELETE FROM summaries WHERE customer_id = ?", (customer_id,))
    conn.commit()
    conn.close()
