# agentkit

Production primitives for autonomous AI agents.

Built from 57 sessions running a live autonomous agent
managing real money for 50+ days without human intervention.

Not theory. Not a tutorial. Production-tested.

```bash
pip install agentkit
```

## Why agentkit?

Most agent frameworks focus on tool calling and prompt chaining.
That's the easy part.

The hard part is what happens when your agent runs for weeks:
- How does it learn from mistakes without forgetting successes?
- How does it know when it's in unfamiliar territory?
- How does it detect when its own signals contradict each other?
- How does it avoid repeating the same error 47 times?
- How does it know when to stop?

These problems don't appear in demos. They appear at 3am on day 23
when your agent has been running autonomously and you're asleep.

agentkit solves them.

## The 8 Primitives

### 1. LessonsMemory
**Agents that learn from outcomes, not just instructions.**

```python
from agentkit import LessonsMemory

memory = LessonsMemory("lessons.json")

# Record what happened
memory.record(
    text="Buying during extreme fear with weak momentum = loss",
    pnl_impact=-12.50,
    outcome="LOSS",
    conditions={"fear_greed": 12, "momentum": -0.3}
)

# Inject top lessons into your next prompt
prompt += memory.to_prompt_block(5)
```

Lessons are ranked by `impact * recency * frequency`. Recent high-impact
lessons surface first. Old lessons decay but don't disappear.

### 2. EpistemicHumility
**Agents that know what they don't know.**

```python
from agentkit import EpistemicHumility

humility = EpistemicHumility("knowledge.json")

assessment = humility.assess({
    "market_regime": "bear",
    "volatility": "extreme",
    "signal": "weak_buy"
})

if assessment["familiarity"] == "UNKNOWN":
    # Never seen this before — reduce action size
    size *= assessment["size_modifier"]  # 0.5x

# After acting, record the experience
humility.record(conditions)
```

Tracks every condition combination your agent has operated in.
Returns KNOWN (3+), RARE (1-2), or UNKNOWN (0) with size modifiers.

### 3. ContradictionDetector
**Surface conflicts before your agent acts.**

```python
from agentkit import ContradictionDetector

detector = ContradictionDetector()

detector.add_rule(
    name="momentum_vs_sentiment",
    severity="HIGH",
    check=lambda ctx: ctx["momentum"] > 0 and ctx["sentiment"] < 20,
    detail=lambda ctx: f"Momentum bullish but sentiment fearful"
)

report = detector.analyze(context)
if report["level"] == "MAJOR_CONFLICT":
    # Don't act — signals disagree
    prompt += report["prompt_block"]
```

Scores contradictions 0-10. CONSENSUS, MINOR_CONFLICT, CONFLICT, MAJOR_CONFLICT.

### 4. OutcomeTracker
**Link every decision to its result.**

```python
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

# Get win rate by condition
stats = tracker.stats_by_condition("fear_greed", buckets=[0, 25, 50, 75, 100])
```

### 5. CircuitBreaker
**Automatic safety limits.**

```python
from agentkit import CircuitBreaker

breaker = CircuitBreaker(
    max_consecutive_losses=3,
    max_drawdown_pct=15.0,
    cooldown_seconds=1800
)

# Check before acting
status = breaker.check(
    consecutive_losses=current_losses,
    drawdown_pct=current_drawdown
)

if status["blocked"]:
    print(f"Blocked: {status['reason']}")
    print(f"Resumes: {status['resumes_at']}")
else:
    # Safe to proceed
    execute_action()
```

### 6. Playbook
**Rules that evolve from patterns.**

```python
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

# Check which rules apply
applicable = playbook.evaluate(context)
for rule in applicable:
    print(f"Apply: {rule['name']} → {rule['action']}")

# Confirm or reject rules based on outcomes
playbook.confirm_rule("fear_entry", outcome="WIN", pnl=12.0)
```

Rules have states: CANDIDATE → CONFIRMED → PROVEN.
Poor performers get demoted or removed automatically.

### 7. Reflexivity
**Detect when momentum creates its own reality.**

```python
from agentkit import Reflexivity

reflex = Reflexivity()

# Feed it market data
score = reflex.update(
    price=67000,
    volume=1200000,
    sentiment=72,
    momentum_1h=0.8
)

print(f"Reflexivity: {score}")  # -7 to +7
print(f"Stage: {reflex.stage}")  # BUST → NEUTRAL → BOOM

if reflex.stage in ["LATE_BOOM", "BLOWOFF"]:
    # Momentum driving price — reduce exposure
    size *= 0.25
```

Based on Soros reflexivity theory. Detects self-reinforcing feedback loops.

### 8. SelfMetrics
**Agent performance tracking.**

```python
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
print(f"Avg hold time: {report['avg_hold_hours']}h")
print(f"Best condition: {report['best_condition']}")
```

## Design Philosophy

**1. File-based persistence.** JSON files, not databases. Your agent
should run on a $6/month server, not require infrastructure.

**2. Prompt-ready output.** Every module has `to_prompt_block()`.
The primitives are designed to inject context into LLM prompts.

**3. Decay over deletion.** Old lessons decay in weight but persist.
Your agent's history is never erased, just de-prioritized.

**4. Composable.** Use one module or all eight. They don't depend
on each other. Mix with any agent framework.

**5. Observable.** Every module has `stats()`. You can inspect
your agent's learning at any time.

## Installation

```bash
pip install agentkit
```

Or from source:

```bash
git clone https://github.com/johhnyg/agentkit
cd agentkit
pip install -e .
```

## Requirements

- Python 3.9+
- No external dependencies (stdlib only)

## Origin

These primitives were extracted from a live trading bot that has been
running autonomously since February 2026. The bot manages real money,
makes its own decisions, and learns from outcomes — with no human in
the loop for weeks at a time.

Every pattern in agentkit exists because we hit a wall without it.

## License

MIT

## Contributing

Issues and PRs welcome at [github.com/johhnyg/agentkit](https://github.com/johhnyg/agentkit).
