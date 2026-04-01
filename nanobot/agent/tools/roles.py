"""Role description tool for subagent role information."""

import re
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class DescribeRoleTool(Tool):
    """Get a quick overview of subagent role capabilities."""

    ROLES_DIR = Path("/home/sir-airhard/nanofoxy/nanobot/roles")

    @property
    def name(self) -> str:
        return "describe_role"

    @property
    def description(self) -> str:
        return (
            "Get a quick overview of a subagent role. "
            "Use this to understand what a role can do before delegating a task. "
            "Returns role name, description, available tools, and excluded tools."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["coding-expert", "information-expert", "websearch-expert", "file-handel-expert", "team-leader"],
                    "description": "The role to describe",
                },
            },
            "required": ["role"],
        }

    async def execute(self, role: str, **kwargs: Any) -> str:
        role_file = self.ROLES_DIR / f"{role}.md"
        
        if not role_file.exists():
            alt_name = role.replace("-", "-")
            if alt_name != role:
                role_file = self.ROLES_DIR / f"{alt_name}.md"
        
        if not role_file.exists():
            return f"Error: Role '{role}' not found in {self.ROLES_DIR}"
        
        content = role_file.read_text(encoding="utf-8")
        
        info: dict[str, Any] = {"role": role}
        
        frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if frontmatter_match:
            fm = frontmatter_match.group(1)
            current_key = None
            current_list = []
            
            for line in fm.split("\n"):
                if line.startswith("  - "):
                    if current_key:
                        current_list.append(line[4:].strip())
                elif ":" in line and not line.startswith(" "):
                    if current_key and current_list:
                        info[current_key] = current_list
                    key, value = line.split(":", 1)
                    current_key = key.strip()
                    value = value.strip()
                    current_list = []
                    if value:
                        current_list = [value]
            
            if current_key and current_list:
                info[current_key] = current_list
        
        main_content = content[frontmatter_match.end():] if frontmatter_match else content
        
        lines = main_content.strip().split("\n")
        desc_lines = []
        in_description = False
        for line in lines:
            if line.startswith("## "):
                break
            if in_description:
                desc_lines.append(line.strip())
            elif line.startswith("# ") and not line.startswith("##"):
                in_description = True
        
        if desc_lines:
            info["about"] = " ".join(desc_lines[:3])
        
        role_name = info.get("name", role)
        if isinstance(role_name, list):
            role_name = role_name[0] if role_name else role
        
        result = f"# {role_name}\n\n"
        
        desc = info.get("description")
        if isinstance(desc, list):
            desc = desc[0] if desc else ""
        if desc:
            result += f"**Description**: {desc}\n\n"
        
        about = info.get("about", "")
        if about:
            result += f"{about}\n\n"
        
        tools = info.get("tools", [])
        if tools:
            result += f"**Available Tools**: {', '.join(tools)}\n\n"
        
        excluded = info.get("excluded_tools", [])
        if excluded:
            result += f"**Excluded Tools**: {', '.join(excluded)}\n\n"
        
        result += f"_Full details: {role_file}_"
        
        return result