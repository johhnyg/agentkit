"""
CircuitBreaker — Automatic safety limits.

When your agent is losing, it should slow down or stop.
This module implements circuit breakers that halt operation
based on consecutive losses, drawdown, or time-based cooldowns.

Usage:
    from agentkit import CircuitBreaker

    breaker = CircuitBreaker(
        max_consecutive_losses=3,
        max_drawdown_pct=15.0,
        cooldown_seconds=1800
    )

    status = breaker.check(
        consecutive_losses=current_losses,
        drawdown_pct=current_drawdown
    )

    if status["blocked"]:
        print(f"Blocked: {status['reason']}")
        print(f"Resumes: {status['resumes_at']}")
    else:
        execute_action()
"""
import json
import time
from datetime import datetime, timezone
from typing import Optional


class CircuitBreaker:
    """
    Implements safety limits that halt agent operation.

    Breakers:
    - consecutive_losses: Stop after N losses in a row
    - drawdown_pct: Stop when portfolio down X%
    - cooldown: Time-based pause after breaker trips

    Once tripped, breaker stays tripped until cooldown expires
    or conditions improve.
    """

    def __init__(
        self,
        max_consecutive_losses: int = 3,
        max_drawdown_pct: float = 15.0,
        cooldown_seconds: int = 1800,
        storage_path: Optional[str] = None
    ):
        self.max_consecutive_losses = max_consecutive_losses
        self.max_drawdown_pct = max_drawdown_pct
        self.cooldown_seconds = cooldown_seconds
        self.path = storage_path
        self._state = self._load()

    def _load(self) -> dict:
        if not self.path:
            return {"tripped_at": None, "trip_reason": None, "trip_count": 0}
        try:
            with open(self.path) as f:
                return json.load(f)
        except Exception:
            return {"tripped_at": None, "trip_reason": None, "trip_count": 0}

    def _save(self):
        if self.path:
            with open(self.path, "w") as f:
                json.dump(self._state, f, indent=2)

    def _trip(self, reason: str):
        """Trip the circuit breaker."""
        self._state["tripped_at"] = time.time()
        self._state["trip_reason"] = reason
        self._state["trip_count"] = self._state.get("trip_count", 0) + 1
        self._state["last_trip"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def _reset(self):
        """Reset the circuit breaker."""
        self._state["tripped_at"] = None
        self._state["trip_reason"] = None
        self._save()

    def check(
        self,
        consecutive_losses: int = 0,
        drawdown_pct: float = 0.0,
        custom_conditions: Optional[dict] = None
    ) -> dict:
        """
        Check if circuit breaker should block operation.

        Args:
            consecutive_losses: Current consecutive loss count
            drawdown_pct: Current portfolio drawdown percentage
            custom_conditions: Optional additional checks

        Returns:
            blocked: True if operation should be blocked
            reason: Why blocked (or None)
            resumes_at: When cooldown expires (ISO timestamp)
            cooldown_remaining: Seconds until resume
            prompt_block: Ready to inject into LLM prompt
        """
        now = time.time()

        # Check if currently in cooldown
        if self._state.get("tripped_at"):
            elapsed = now - self._state["tripped_at"]
            remaining = self.cooldown_seconds - elapsed

            if remaining > 0:
                resumes_at = datetime.fromtimestamp(
                    self._state["tripped_at"] + self.cooldown_seconds,
                    tz=timezone.utc
                ).isoformat()

                return {
                    "blocked": True,
                    "reason": f"Cooldown active: {self._state['trip_reason']}",
                    "resumes_at": resumes_at,
                    "cooldown_remaining": int(remaining),
                    "prompt_block": (
                        f"\nCIRCUIT BREAKER: TRIPPED\n"
                        f"Reason: {self._state['trip_reason']}\n"
                        f"Cooldown remaining: {int(remaining)}s\n"
                        f"DO NOT take any actions until cooldown expires.\n"
                    )
                }
            else:
                # Cooldown expired — check if conditions improved
                pass

        # Check consecutive losses
        if consecutive_losses >= self.max_consecutive_losses:
            self._trip(f"consecutive_losses={consecutive_losses}")
            return {
                "blocked": True,
                "reason": f"Consecutive losses ({consecutive_losses}) >= limit ({self.max_consecutive_losses})",
                "resumes_at": datetime.fromtimestamp(
                    now + self.cooldown_seconds, tz=timezone.utc
                ).isoformat(),
                "cooldown_remaining": self.cooldown_seconds,
                "prompt_block": (
                    f"\nCIRCUIT BREAKER: TRIPPED\n"
                    f"Reason: {consecutive_losses} consecutive losses\n"
                    f"Cooldown: {self.cooldown_seconds}s\n"
                    f"STOP all trading until conditions improve.\n"
                )
            }

        # Check drawdown
        if drawdown_pct >= self.max_drawdown_pct:
            self._trip(f"drawdown={drawdown_pct}%")
            return {
                "blocked": True,
                "reason": f"Drawdown ({drawdown_pct}%) >= limit ({self.max_drawdown_pct}%)",
                "resumes_at": datetime.fromtimestamp(
                    now + self.cooldown_seconds, tz=timezone.utc
                ).isoformat(),
                "cooldown_remaining": self.cooldown_seconds,
                "prompt_block": (
                    f"\nCIRCUIT BREAKER: TRIPPED\n"
                    f"Reason: Drawdown at {drawdown_pct}%\n"
                    f"Cooldown: {self.cooldown_seconds}s\n"
                    f"STOP all trading until drawdown recovers.\n"
                )
            }

        # All clear — reset if previously tripped
        if self._state.get("tripped_at"):
            self._reset()

        return {
            "blocked": False,
            "reason": None,
            "resumes_at": None,
            "cooldown_remaining": 0,
            "prompt_block": ""
        }

    def force_reset(self):
        """Manually reset the circuit breaker."""
        self._reset()

    def stats(self) -> dict:
        """Circuit breaker statistics."""
        return {
            "currently_tripped": self._state.get("tripped_at") is not None,
            "trip_reason": self._state.get("trip_reason"),
            "total_trips": self._state.get("trip_count", 0),
            "last_trip": self._state.get("last_trip"),
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_drawdown_pct": self.max_drawdown_pct,
            "cooldown_seconds": self.cooldown_seconds
        }
