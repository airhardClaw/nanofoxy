"""Memory tool for querying agent memory."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from nanobot.agent.tools.base import Tool
from nanobot.agent.memory import MemoryStore, QMDEngine

if TYPE_CHECKING:
    from nanobot.agent.memory.consolidator import MemoryConsolidator


class MemoryTool(Tool):
    """Query and search agent memory."""

    def __init__(
        self,
        workspace: Path | None = None,
        subdirectory: str | None = None,
        qmd_engine: QMDEngine | None = None,
        citations: str = "auto",
        consolidator: "MemoryConsolidator | None" = None,
    ):
        self._workspace = workspace
        self._subdirectory = subdirectory
        self._qmd_engine = qmd_engine
        self._citations = citations
        self._consolidator = consolidator

    @property
    def name(self) -> str:
        return "memory"

    @property
    def description(self) -> str:
        return (
            "Query the agent's long-term memory. "
            "Use action='search' to search for specific information, "
            "action='summary' to get a brief overview, "
            "or action='history' to search recent events. "
            "Supports search modes: search (BM25), vsearch (vector), query (reranked)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "summary", "history", "promote", "dreaming"],
                    "description": "Action to perform: search, summary, history, promote, or dreaming",
                },
                "query": {
                    "type": "string",
                    "description": "Search query (required for search action)",
                },
                "mode": {
                    "type": "string",
                    "enum": ["search", "vsearch", "query"],
                    "description": "Search mode: search (BM25), vsearch (vector), query (reranked). Only used with QMD.",
                    "default": "search",
                },
                "collection": {
                    "type": "string",
                    "description": "Collection to search: workspace, sessions, or custom. Only used with QMD.",
                },
            },
            "required": ["action"],
        }

    async def execute(
        self,
        action: str = "summary",
        query: str = "",
        mode: str = "search",
        collection: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            if not self._workspace:
                return "Error: Workspace not configured"

            if self._subdirectory:
                store = MemoryStore(self._workspace / self._subdirectory)
            else:
                store = MemoryStore(self._workspace)

            if action == "search":
                if not query:
                    return "Error: query is required for search action"
                
                entry_id = f"search_{hash(query) % 100000}"
                self._track_recall(entry_id, query)
                
                if self._qmd_engine:
                    results = await store.search_with_qmd(
                        query,
                        qmd_engine=self._qmd_engine,
                    )
                    if not results:
                        return f"No results found for: {query}"
                    return self._format_qmd_results(results)
                else:
                    results = store.search_memory(query)
                    if not results:
                        return f"No results found for: {query}"
                    return f"Search results for '{query}':\n\n" + "\n".join(results)

            elif action == "summary":
                summary = store.get_memory_summary()
                return f"Memory Summary:\n{summary}"

            elif action == "history":
                if not query:
                    return "Error: query is required for history action"
                
                self._track_recall(f"history_{hash(query) % 100000}", query)
                
                if self._qmd_engine:
                    results = await store.search_with_qmd(
                        query,
                        qmd_engine=self._qmd_engine,
                    )
                    filtered = [r for r in results if r.get("collection") == "sessions"]
                    if not filtered:
                        return f"No history found for: {query}"
                    return self._format_qmd_results(filtered)
                else:
                    results = store.search_memory(query)
                    filtered = [r for r in results if r.startswith("[HISTORY]")]
                    if not filtered:
                        return f"No history found for: {query}"
                    return "History results:\n\n" + "\n".join(filtered)

            elif action == "dreaming":
                if self._consolidator and self._consolidator.dreaming:
                    stats = self._consolidator.get_dreaming_stats()
                    return f"Dreaming Status:\n- Enabled: {stats.get('enabled', False)}\n- Short-term recalls: {stats.get('short_term_recalls', 0)}\n- Promoted entries: {stats.get('promoted_count', 0)}"
                return "Dreaming is not enabled"

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"Error accessing memory: {e}"

    def _track_recall(self, entry_id: str, query: str) -> None:
        """Track recall for dreaming promotion decisions."""
        if self._consolidator and self._consolidator.dreaming:
            try:
                self._consolidator.dreaming.recall_store.add_recall(entry_id, query, 1.0)
            except Exception:
                pass

    def _format_qmd_results(self, results: list[dict[str, Any]]) -> str:
        """Format QMD search results with optional citations."""
        lines = []
        for r in results:
            content = r.get("content") or r.get("snippet", "")
            lines.append(content)
            
            if self._citations in ("auto", "on"):
                if citation := r.get("source"):
                    lines.append(f"_{citation}_")
        
        return "\n\n".join(lines)