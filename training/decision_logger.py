import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "decisions.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts           TEXT NOT NULL,
            agent_id     TEXT NOT NULL,
            department   TEXT NOT NULL,
            task         TEXT NOT NULL,
            agent_output TEXT NOT NULL,
            decision     TEXT DEFAULT '',
            rag_context  TEXT DEFAULT '',
            human_label  TEXT DEFAULT '',
            human_note   TEXT DEFAULT '',
            quality      INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def log_decision(agent_id: str, department: str, task: str,
                 output: str, decision: str = "", rag_context: str = "") -> int:
    conn = _get_conn()
    cursor = conn.execute("""
        INSERT INTO decisions
        (ts, agent_id, department, task, agent_output, decision, rag_context)
        VALUES (?,?,?,?,?,?,?)
    """, (
        datetime.utcnow().isoformat(), agent_id, department,
        task[:3000], output[:6000], decision, rag_context[:2000]
    ))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def label(decision_id: int, human_label: str, note: str = "", quality: int = 1):
    conn = _get_conn()
    conn.execute("""
        UPDATE decisions
        SET human_label = ?, human_note = ?, quality = ?
        WHERE id = ?
    """, (human_label, note, quality, decision_id))
    conn.commit()
    conn.close()


def export_finetune_jsonl(output_path: str, labeled_only: bool = True,
                          min_quality: int = 1) -> int:
    conn = _get_conn()
    if labeled_only:
        rows = conn.execute("""
            SELECT * FROM decisions
            WHERE human_label != '' AND quality >= ?
            ORDER BY ts
        """, (min_quality,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM decisions ORDER BY ts").fetchall()
    conn.close()

    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for row in rows:
            r = dict(row)
            system_msg = (
                f"You are {r['agent_id']} in the {r['department']} department "
                f"of BankAI. Respond professionally and accurately."
            )
            if r.get("rag_context"):
                system_msg += f"\n\nContext:\n{r['rag_context']}"

            record = {
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": r["task"]},
                    {"role": "assistant", "content": r["human_label"] or r["agent_output"]},
                ]
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    return count


def export_dpo_jsonl(output_path: str) -> int:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT * FROM decisions
        WHERE human_label != '' AND agent_output != human_label
        ORDER BY ts
    """).fetchall()
    conn.close()

    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for row in rows:
            r = dict(row)
            record = {
                "prompt": r["task"],
                "chosen": r["human_label"],
                "rejected": r["agent_output"],
                "agent_id": r["agent_id"],
                "department": r["department"],
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    return count


def stats() -> dict:
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    labeled = conn.execute(
        "SELECT COUNT(*) FROM decisions WHERE human_label != ''"
    ).fetchone()[0]
    by_dept = conn.execute("""
        SELECT department, COUNT(*) as cnt FROM decisions
        GROUP BY department ORDER BY cnt DESC
    """).fetchall()
    conn.close()
    return {
        "total": total,
        "labeled": labeled,
        "unlabeled": total - labeled,
        "by_department": [dict(r) for r in by_dept],
    }


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"

    if cmd == "stats":
        s = stats()
        print(f"Toplam: {s['total']}  Etiketli: {s['labeled']}  Etiketlenmemiş: {s['unlabeled']}")
        for r in s["by_department"]:
            print(f"  {r['department']}: {r['cnt']}")

    elif cmd == "export" and len(sys.argv) > 2:
        n = export_finetune_jsonl(sys.argv[2])
        print(f"{n} kayıt JSONL formatında dışa aktarıldı: {sys.argv[2]}")

    elif cmd == "export-dpo" and len(sys.argv) > 2:
        n = export_dpo_jsonl(sys.argv[2])
        print(f"{n} DPO çifti dışa aktarıldı: {sys.argv[2]}")
