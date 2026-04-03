"""
ContradictionDetector — Surface conflicts before your agent acts.

When multiple signals drive an agent's decision, they often
disagree. This module detects those contradictions, scores
the conflict level, and tells your agent exactly what
disagrees and why — before it acts.

Usage:
    from agentkit import ContradictionDetector

    detector = ContradictionDetector()
    detector.add_rule(
        name="signal_vs_sentiment",
        severity="HIGH",
        check=lambda ctx: (
            ctx.get("signal_score", 0) > 3
            and ctx.get("sentiment", 0) < 30
        ),
        detail=lambda ctx: (
            f"Signal bullish ({ctx['signal_score']}) "
            f"but sentiment bearish ({ctx['sentiment']})"
        )
    )

    report = detector.analyze(context, proposed_action="BUY")
    print(report["level"])  # CONSENSUS / CONFLICT / MAJOR_CONFLICT
    prompt += report["prompt_block"]
"""
import json
import os
import time
from datetime import datetime, timezone
from typing import Callable, Optional


class ContradictionDetector:
    """
    Detects signal conflicts before agent decisions.

    Contradiction score 0-10:
      0     = CONSENSUS (all signals agree)
      1-2   = MINOR_CONFLICT
      3-5   = CONFLICT
      6-10  = MAJOR_CONFLICT
    """

    SEVERITY_WEIGHTS = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

    def __init__(self, storage_path: Optional[str] = None):
        self.path = storage_path
        self._rules = []

    def add_rule(
        self,
        name: str,
        severity: str,
        check: Callable[[dict], bool],
        detail: Callable[[dict], str]
    ):
        """
        Add a contradiction rule.

        Args:
            name:     Rule identifier
            severity: HIGH / MEDIUM / LOW
            check:    Function(context) -> bool
                      Returns True when contradiction exists
            detail:   Function(context) -> str
                      Returns human-readable description
        """
        self._rules.append({
            "name": name,
            "severity": severity,
            "check": check,
            "detail": detail
        })

    def analyze(
        self,
        context: dict,
        proposed_action: str = ""
    ) -> dict:
        """
        Analyze context for contradictions.

        Args:
            context:         Current agent context/signals
            proposed_action: What the agent plans to do

        Returns:
            contradiction_score: 0-10
            level:  CONSENSUS/MINOR_CONFLICT/CONFLICT/MAJOR_CONFLICT
            conflicts:    List of found contradictions
            agreements:   List of signals that agree
            prompt_block: Ready to inject into LLM prompt
        """
        conflicts = []
        agreements = []

        for rule in self._rules:
            try:
                if rule["check"](context):
                    conflicts.append({
                        "name": rule["name"],
                        "severity": rule["severity"],
                        "detail": rule["detail"](context)
                    })
                else:
                    agreements.append(rule["name"])
            except Exception:
                pass

        raw = sum(
            self.SEVERITY_WEIGHTS.get(c["severity"], 1)
            for c in conflicts
        )
        score = min(10, raw)

        if score == 0:
            level = "CONSENSUS"
        elif score <= 2:
            level = "MINOR_CONFLICT"
        elif score <= 5:
            level = "CONFLICT"
        else:
            level = "MAJOR_CONFLICT"

        block = (
            f"\nCONTRADICTION REPORT:\n"
            f"Level: {level} (score: {score}/10)\n"
        )
        if conflicts:
            block += "Conflicts:\n"
            for c in conflicts:
                block += f"  [{c['severity']}] {c['detail']}\n"
        if agreements:
            block += f"Agreements: {', '.join(agreements)}\n"
        if level == "MAJOR_CONFLICT":
            block += (
                "\nWARNING: Major conflict. Address each "
                "conflict before proceeding.\n"
            )

        return {
            "contradiction_score": score,
            "level": level,
            "conflicts": conflicts,
            "agreements": agreements,
            "conflict_count": len(conflicts),
            "agreement_count": len(agreements),
            "prompt_block": block,
            "ts": datetime.now(timezone.utc).isoformat()
        }
