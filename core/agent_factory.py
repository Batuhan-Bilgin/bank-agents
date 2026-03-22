"""
AgentFactory — loads agents from agents_config.json and instantiates BaseAgent objects.
Provides lookup by ID, role, department, or specialization keyword.
"""

import json
import re
from pathlib import Path
from functools import lru_cache
from typing import Optional

import os
from dotenv import load_dotenv
load_dotenv()

from core.base_agent import BaseAgent

CONFIG_PATH = Path(__file__).parent.parent / "agents_config.json"


def _agent_class():
    """Return the right agent class based on PROVIDER env var."""
    provider = os.environ.get("PROVIDER", "anthropic").lower()
    if provider == "groq":
        from core.groq_agent import GroqBaseAgent
        return GroqBaseAgent
    return BaseAgent


class AgentFactory:
    """
    Singleton-style factory that reads agents_config.json once and
    builds / caches agent instances on demand.
    """

    def __init__(self, config_path: Path = CONFIG_PATH):
        with open(config_path, encoding="utf-8") as f:
            raw = json.load(f)

        self._configs: dict[str, dict] = {a["id"]: a for a in raw["agents"]}
        self._instances: dict[str, BaseAgent] = {}

        # Build indexes for fast lookup
        self._by_role: dict[str, list[str]] = {}
        self._by_department: dict[str, list[str]] = {}

        for cfg in raw["agents"]:
            role_key = cfg["role"].lower()
            dept_key = cfg["department"].lower()
            self._by_role.setdefault(role_key, []).append(cfg["id"])
            self._by_department.setdefault(dept_key, []).append(cfg["id"])

        self.total = len(self._configs)

    # ------------------------------------------------------------------
    # Creation / retrieval
    # ------------------------------------------------------------------

    def get(self, agent_id: str) -> BaseAgent:
        """Get (or create) an agent by its unique ID."""
        if agent_id not in self._instances:
            cfg = self._configs.get(agent_id)
            if cfg is None:
                raise ValueError(f"Agent '{agent_id}' not found. Use list_agents() to see all IDs.")
            self._instances[agent_id] = _agent_class()(cfg)
        return self._instances[agent_id]

    def get_by_role(self, role_keyword: str) -> list[BaseAgent]:
        """Find agents whose role contains the given keyword (case-insensitive)."""
        kw = role_keyword.lower()
        matches = []
        for role, ids in self._by_role.items():
            if kw in role:
                matches.extend(ids)
        return [self.get(aid) for aid in matches]

    def get_by_department(self, department: str) -> list[BaseAgent]:
        """Get all agents in a department."""
        dept_key = department.lower()
        ids = self._by_department.get(dept_key, [])
        return [self.get(aid) for aid in ids]

    def best_agent_for(self, task_description: str) -> BaseAgent:
        """
        Simple keyword-based routing to find the most relevant agent.
        Returns the first strong match, or the general inquiry agent as fallback.
        """
        task_lower = task_description.lower()

        routing_map = [
            # (keywords, department or agent_id)
            (["fraud", "scam", "suspicious transaction", "card fraud"],       "fraud detection"),
            (["aml", "money laundering", "suspicious activity", "str", "ctr"], "aml/kyc"),
            (["sanctions", "ofac", "blocked", "blacklist"],                   "aml/kyc"),
            (["kyc", "identity", "verification", "onboarding document"],      "aml/kyc"),
            (["mortgage", "housing loan", "konut kredisi", "bireysel kredi"], "retail banking"),
            (["sme", "kobi", "small business", "trade finance"],              "corporate & sme banking"),
            (["credit", "loan", "scoring", "npl", "default", "collateral"],   "credit risk"),
            (["liquidity", "lcr", "nsfr", "cash flow", "funding"],            "treasury & liquidity"),
            (["forex", "fx rate", "fx forward", "currency", "exchange rate", "döviz", "kur"], "treasury & liquidity"),
            (["market risk", "var", "trading", "derivatives", "hedging"],     "risk management"),
            (["operational risk", "rcsa", "kri", "loss event"],               "risk management"),
            (["capital", "cet1", "rwa", "basel", "icaap"],                    "regulatory compliance"),
            (["gdpr", "kvkk", "privacy", "data subject", "dsar"],             "regulatory compliance"),
            (["regulatory report", "corep", "finrep", "bddk report"],         "regulatory compliance"),
            (["data quality", "reconciliation", "dq score", "lineage"],       "data quality"),
            (["payment", "eft", "fast", "wire transfer", "swift"],            "operations & process"),
            (["investment", "portfolio", "wealth", "asset management"],       "investment & wealth"),
            (["complaint", "şikayet", "unhappy", "dissatisfied"],             "customer service"),
            (["account", "balance", "statement", "müşteri"],                  "customer service"),
            (["analytics", "dashboard", "kpi", "profitability", "report generation"], "analytics & reporting"),
            (["cybersecurity", "cyber incident", "hack", "breach", "malware", "ransomware", "phishing", "siber"], "it & cybersecurity"),
            (["hr", "employee", "training", "performance review"],            "hr & performance"),
        ]

        def _matches(kw: str, text: str) -> bool:
            """Word-boundary match for short keywords (≤4 chars), substring for longer ones."""
            if len(kw) <= 4:
                return bool(re.search(r'\b' + re.escape(kw) + r'\b', text))
            return kw in text

        for keywords, target in routing_map:
            if any(_matches(kw, task_lower) for kw in keywords):
                dept_key = target.lower()
                ids = self._by_department.get(dept_key, [])
                if ids:
                    return self.get(ids[0])  # return first agent in that department

        # Fallback: customer inquiry agent
        return self.get("customer_inquiry_agent_027")

    # ------------------------------------------------------------------
    # Listing helpers
    # ------------------------------------------------------------------

    def list_agents(self, department: str | None = None) -> list[dict]:
        """List all agent summaries, optionally filtered by department."""
        results = []
        for cfg in self._configs.values():
            if department and cfg["department"].lower() != department.lower():
                continue
            results.append({
                "id": cfg["id"],
                "role": cfg["role"],
                "department": cfg["department"],
                "authority_level": cfg["authority_level"],
                "tool_count": len(cfg.get("tools", []))
            })
        return results

    def list_departments(self) -> list[str]:
        return sorted(set(cfg["department"] for cfg in self._configs.values()))

    def stats(self) -> dict:
        by_dept: dict[str, int] = {}
        by_level: dict[int, int] = {}
        for cfg in self._configs.values():
            by_dept[cfg["department"]] = by_dept.get(cfg["department"], 0) + 1
            lvl = cfg["authority_level"]
            by_level[lvl] = by_level.get(lvl, 0) + 1
        return {
            "total_agents": self.total,
            "departments": len(by_dept),
            "by_department": dict(sorted(by_dept.items())),
            "by_authority_level": dict(sorted(by_level.items())),
            "cached_instances": len(self._instances)
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_factory: AgentFactory | None = None


def get_factory() -> AgentFactory:
    global _factory
    if _factory is None:
        _factory = AgentFactory()
    return _factory
