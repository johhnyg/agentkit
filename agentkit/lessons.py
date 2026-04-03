"""
LessonsMemory — Auto-ranks learnings from agent outcomes.

Agents make decisions. Decisions have outcomes. Outcomes
teach lessons. This module captures, ranks, and surfaces
the most impactful lessons so your agent reads its own
history before every decision.

Usage:
    from agentkit import LessonsMemory

    memory = LessonsMemory("lessons.json")
    memory.record(
        text="F&G below 15 with negative signals = bad entry",
        pnl_impact=-12.50,
        conditions={"fear_greed": 12, "signal_score": -2}
    )
    top = memory.get_top(5)
    prompt += memory.to_prompt_block(5)
"""
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional


class LessonsMemory:
    """
    Captures agent outcomes as ranked lessons.
    Lessons are ranked by P&L impact * recency weight.
    Older lessons decay. High-impact lessons persist.
    """

    def __init__(self, storage_path: str = "lessons.json"):
        self.path = storage_path
        self._data = self._load()

    def _load(self) -> dict:
        try:
            with open(self.path) as f:
                return json.load(f)
        except Exception:
            return {"lessons": [], "total_recorded": 0}

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def _recency_weight(self, ts: float) -> float:
        age_days = (time.time() - ts) / 86400
        if age_days < 7:
            return 1.0
        if age_days < 30:
            return 0.7
        return 0.3

    def _score(self, lesson: dict) -> float:
        impact = abs(lesson.get("pnl_impact", 0))
        weight = self._recency_weight(lesson.get("ts", 0))
        freq = lesson.get("frequency", 1)
        return impact * weight * (1 + freq * 0.1)

    def record(
        self,
        text: str,
        pnl_impact: float = 0.0,
        outcome: str = "WIN",
        conditions: Optional[dict] = None
    ) -> dict:
        """
        Record a lesson from an agent outcome.

        Args:
            text: The lesson in plain English
            pnl_impact: Dollar P&L from this outcome
            outcome: "WIN" or "LOSS"
            conditions: Market conditions at time of decision

        Returns: The recorded lesson entry
        """
        ts = time.time()
        key = text[:60].lower().strip()

        # Deduplicate — same lesson seen again increases frequency
        for lesson in self._data["lessons"]:
            if lesson.get("key") == key:
                lesson["frequency"] = lesson.get("frequency", 1) + 1
                lesson["last_seen"] = ts
                lesson["pnl_impact"] = (
                    lesson["pnl_impact"] + pnl_impact) / 2
                self._save()
                return lesson

        entry = {
            "key": key,
            "text": text,
            "pnl_impact": pnl_impact,
            "outcome": outcome,
            "conditions": conditions or {},
            "ts": ts,
            "frequency": 1,
            "last_seen": ts,
            "added": datetime.now(timezone.utc).isoformat()
        }
        self._data["lessons"].append(entry)
        self._data["total_recorded"] = (
            self._data.get("total_recorded", 0) + 1)
        self._save()
        return entry

    def get_top(self, n: int = 10) -> list:
        """
        Return top N lessons ranked by impact * recency.
        """
        lessons = self._data.get("lessons", [])
        return sorted(lessons, key=self._score, reverse=True)[:n]

    def to_prompt_block(self, n: int = 5) -> str:
        """
        Format top lessons for injection into an LLM prompt.

        Returns a string block ready to append to any prompt.
        """
        top = self.get_top(n)
        if not top:
            return ""
        lines = ["\nLESSONS FROM REAL OUTCOMES (ranked by impact):\n"]
        for i, lesson in enumerate(top, 1):
            sign = "+" if lesson["pnl_impact"] >= 0 else ""
            lines.append(
                f"{i}. {lesson['text']} "
                f"(impact: {sign}${lesson['pnl_impact']:.2f}, "
                f"seen {lesson['frequency']}x)\n"
            )
        return "".join(lines)

    def stats(self) -> dict:
        lessons = self._data.get("lessons", [])
        return {
            "total_lessons": len(lessons),
            "total_recorded": self._data.get("total_recorded", 0),
            "top_lesson": self.get_top(1)[0]["text"]
                          if lessons else None,
        }
