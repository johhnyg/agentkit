"""
Example: Using all 8 agentkit modules for a trading agent.
"""
import sys
sys.path.insert(0, "/root/agentkit")

from agentkit import (
    LessonsMemory,
    EpistemicHumility,
    ContradictionDetector,
    OutcomeTracker,
    CircuitBreaker,
    Playbook,
    Reflexivity,
    SelfMetrics
)

print("=" * 60)
print("AGENTKIT — All 8 Primitives Demo")
print("=" * 60)

# 1. LessonsMemory — learn from outcomes
print("\n1. LESSONS MEMORY")
memory = LessonsMemory("/tmp/lessons.json")
memory.record(
    text="Entering during extreme fear with negative momentum = loss",
    pnl_impact=-12.50,
    outcome="LOSS"
)
print(memory.to_prompt_block(3))

# 2. EpistemicHumility — know what you don't know
print("2. EPISTEMIC HUMILITY")
humility = EpistemicHumility("/tmp/knowledge.json")
assessment = humility.assess({
    "market_regime": "bear",
    "volatility": "high"
})
print(f"   Familiarity: {assessment['familiarity']}")
print(f"   Size modifier: {assessment['size_modifier']}x")

# 3. ContradictionDetector — surface conflicts
print("\n3. CONTRADICTION DETECTOR")
detector = ContradictionDetector()
detector.add_rule(
    name="signal_vs_fear",
    severity="HIGH",
    check=lambda ctx: ctx.get("signal", 0) > 3 and ctx.get("fear_greed", 50) > 70,
    detail=lambda ctx: f"Bullish signal but greedy market"
)
report = detector.analyze({"signal": 5, "fear_greed": 75})
print(f"   Level: {report['level']} (score: {report['contradiction_score']}/10)")

# 4. OutcomeTracker — link decisions to results
print("\n4. OUTCOME TRACKER")
tracker = OutcomeTracker("/tmp/outcomes.json")
decision_id = tracker.record_decision(
    action="BUY",
    reasoning="Strong signal alignment",
    context={"signal": 6, "fear_greed": 25}
)
tracker.record_outcome(decision_id, result="WIN", pnl=15.30)
print(f"   Decision recorded: {decision_id}")
print(f"   Stats: {tracker.stats()}")

# 5. CircuitBreaker — automatic safety limits
print("\n5. CIRCUIT BREAKER")
breaker = CircuitBreaker(
    max_consecutive_losses=3,
    max_drawdown_pct=15.0,
    cooldown_seconds=1800
)
status = breaker.check(consecutive_losses=2, drawdown_pct=8.0)
print(f"   Blocked: {status['blocked']}")
print(f"   Stats: {breaker.stats()}")

# 6. Playbook — rules that evolve
print("\n6. PLAYBOOK")
playbook = Playbook("/tmp/playbook.json")
playbook.add_rule(
    name="fear_entry",
    trigger="fear_greed < 20 AND signal > 3",
    action="size *= 1.5",
    source="LEARNED"
)
playbook.confirm_rule("fear_entry", outcome="WIN", pnl=12.0)
playbook.confirm_rule("fear_entry", outcome="WIN", pnl=8.0)
playbook.confirm_rule("fear_entry", outcome="WIN", pnl=15.0)
rule = playbook.get_rule("fear_entry")
print(f"   Rule 'fear_entry' state: {rule['state']}")
print(f"   Confirmations: {rule['confirmations']}")

# 7. Reflexivity — detect momentum loops
print("\n7. REFLEXIVITY")
reflex = Reflexivity("/tmp/reflexivity.json")
score = reflex.update(
    price=67000,
    volume=1200000,
    sentiment=72,
    momentum_1h=0.6
)
print(f"   Score: {score}/7")
print(f"   Stage: {reflex.stage}")
print(f"   Size modifier: {reflex.size_modifier}x")

# 8. SelfMetrics — performance tracking
print("\n8. SELF METRICS")
metrics = SelfMetrics("/tmp/metrics.json")
metrics.record_action("BUY", size=50.0, context={"regime": "normal"})
metrics.record_outcome(pnl=12.50, fees=0.50)
metrics.record_action("BUY", size=50.0, context={"regime": "normal"})
metrics.record_outcome(pnl=-8.00, fees=0.50)
report = metrics.report()
print(f"   Win rate: {report['win_rate']}%")
print(f"   Net P&L: ${report['net_pnl']}")

print("\n" + "=" * 60)
print("All 8 primitives working. Ready for production.")
print("=" * 60)
