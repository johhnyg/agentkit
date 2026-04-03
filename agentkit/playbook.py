"""
Playbook — Rules that evolve from patterns.

As your agent learns, it discovers patterns. This module
captures those patterns as rules that can be confirmed,
promoted, or demoted based on real outcomes.

Usage:
    from agentkit import Playbook

    playbook = Playbook("playbook.json")

    # Add a rule learned from experience
    playbook.add_rule(
        name="fear_entry",
        trigger="fear_greed < 20 AND signal_score > 3",
        action="size *= 1.5",
        source="LEARNED",
        evidence={"wins": 7, "losses": 2, "avg_pnl": 8.50}
    )

    # Check which rules apply to current context
    applicable = playbook.evaluate(context)

    # Confirm or reject based on outcome
    playbook.confirm_rule("fear_entry", outcome="WIN", pnl=12.0)
"""
import json
import time
from datetime import datetime, timezone
from typing import Optional, List, Callable


class Playbook:
    """
    Self-evolving rule system.

    Rules have states:
    - CANDIDATE: Newly discovered, needs validation
    - CONFIRMED: Validated with 3+ positive outcomes
    - PROVEN: 10+ positive outcomes, high confidence
    - DEMOTED: Poor recent performance
    - RETIRED: Removed from active use

    Rules auto-promote on success and auto-demote on failure.
    """

    STATE_THRESHOLDS = {
        "CONFIRMED": 3,
        "PROVEN": 10
    }

    def __init__(self, storage_path: str = "playbook.json"):
        self.path = storage_path
        self._data = self._load()
        self._evaluators = {}

    def _load(self) -> dict:
        try:
            with open(self.path) as f:
                return json.load(f)
        except Exception:
            return {"rules": [], "version": 1}

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def add_rule(
        self,
        name: str,
        trigger: str,
        action: str,
        source: str = "LEARNED",
        evidence: Optional[dict] = None,
        evaluator: Optional[Callable[[dict], bool]] = None
    ) -> dict:
        """
        Add a new rule to the playbook.

        Args:
            name: Unique rule identifier
            trigger: Human-readable trigger condition
            action: What to do when triggered
            source: LEARNED / MANUAL / INHERITED
            evidence: Initial evidence for the rule
            evaluator: Optional function(context) -> bool

        Returns:
            The created rule entry
        """
        # Check for duplicate
        for rule in self._data["rules"]:
            if rule["name"] == name:
                return rule

        ts = time.time()
        rule = {
            "name": name,
            "trigger": trigger,
            "action": action,
            "source": source,
            "state": "CANDIDATE",
            "evidence": evidence or {},
            "confirmations": 0,
            "rejections": 0,
            "total_pnl": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_applied": None,
            "last_confirmed": None
        }

        self._data["rules"].append(rule)
        self._save()

        if evaluator:
            self._evaluators[name] = evaluator

        return rule

    def register_evaluator(self, name: str, evaluator: Callable[[dict], bool]):
        """Register a function to evaluate if a rule applies."""
        self._evaluators[name] = evaluator

    def evaluate(self, context: dict) -> List[dict]:
        """
        Find all rules that apply to current context.

        Args:
            context: Current conditions

        Returns:
            List of applicable rules (active states only)
        """
        applicable = []
        active_states = ["CANDIDATE", "CONFIRMED", "PROVEN"]

        for rule in self._data["rules"]:
            if rule["state"] not in active_states:
                continue

            # Check if we have an evaluator
            if rule["name"] in self._evaluators:
                try:
                    if self._evaluators[rule["name"]](context):
                        rule["last_applied"] = datetime.now(timezone.utc).isoformat()
                        applicable.append(rule)
                except Exception:
                    pass

        self._save()
        return applicable

    def confirm_rule(self, name: str, outcome: str, pnl: float = 0.0) -> Optional[dict]:
        """
        Record outcome when a rule was applied.

        Args:
            name: Rule name
            outcome: "WIN" or "LOSS"
            pnl: P&L from this application

        Returns:
            Updated rule or None if not found
        """
        for rule in self._data["rules"]:
            if rule["name"] != name:
                continue

            rule["total_pnl"] = rule.get("total_pnl", 0) + pnl

            if outcome == "WIN":
                rule["confirmations"] = rule.get("confirmations", 0) + 1
                rule["last_confirmed"] = datetime.now(timezone.utc).isoformat()

                # Check for promotion
                if rule["state"] == "CANDIDATE" and rule["confirmations"] >= self.STATE_THRESHOLDS["CONFIRMED"]:
                    rule["state"] = "CONFIRMED"
                elif rule["state"] == "CONFIRMED" and rule["confirmations"] >= self.STATE_THRESHOLDS["PROVEN"]:
                    rule["state"] = "PROVEN"
            else:
                rule["rejections"] = rule.get("rejections", 0) + 1

                # Check for demotion
                recent_ratio = rule["rejections"] / max(1, rule["confirmations"])
                if recent_ratio > 0.5 and rule["rejections"] >= 3:
                    if rule["state"] == "PROVEN":
                        rule["state"] = "CONFIRMED"
                    elif rule["state"] == "CONFIRMED":
                        rule["state"] = "DEMOTED"
                    elif rule["state"] == "CANDIDATE":
                        rule["state"] = "RETIRED"

            self._save()
            return rule

        return None

    def get_rule(self, name: str) -> Optional[dict]:
        """Get a specific rule by name."""
        for rule in self._data["rules"]:
            if rule["name"] == name:
                return rule
        return None

    def get_active(self) -> List[dict]:
        """Get all active rules (CANDIDATE, CONFIRMED, PROVEN)."""
        active_states = ["CANDIDATE", "CONFIRMED", "PROVEN"]
        return [r for r in self._data["rules"] if r["state"] in active_states]

    def to_prompt_block(self) -> str:
        """Format active rules for injection into LLM prompt."""
        active = self.get_active()
        if not active:
            return ""

        lines = ["\nACTIVE PLAYBOOK RULES:\n"]
        for rule in sorted(active, key=lambda r: r.get("confirmations", 0), reverse=True):
            conf = rule.get("confirmations", 0)
            rej = rule.get("rejections", 0)
            lines.append(
                f"- [{rule['state']}] {rule['name']}: "
                f"IF {rule['trigger']} THEN {rule['action']} "
                f"({conf}W/{rej}L)\n"
            )
        return "".join(lines)

    def stats(self) -> dict:
        """Playbook statistics."""
        rules = self._data.get("rules", [])
        by_state = {}
        for rule in rules:
            state = rule.get("state", "UNKNOWN")
            by_state[state] = by_state.get(state, 0) + 1

        total_pnl = sum(r.get("total_pnl", 0) for r in rules)

        return {
            "total_rules": len(rules),
            "by_state": by_state,
            "active": len(self.get_active()),
            "total_pnl": round(total_pnl, 2)
        }
