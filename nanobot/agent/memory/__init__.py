"""Memory system - dual backend support for builtin and QMD."""

from nanobot.agent.memory.store import MemoryStore
from nanobot.agent.memory.consolidator import MemoryConsolidator
from nanobot.agent.memory.qmd_engine import QMDEngine
from nanobot.agent.memory.dreaming import DreamingService, ShortTermRecallStore, DailyNoteManager

# Re-export helpers for backwards compatibility
from nanobot.utils.helpers import estimate_message_tokens, estimate_prompt_tokens_chain

__all__ = [
    "MemoryStore",
    "MemoryConsolidator",
    "QMDEngine",
    "DreamingService",
    "ShortTermRecallStore",
    "DailyNoteManager",
    "estimate_message_tokens",
    "estimate_prompt_tokens_chain",
]