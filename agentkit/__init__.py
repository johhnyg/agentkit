"""
agentkit — Production primitives for autonomous AI agents.

Built from 57 sessions of running a live autonomous agent.
Not theory. Production-tested.

pip install agentkit
"""
__version__ = "0.1.0"

from .lessons import LessonsMemory
from .humility import EpistemicHumility
from .contradiction import ContradictionDetector
from .outcomes import OutcomeTracker
from .circuit import CircuitBreaker
from .playbook import Playbook
from .reflexivity import Reflexivity
from .metrics import SelfMetrics

__all__ = [
    "LessonsMemory",
    "EpistemicHumility",
    "ContradictionDetector",
    "OutcomeTracker",
    "CircuitBreaker",
    "Playbook",
    "Reflexivity",
    "SelfMetrics",
]
