"""
SelfMetrics — Agent performance tracking.

Your agent needs to know how it's performing. This module
tracks actions, outcomes, and calculates performance metrics
like win rate, Sharpe ratio, and condition analysis.

Usage:
    from agentkit import SelfMetrics

    metrics = SelfMetrics("metrics.json")

    # Record every action
    metrics.record_action(
        action="BUY",
        size=50.0,
        context={"signal": 5, "regime": "normal"}
    )

    # Record outcomes
    metrics.record_outcome(pnl=12.50, fees=0.50)

    # Get performance report
    report = metrics.report()
    print(f"Win rate: {report['win_rate']}%")
    print(f"Sharpe: {report['sharpe_ratio']}")
"""
import json
import time
import math
from datetime import datetime, timezone
from typing import Optional, List
from collections import defaultdict


class SelfMetrics:
    """
    Comprehensive agent performance tracking.

    Tracks:
    - Actions taken and their outcomes
    - Win/loss rate
    - P&L and fees
    - Performance by condition
    - Risk-adjusted returns (Sharpe ratio)
    """

    def __init__(self, storage_path: str = "metrics.json"):
        self.path = storage_path
        self._data = self._load()
        self._pending_action = None

    def _load(self) -> dict:
        try:
            with open(self.path) as f:
                return json.load(f)
        except Exception:
            return {
                "actions": [],
                "total_actions": 0,
                "total_pnl": 0.0,
                "total_fees": 0.0,
                "wins": 0,
                "losses": 0,
                "returns": [],
                "by_condition": {}
            }

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def record_action(
        self,
        action: str,
        size: float,
        context: Optional[dict] = None,
        notes: Optional[str] = None
    ) -> dict:
        """
        Record an action taken by the agent.

        Args:
            action: Action type (BUY, SELL, HOLD, etc.)
            size: Size of the action (dollars, units, etc.)
            context: Conditions at time of action
            notes: Optional notes

        Returns:
            The recorded action entry
        """
        ts = time.time()
        entry = {
            "action": action,
            "size": size,
            "context": context or {},
            "notes": notes,
            "ts": ts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "outcome": None
        }

        self._pending_action = entry
        self._data["actions"].append(entry)
        self._data["total_actions"] = self._data.get("total_actions", 0) + 1
        self._save()
        return entry

    def record_outcome(
        self,
        pnl: float,
        fees: float = 0.0,
        hold_hours: Optional[float] = None
    ) -> dict:
        """
        Record the outcome of the last action.

        Args:
            pnl: Profit/loss (after fees)
            fees: Fees paid
            hold_hours: How long position was held

        Returns:
            Updated metrics summary
        """
        net_pnl = pnl - fees
        result = "WIN" if net_pnl > 0 else "LOSS" if net_pnl < 0 else "NEUTRAL"

        # Update last action
        if self._data["actions"]:
            last = self._data["actions"][-1]
            last["outcome"] = {
                "pnl": pnl,
                "fees": fees,
                "net_pnl": net_pnl,
                "result": result,
                "hold_hours": hold_hours,
                "closed_at": datetime.now(timezone.utc).isoformat()
            }

            # Track by condition
            for key, value in last.get("context", {}).items():
                cond_key = f"{key}:{value}"
                if cond_key not in self._data["by_condition"]:
                    self._data["by_condition"][cond_key] = {
                        "wins": 0, "losses": 0, "total_pnl": 0.0
                    }
                self._data["by_condition"][cond_key]["total_pnl"] += net_pnl
                if result == "WIN":
                    self._data["by_condition"][cond_key]["wins"] += 1
                elif result == "LOSS":
                    self._data["by_condition"][cond_key]["losses"] += 1

        # Update totals
        self._data["total_pnl"] = self._data.get("total_pnl", 0) + net_pnl
        self._data["total_fees"] = self._data.get("total_fees", 0) + fees

        if result == "WIN":
            self._data["wins"] = self._data.get("wins", 0) + 1
        elif result == "LOSS":
            self._data["losses"] = self._data.get("losses", 0) + 1

        # Track returns for Sharpe calculation
        self._data.setdefault("returns", []).append(net_pnl)

        self._pending_action = None
        self._save()

        return {
            "result": result,
            "net_pnl": net_pnl,
            "total_pnl": self._data["total_pnl"],
            "win_rate": self._calculate_win_rate()
        }

    def _calculate_win_rate(self) -> float:
        """Calculate win rate percentage."""
        wins = self._data.get("wins", 0)
        losses = self._data.get("losses", 0)
        total = wins + losses
        return round(wins / total * 100, 1) if total > 0 else 0.0

    def _calculate_sharpe(self) -> Optional[float]:
        """
        Calculate Sharpe ratio from returns.
        Assumes risk-free rate of 0 for simplicity.
        """
        returns = self._data.get("returns", [])
        if len(returns) < 10:
            return None

        mean_return = sum(returns) / len(returns)
        if mean_return == 0:
            return 0.0

        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return 0.0

        # Annualized (assuming daily returns)
        return round(mean_return / std_dev * math.sqrt(252), 2)

    def _calculate_avg_hold(self) -> Optional[float]:
        """Calculate average hold time in hours."""
        hold_times = []
        for action in self._data.get("actions", []):
            outcome = action.get("outcome", {})
            if outcome and outcome.get("hold_hours"):
                hold_times.append(outcome["hold_hours"])

        if not hold_times:
            return None
        return round(sum(hold_times) / len(hold_times), 1)

    def _find_best_condition(self) -> Optional[str]:
        """Find condition with best win rate (min 3 trades)."""
        best = None
        best_rate = 0

        for cond, stats in self._data.get("by_condition", {}).items():
            total = stats["wins"] + stats["losses"]
            if total >= 3:
                rate = stats["wins"] / total
                if rate > best_rate:
                    best_rate = rate
                    best = cond

        return best

    def report(self) -> dict:
        """
        Generate comprehensive performance report.

        Returns:
            Dict with all performance metrics
        """
        return {
            "total_actions": self._data.get("total_actions", 0),
            "wins": self._data.get("wins", 0),
            "losses": self._data.get("losses", 0),
            "win_rate": self._calculate_win_rate(),
            "total_pnl": round(self._data.get("total_pnl", 0), 2),
            "total_fees": round(self._data.get("total_fees", 0), 2),
            "net_pnl": round(
                self._data.get("total_pnl", 0) - self._data.get("total_fees", 0), 2
            ),
            "sharpe_ratio": self._calculate_sharpe(),
            "avg_hold_hours": self._calculate_avg_hold(),
            "best_condition": self._find_best_condition(),
            "conditions_tracked": len(self._data.get("by_condition", {}))
        }

    def get_condition_stats(self) -> dict:
        """Get performance breakdown by condition."""
        result = {}
        for cond, stats in self._data.get("by_condition", {}).items():
            total = stats["wins"] + stats["losses"]
            result[cond] = {
                "wins": stats["wins"],
                "losses": stats["losses"],
                "total": total,
                "win_rate": round(stats["wins"] / total * 100, 1) if total > 0 else 0,
                "total_pnl": round(stats["total_pnl"], 2)
            }
        return result

    def to_prompt_block(self) -> str:
        """Format metrics for injection into LLM prompt."""
        report = self.report()
        best = report.get("best_condition")

        block = (
            f"\nAGENT PERFORMANCE METRICS:\n"
            f"Win rate: {report['win_rate']}% "
            f"({report['wins']}W/{report['losses']}L)\n"
            f"Net P&L: ${report['net_pnl']}\n"
        )

        if report.get("sharpe_ratio") is not None:
            block += f"Sharpe ratio: {report['sharpe_ratio']}\n"

        if report.get("avg_hold_hours") is not None:
            block += f"Avg hold: {report['avg_hold_hours']}h\n"

        if best:
            block += f"Best condition: {best}\n"

        return block

    def stats(self) -> dict:
        """Alias for report()."""
        return self.report()
