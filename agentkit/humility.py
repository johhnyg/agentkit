"""
EpistemicHumility — Agents that know what they don't know.

Before your agent acts, ask: has it seen conditions like
these before? If not, it should be cautious. If yes,
it can act with full confidence.

This module tracks experience across condition dimensions
and returns a familiarity assessment with a size modifier
your agent can apply to any action.

Usage:
    from agentkit import EpistemicHumility

    humility = EpistemicHumility("knowledge.json")

    assessment = humility.assess({
        "market_regime": "bear",
        "signal_strength": "weak",
        "volatility": "high"
    })

    print(assessment["familiarity"])  # KNOWN / RARE / UNKNOWN
    print(assessment["size_modifier"])  # 1.0 / 0.75 / 0.5
    prompt += assessment["prompt_block"]
"""
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional


class EpistemicHumility:
    """
    Tracks agent experience across condition combinations.

    KNOWN   (3+ experiences) → full confidence, 1.0x modifier
    RARE    (1-2 experiences) → cautious, 0.75x modifier
    UNKNOWN (0 experiences)  → very cautious, 0.5x modifier
    """

    KNOWN_THRESHOLD = 3
    RARE_THRESHOLD = 1

    def __init__(
        self,
        storage_path: str = "knowledge.json",
        known_threshold: int = 3,
        rare_threshold: int = 1
    ):
        self.path = storage_path
        self.KNOWN_THRESHOLD = known_threshold
        self.RARE_THRESHOLD = rare_threshold
        self._data = self._load()

    def _load(self) -> dict:
        try:
            with open(self.path) as f:
                return json.load(f)
        except Exception:
            return {
                "conditions": {},
                "total_unknown": 0,
                "last_updated": ""
            }

    def _save(self):
        self._data["last_updated"] = (
            datetime.now(timezone.utc).isoformat())
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def _make_key(self, conditions: dict) -> str:
        """Build a condition fingerprint from context dict."""
        parts = []
        for k in sorted(conditions.keys()):
            parts.append(f"{k}:{conditions[k]}")
        return "|".join(parts)

    def assess(self, conditions: dict) -> dict:
        """
        Assess familiarity with given conditions.

        Args:
            conditions: dict of condition dimensions
                        e.g. {"regime": "bear", "vol": "high"}

        Returns:
            familiarity:   KNOWN / RARE / UNKNOWN
            experience:    N times seen these conditions
            size_modifier: 1.0 / 0.75 / 0.5
            warning:       Human-readable warning or None
            prompt_block:  Ready to inject into LLM prompt
            condition_key: The fingerprint used
        """
        key = self._make_key(conditions)
        seen = self._data["conditions"].get(key, 0)

        if seen >= self.KNOWN_THRESHOLD:
            familiarity = "KNOWN"
            modifier = 1.0
            warning = None
        elif seen >= self.RARE_THRESHOLD:
            familiarity = "RARE"
            modifier = 0.75
            warning = (
                f"Seen conditions like these only {seen} "
                f"time(s). Recommend caution."
            )
        else:
            familiarity = "UNKNOWN"
            modifier = 0.5
            self._data["total_unknown"] = (
                self._data.get("total_unknown", 0) + 1)
            self._save()
            warning = (
                "Never operated in conditions like these. "
                "Recommend minimum action size."
            )

        block = (
            f"\nEPISTEMIC ASSESSMENT:\n"
            f"Familiarity: {familiarity} "
            f"({seen} prior experiences)\n"
        )
        if warning:
            block += f"Warning: {warning}\n"

        return {
            "familiarity": familiarity,
            "experience": seen,
            "size_modifier": modifier,
            "warning": warning,
            "prompt_block": block,
            "condition_key": key
        }

    def record(self, conditions: dict):
        """
        Record that the agent operated in these conditions.
        Call after every significant action.
        """
        key = self._make_key(conditions)
        self._data["conditions"][key] = (
            self._data["conditions"].get(key, 0) + 1)
        self._save()

    def stats(self) -> dict:
        conds = self._data.get("conditions", {})
        known = sum(1 for v in conds.values()
                    if v >= self.KNOWN_THRESHOLD)
        rare = sum(1 for v in conds.values()
                   if self.RARE_THRESHOLD <= v
                   < self.KNOWN_THRESHOLD)
        return {
            "total_mapped": len(conds),
            "known": known,
            "rare": rare,
            "unknown_hits": self._data.get("total_unknown", 0),
        }
