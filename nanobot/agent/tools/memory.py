"""Memory tool for querying agent memory."""

from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.agent.memory import MemoryStore


class MemoryTool(Tool):
    """Query and search agent memory."""

    def __init__(self, workspace: Path | None = None):
        self._workspace = workspace

    @property
    def name(self) -> str:
        return "memory"

    @property
    def description(self) -> str:
        return (
            "Query the agent's long-term memory. "
            "Use action='search' to search for specific information, "
            "action='summary' to get a brief overview, "
            "or action='history' to search recent events."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "summary", "history"],
                    "description": "Action to perform: search, summary, or history",
                },
                "query": {
                    "type": "string",
                    "description": "Search query (required for search action)",
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str = "summary", query: str = "", **kwargs: Any) -> str:
        try:
            if not self._workspace:
                return "Error: Workspace not configured"

            store = MemoryStore(self._workspace)

            if action == "search":
                if not query:
                    return "Error: query is required for search action"
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
                results = store.search_memory(query)
                filtered = [r for r in results if r.startswith("[HISTORY]")]
                if not filtered:
                    return f"No history found for: {query}"
                return "History results:\n\n" + "\n".join(filtered)

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"Error accessing memory: {e}"
