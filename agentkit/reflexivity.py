"""
Reflexivity — Detect when momentum creates its own reality.

Based on Soros reflexivity theory: market participants' biased
views can influence fundamentals, creating self-reinforcing
feedback loops. This module detects those loops and helps
your agent adjust sizing accordingly.

Usage:
    from agentkit import Reflexivity

    reflex = Reflexivity()

    score = reflex.update(
        price=67000,
        volume=1200000,
        sentiment=72,
        momentum_1h=0.8
    )

    print(f"Reflexivity: {score}")  # -7 to +7
    print(f"Stage: {reflex.stage}")  # BUST → NEUTRAL → BOOM

    if reflex.stage in ["LATE_BOOM", "BLOWOFF"]:
        size *= 0.25  # Reduce exposure in euphoria
"""
import json
import time
from datetime import datetime, timezone
from typing import Optional, List
from collections import deque


class Reflexivity:
    """
    Detects self-reinforcing feedback loops in market data.

    Score ranges from -7 (bust) to +7 (boom).

    Stages:
    - BUST (-7 to -5): Capitulation, max fear
    - EARLY_RECOVERY (-4 to -2): Fear fading
    - NEUTRAL (-1 to +1): No clear momentum
    - EARLY_BOOM (+2 to +4): Optimism building
    - LATE_BOOM (+5 to +6): Euphoria, caution advised
    - BLOWOFF (+7): Maximum greed, high reversal risk
    """

    STAGES = {
        (-7, -5): "BUST",
        (-4, -2): "EARLY_RECOVERY",
        (-1, 1): "NEUTRAL",
        (2, 4): "EARLY_BOOM",
        (5, 6): "LATE_BOOM",
        (7, 7): "BLOWOFF"
    }

    SIZE_MODIFIERS = {
        "BUST": 2.0,       # Max opportunity
        "EARLY_RECOVERY": 1.5,
        "NEUTRAL": 1.0,
        "EARLY_BOOM": 1.5,
        "LATE_BOOM": 0.5,
        "BLOWOFF": 0.25    # Max caution
    }

    def __init__(self, storage_path: Optional[str] = None, history_size: int = 24):
        self.path = storage_path
        self.history_size = history_size
        self._data = self._load()
        self._price_history = deque(maxlen=history_size)
        self._volume_history = deque(maxlen=history_size)
        self._sentiment_history = deque(maxlen=history_size)

        # Restore history from saved data
        for entry in self._data.get("history", [])[-history_size:]:
            if "price" in entry:
                self._price_history.append(entry["price"])
            if "volume" in entry:
                self._volume_history.append(entry["volume"])
            if "sentiment" in entry:
                self._sentiment_history.append(entry["sentiment"])

    def _load(self) -> dict:
        if not self.path:
            return {"score": 0, "stage": "NEUTRAL", "history": []}
        try:
            with open(self.path) as f:
                return json.load(f)
        except Exception:
            return {"score": 0, "stage": "NEUTRAL", "history": []}

    def _save(self):
        if self.path:
            # Trim history
            self._data["history"] = self._data.get("history", [])[-self.history_size:]
            with open(self.path, "w") as f:
                json.dump(self._data, f, indent=2)

    def _get_stage(self, score: int) -> str:
        """Map score to stage name."""
        for (low, high), stage in self.STAGES.items():
            if low <= score <= high:
                return stage
        return "NEUTRAL"

    def _calculate_score(
        self,
        price: float,
        volume: float,
        sentiment: float,
        momentum_1h: float
    ) -> int:
        """
        Calculate reflexivity score from inputs.

        Factors:
        - Price trend vs history
        - Volume relative to average
        - Sentiment level
        - Short-term momentum
        """
        score = 0

        # Sentiment component (-2 to +2)
        if sentiment >= 80:
            score += 2
        elif sentiment >= 65:
            score += 1
        elif sentiment <= 20:
            score -= 2
        elif sentiment <= 35:
            score -= 1

        # Momentum component (-2 to +2)
        if momentum_1h >= 0.5:
            score += 2
        elif momentum_1h >= 0.2:
            score += 1
        elif momentum_1h <= -0.5:
            score -= 2
        elif momentum_1h <= -0.2:
            score -= 1

        # Volume surge component (-1 to +1)
        if len(self._volume_history) >= 3:
            avg_volume = sum(self._volume_history) / len(self._volume_history)
            if volume > avg_volume * 1.5:
                # High volume amplifies current direction
                score += 1 if momentum_1h > 0 else -1

        # Price trend component (-2 to +2)
        if len(self._price_history) >= 6:
            recent_avg = sum(list(self._price_history)[-3:]) / 3
            older_avg = sum(list(self._price_history)[:3]) / 3
            trend = (recent_avg - older_avg) / older_avg * 100

            if trend > 3:
                score += 2
            elif trend > 1:
                score += 1
            elif trend < -3:
                score -= 2
            elif trend < -1:
                score -= 1

        # Clamp to valid range
        return max(-7, min(7, score))

    def update(
        self,
        price: float,
        volume: float = 0,
        sentiment: float = 50,
        momentum_1h: float = 0.0
    ) -> int:
        """
        Update reflexivity score with new data.

        Args:
            price: Current price
            volume: Current volume (optional)
            sentiment: Fear & Greed index 0-100 (default 50)
            momentum_1h: 1-hour momentum -1 to +1 (default 0)

        Returns:
            Updated reflexivity score (-7 to +7)
        """
        # Update histories
        self._price_history.append(price)
        if volume > 0:
            self._volume_history.append(volume)
        self._sentiment_history.append(sentiment)

        # Calculate score
        score = self._calculate_score(price, volume, sentiment, momentum_1h)
        stage = self._get_stage(score)

        # Save to history
        entry = {
            "ts": time.time(),
            "price": price,
            "volume": volume,
            "sentiment": sentiment,
            "momentum": momentum_1h,
            "score": score,
            "stage": stage
        }
        self._data.setdefault("history", []).append(entry)
        self._data["score"] = score
        self._data["stage"] = stage
        self._data["last_update"] = datetime.now(timezone.utc).isoformat()

        self._save()
        return score

    @property
    def score(self) -> int:
        """Current reflexivity score."""
        return self._data.get("score", 0)

    @property
    def stage(self) -> str:
        """Current stage name."""
        return self._data.get("stage", "NEUTRAL")

    @property
    def size_modifier(self) -> float:
        """Recommended size modifier for current stage."""
        return self.SIZE_MODIFIERS.get(self.stage, 1.0)

    def should_block_buy(self) -> bool:
        """Returns True if conditions suggest avoiding buys."""
        return self.stage in ["LATE_BOOM", "BLOWOFF"]

    def should_block_sell(self) -> bool:
        """Returns True if conditions suggest avoiding sells."""
        return self.stage == "BUST"

    def to_prompt_block(self) -> str:
        """Format current state for injection into LLM prompt."""
        block = (
            f"\nREFLEXIVITY ASSESSMENT:\n"
            f"Score: {self.score}/7\n"
            f"Stage: {self.stage}\n"
            f"Size modifier: {self.size_modifier}x\n"
        )
        if self.stage == "BLOWOFF":
            block += "WARNING: Euphoria detected. High reversal risk.\n"
        elif self.stage == "BUST":
            block += "NOTE: Capitulation phase. Potential opportunity.\n"
        return block

    def stats(self) -> dict:
        """Reflexivity statistics."""
        history = self._data.get("history", [])
        return {
            "current_score": self.score,
            "current_stage": self.stage,
            "size_modifier": self.size_modifier,
            "history_length": len(history),
            "last_update": self._data.get("last_update")
        }
