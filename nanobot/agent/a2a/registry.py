"""Agent Registry for A2A discovery and registration."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for managing subagent discovery and registration.
    
    Provides:
    - Registration of new subagents
    - Discovery by capabilities
    - Listing all registered agents
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self._agents: dict[str, dict] = {}
        self._load_existing()

    def _load_existing(self) -> None:
        """Load existing subagent configs from .subagents directory."""
        subagent_dir = self.workspace / ".subagents"
        if not subagent_dir.exists():
            return

        for config_file in subagent_dir.glob("*.json"):
            if config_file.name == "config.json" or config_file.name.startswith("_"):
                continue
            try:
                config = json.loads(config_file.read_text(encoding="utf-8"))
                subagent_id = config_file.stem
                if config.get("enabled", True):
                    self._agents[subagent_id] = config
                    logger.info("Loaded subagent: {}", subagent_id)
            except json.JSONDecodeError:
                logger.warning("Failed to parse subagent config: {}", config_file.name)

    def register(self, config: dict[str, Any]) -> dict[str, Any]:
        """Register a new subagent or update existing.
        
        Args:
            config: Subagent configuration dict
            
        Returns:
            Registration result with subagent_id
        """
        subagent_id = config.get("subagent_id") or config.get("role", "").replace("-", "_")
        
        if not subagent_id:
            return {"success": False, "error": "No subagent_id or role provided"}
        
        config["subagent_id"] = subagent_id
        config["enabled"] = True
        
        # Save to file
        subagent_dir = self.workspace / ".subagents"
        subagent_dir.mkdir(exist_ok=True)
        
        config_file = subagent_dir / f"{subagent_id}.json"
        config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        
        self._agents[subagent_id] = config
        logger.info("Registered subagent: {}", subagent_id)
        
        return {"success": True, "subagent_id": subagent_id}

    def unregister(self, subagent_id: str) -> dict[str, Any]:
        """Unregister a subagent (disable, not delete).
        
        Args:
            subagent_id: ID of subagent to unregister
            
        Returns:
            Result of unregistration
        """
        if subagent_id not in self._agents:
            return {"success": False, "error": f"Subagent {subagent_id} not found"}
        
        self._agents[subagent_id]["enabled"] = False
        
        # Update file
        subagent_dir = self.workspace / ".subagents"
        config_file = subagent_dir / f"{subagent_id}.json"
        if config_file.exists():
            config_file.write_text(json.dumps(self._agents[subagent_id], indent=2), encoding="utf-8")
        
        logger.info("Unregistered subagent: {}", subagent_id)
        return {"success": True, "subagent_id": subagent_id}

    def get(self, subagent_id: str) -> dict[str, Any] | None:
        """Get subagent configuration by ID."""
        return self._agents.get(subagent_id)

    def list_all(self) -> list[dict[str, Any]]:
        """List all registered (enabled) subagents."""
        return [
            {
                "subagent_id": subagent_id,
                "name": config.get("name", subagent_id),
                "role": config.get("role", ""),
                "description": config.get("description", ""),
                "capabilities": config.get("capabilities", []),
                "skills": config.get("skills", []),
                "enabled": config.get("enabled", True),
            }
            for subagent_id, config in self._agents.items()
            if config.get("enabled", True)
        ]

    def discover(self, capabilities: list[str]) -> list[dict[str, Any]]:
        """Discover subagents by required capabilities.
        
        Args:
            capabilities: List of required capabilities
            
        Returns:
            List of subagents that have ALL required capabilities
        """
        results = []
        for subagent_id, config in self._agents.items():
            if not config.get("enabled", True):
                continue
            
            agent_caps = config.get("capabilities", [])
            if all(cap in agent_caps for cap in capabilities):
                results.append({
                    "subagent_id": subagent_id,
                    "name": config.get("name", subagent_id),
                    "role": config.get("role", ""),
                    "capabilities": agent_caps,
                })
        
        return results

    def get_by_role(self, role: str) -> dict[str, Any] | None:
        """Get subagent by role name."""
        role_normalized = role.lower().replace(" ", "-")
        for config in self._agents.values():
            if config.get("role", "").lower().replace(" ", "-") == role_normalized:
                return config
        return None

    def reload(self) -> None:
        """Reload all subagent configs from disk."""
        self._agents.clear()
        self._load_existing()