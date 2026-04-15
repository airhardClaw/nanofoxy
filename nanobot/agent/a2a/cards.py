"""Agent Card generation for A2A discovery."""

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentCard:
    """A2A Agent Card (metadata for discovery)."""
    subagent_id: str
    name: str
    role: str
    description: str
    capabilities: list[str]
    skills: list[dict[str, str]]
    version: str = "1.0"
    provider: str = "nanofoxy"

    def to_dict(self) -> dict[str, Any]:
        """Convert to A2A Agent Card format."""
        return {
            "schema": "agentcard@v1",
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "provider": {
                "organization": self.provider,
            },
            "capabilities": {
                "supported modalities": ["text"],
                "supported content types": ["text", "json"],
            },
            "skills": [
                {
                    "id": skill.get("id", ""),
                    "name": skill.get("name", ""),
                    "description": skill.get("description", ""),
                }
                for skill in self.skills
            ],
            "metadata": {
                "subagent_id": self.subagent_id,
                "role": self.role,
                "capabilities": self.capabilities,
            },
        }


def generate_agent_card(
    subagent_id: str,
    name: str,
    role: str,
    description: str,
    capabilities: list[str],
    skills: list[dict[str, str]],
) -> dict[str, Any]:
    """Generate an A2A Agent Card from config.
    
    Args:
        subagent_id: Subagent identifier
        name: Display name
        role: Role name (e.g., "coding-expert")
        description: Description of capabilities
        capabilities: List of capabilities
        skills: List of skill definitions
        
    Returns:
        Agent Card dict in A2A format
    """
    card = AgentCard(
        subagent_id=subagent_id,
        name=name,
        role=role,
        description=description,
        capabilities=capabilities,
        skills=skills,
    )
    return card.to_dict()


def generate_all_cards(configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate Agent Cards for all subagent configs.
    
    Args:
        configs: List of subagent configurations
        
    Returns:
        List of Agent Cards
    """
    cards = []
    for config in configs:
        if not config.get("enabled", True):
            continue
        card = generate_agent_card(
            subagent_id=config.get("subagent_id", ""),
            name=config.get("name", config.get("role", "")),
            role=config.get("role", ""),
            description=config.get("description", ""),
            capabilities=config.get("capabilities", []),
            skills=config.get("skills", []),
        )
        cards.append(card)
    return cards