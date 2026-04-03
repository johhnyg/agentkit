"""
OutcomeTracker — Link every decision to its result.

Your agent makes decisions. Those decisions have outcomes.
This module tracks the full lifecycle: decision → outcome → lesson.
Enables retrospective analysis of what conditions led to wins vs losses.

Usage:
    from agentkit import OutcomeTracker

    tracker = OutcomeTracker("outcomes.json")

    # Record the decision
    decision_id = tracker.record_decision(
        action="BUY",
        reasoning="Strong signal score, low fear",
        context={"signal": 6, "fear_greed": 25}
    )

    # Later, record what happened
    tracker.record_outcome(
        decision_id=decision_id,
        result="WIN",
        pnl=15.30,
        learned="Low F&G entries during signal alignment work"
    )

    # Analyze patterns
    stats = tracker.stats_by_condition("fear_greed", buckets=[0, 25, 50, 75, 100])
"""
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List


class OutcomeTracker:
    """
    Tracks decisions and their outcomes for pattern analysis.

    Each decision gets a unique ID. Outcomes are linked back
    to decisions. Enables analysis like "what's my win rate
    when fear_greed < 25?"
    """

    def __init__(self, storage_path: str = "outcomes.json", max_entries: int = 500):
        self.path = storage_path
        self.max_entries = max_entries
        self._data = self._load()

    def _load(self) -> dict:
        try:
            with open(self.path) as f:
                return json.load(f)
        except Exception:
            return {
                "decisions": [],
                "total_decisions": 0,
                "total_outcomes": 0
            }

    def _save(self):
        # Trim old entries if over limit
        if len(self._data["decisions"]) > self.max_entries:
            self._data["decisions"] = self._data["decisions"][-self.max_entries:]
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def record_decision(
        self,
        action: str,
        reasoning: str,
        context: dict,
        confidence: float = 1.0
    ) -> str:
        """
        Record a decision before executing it.

        Args:
            action: What the agent decided to do (BUY, SELL, HOLD, etc.)
            reasoning: Why the agent made this decision
            context: Current conditions at decision time
            confidence: Agent's confidence level 0.0-1.0

        Returns:
            decision_id: Unique ID to link outcome later
        """
        decision_id = str(uuid.uuid4())[:8]
        ts = time.time()

        entry = {
            "id": decision_id,
            "action": action,
            "reasoning": reasoning,
            "context": context,
            "confidence": confidence,
            "ts": ts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "outcome": None,
            "result": None,
            "pnl": None,
            "learned": None,
            "outcome_ts": None
        }

        self._data["decisions"].append(entry)
        self._data["total_decisions"] = self._data.get("total_decisions", 0) + 1
        self._save()
        return decision_id

    def record_outcome(
        self,
        decision_id: str,
        result: str,
        pnl: float = 0.0,
        learned: Optional[str] = None
    ) -> bool:
        """
        Record the outcome of a previous decision.

        Args:
            decision_id: ID from record_decision()
            result: "WIN", "LOSS", or "NEUTRAL"
            pnl: Profit/loss from this decision
            learned: Optional lesson learned

        Returns:
            True if decision found and updated
        """
        for decision in self._data["decisions"]:
            if decision["id"] == decision_id:
                decision["outcome"] = "recorded"
                decision["result"] = result
                decision["pnl"] = pnl
                decision["learned"] = learned
                decision["outcome_ts"] = time.time()
                self._data["total_outcomes"] = self._data.get("total_outcomes", 0) + 1
                self._save()
                return True
        return False

    def get_pending(self) -> List[dict]:
        """Get decisions without outcomes yet."""
        return [d for d in self._data["decisions"] if d.get("outcome") is None]

    def get_recent(self, n: int = 10) -> List[dict]:
        """Get N most recent decisions with outcomes."""
        with_outcomes = [d for d in self._data["decisions"] if d.get("outcome")]
        return sorted(with_outcomes, key=lambda x: x.get("ts", 0), reverse=True)[:n]

    def stats_by_condition(
        self,
        condition_key: str,
        buckets: Optional[List[float]] = None
    ) -> dict:
        """
        Analyze win rate by a condition dimension.

        Args:
            condition_key: Key in context dict (e.g., "fear_greed")
            buckets: Optional bucket boundaries for numeric values

        Returns:
            Dict with win rates per bucket/value
        """
        results = {}
        with_outcomes = [d for d in self._data["decisions"] if d.get("result")]

        for decision in with_outcomes:
            value = decision.get("context", {}).get(condition_key)
            if value is None:
                continue

            # Bucket numeric values
            if buckets and isinstance(value, (int, float)):
                bucket_label = None
                for i, threshold in enumerate(buckets[:-1]):
                    if value < buckets[i + 1]:
                        bucket_label = f"{threshold}-{buckets[i+1]}"
                        break
                if bucket_label is None:
                    bucket_label = f"{buckets[-1]}+"
                key = bucket_label
            else:
                key = str(value)

            if key not in results:
                results[key] = {"wins": 0, "losses": 0, "total_pnl": 0.0}

            if decision["result"] == "WIN":
                results[key]["wins"] += 1
            elif decision["result"] == "LOSS":
                results[key]["losses"] += 1
            results[key]["total_pnl"] += decision.get("pnl", 0)

        # Calculate win rates
        for key in results:
            total = results[key]["wins"] + results[key]["losses"]
            results[key]["win_rate"] = (
                round(results[key]["wins"] / total * 100, 1) if total > 0 else 0
            )
            results[key]["total_trades"] = total

        return results

    def stats(self) -> dict:
        """Overall outcome statistics."""
        with_outcomes = [d for d in self._data["decisions"] if d.get("result")]
        wins = sum(1 for d in with_outcomes if d["result"] == "WIN")
        losses = sum(1 for d in with_outcomes if d["result"] == "LOSS")
        total_pnl = sum(d.get("pnl", 0) for d in with_outcomes)

        return {
            "total_decisions": self._data.get("total_decisions", 0),
            "total_outcomes": len(with_outcomes),
            "pending": len(self.get_pending()),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0,
            "total_pnl": round(total_pnl, 2)
        }
