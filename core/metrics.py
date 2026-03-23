import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "metrics.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_calls (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT NOT NULL,
            agent_id    TEXT NOT NULL,
            department  TEXT NOT NULL,
            provider    TEXT NOT NULL,
            latency_ms  INTEGER NOT NULL,
            input_tokens  INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            tool_calls  INTEGER DEFAULT 0,
            rag_hits    INTEGER DEFAULT 0,
            rag_avg_score REAL DEFAULT 0.0,
            loop_count  INTEGER DEFAULT 1,
            decision    TEXT DEFAULT '',
            error       TEXT DEFAULT '',
            task_hash   TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tool_calls (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ts         TEXT NOT NULL,
            agent_id   TEXT NOT NULL,
            tool_name  TEXT NOT NULL,
            latency_ms INTEGER NOT NULL,
            success    INTEGER NOT NULL,
            error      TEXT DEFAULT ''
        )
    """)
    conn.commit()
    return conn


class AgentCallMetric:
    def __init__(self, agent_id: str, department: str, provider: str):
        self.agent_id = agent_id
        self.department = department
        self.provider = provider
        self.ts = datetime.utcnow().isoformat()
        self.latency_ms = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.tool_calls = 0
        self.rag_hits = 0
        self.rag_avg_score = 0.0
        self.loop_count = 1
        self.decision = ""
        self.error = ""
        self.task_hash = ""
        self._start = time.monotonic()

    def stop(self):
        self.latency_ms = int((time.monotonic() - self._start) * 1000)

    def save(self):
        conn = _get_conn()
        conn.execute("""
            INSERT INTO agent_calls
            (ts, agent_id, department, provider, latency_ms,
             input_tokens, output_tokens, tool_calls, rag_hits,
             rag_avg_score, loop_count, decision, error, task_hash)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            self.ts, self.agent_id, self.department, self.provider,
            self.latency_ms, self.input_tokens, self.output_tokens,
            self.tool_calls, self.rag_hits, self.rag_avg_score,
            self.loop_count, self.decision, self.error, self.task_hash
        ))
        conn.commit()
        conn.close()


@contextmanager
def record_tool(agent_id: str, tool_name: str):
    start = time.monotonic()
    error = ""
    try:
        yield
    except Exception as e:
        error = str(e)
        raise
    finally:
        latency = int((time.monotonic() - start) * 1000)
        try:
            conn = _get_conn()
            conn.execute("""
                INSERT INTO tool_calls (ts, agent_id, tool_name, latency_ms, success, error)
                VALUES (?,?,?,?,?,?)
            """, (datetime.utcnow().isoformat(), agent_id, tool_name,
                  latency, 1 if not error else 0, error))
            conn.commit()
            conn.close()
        except Exception:
            pass


def summary(hours: int = 24) -> dict:
    conn = _get_conn()
    cutoff = datetime.utcnow().replace(microsecond=0).isoformat()

    rows = conn.execute("""
        SELECT agent_id, department, provider,
               COUNT(*) as calls,
               AVG(latency_ms) as avg_latency,
               SUM(input_tokens + output_tokens) as total_tokens,
               SUM(tool_calls) as total_tools,
               AVG(rag_avg_score) as avg_rag,
               SUM(CASE WHEN error != '' THEN 1 ELSE 0 END) as errors
        FROM agent_calls
        WHERE ts >= datetime('now', ?)
        GROUP BY agent_id
        ORDER BY calls DESC
    """, (f"-{hours} hours",)).fetchall()

    tool_rows = conn.execute("""
        SELECT tool_name, COUNT(*) as calls,
               AVG(latency_ms) as avg_latency,
               SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) as errors
        FROM tool_calls
        WHERE ts >= datetime('now', ?)
        GROUP BY tool_name
        ORDER BY calls DESC
    """, (f"-{hours} hours",)).fetchall()

    conn.close()
    return {
        "period_hours": hours,
        "agents": [dict(r) for r in rows],
        "tools": [dict(r) for r in tool_rows],
    }


def agent_history(agent_id: str, limit: int = 50) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT * FROM agent_calls WHERE agent_id = ?
        ORDER BY ts DESC LIMIT ?
    """, (agent_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def export_jsonl(path: str, hours: int = 0):
    conn = _get_conn()
    query = "SELECT * FROM agent_calls"
    if hours:
        rows = conn.execute(query + " WHERE ts >= datetime('now', ?)",
                            (f"-{hours} hours",)).fetchall()
    else:
        rows = conn.execute(query).fetchall()
    conn.close()
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(dict(r), ensure_ascii=False) + "\n")
    return len(rows)
