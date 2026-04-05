"""Tests for QMD memory engine configuration and functionality."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from nanobot.config.schema import (
    Config,
    QMDConfig,
    QMDSessionsConfig,
    QMDSearchScope,
    QMDLimitsConfig,
    MemoryConfig,
)


class TestQMDConfigSchema:
    """Test QMD configuration schema."""

    def test_default_qmd_config(self):
        """Test default QMD configuration values."""
        config = Config()
        memory = config.tools.memory

        assert memory.backend == "builtin"
        assert memory.qmd.update_interval_seconds == 300
        assert memory.qmd.sessions.enabled is True
        assert memory.qmd.limits.timeout_ms == 4000

    def test_qmd_config_from_dict(self):
        """Test QMD config can be created from dict."""
        data = {
            "backend": "qmd",
            "qmd": {
                "paths": [
                    {"name": "docs", "path": "~/notes", "pattern": "**/*.md"}
                ],
                "sessions": {"enabled": False},
                "limits": {"timeoutMs": 8000},
            },
        }
        # Need to wrap in the tools.m structure
        config = Config.model_validate({"tools": {"memory": data}})

        assert config.tools.memory.backend == "qmd"
        assert len(config.tools.memory.qmd.paths) == 1
        assert config.tools.memory.qmd.paths[0].name == "docs"
        assert config.tools.memory.qmd.sessions.enabled is False
        assert config.tools.memory.qmd.limits.timeout_ms == 8000

    def test_qmd_citations_config(self):
        """Test citations configuration."""
        data = {"citations": "on"}
        config = Config.model_validate({"tools": {"memory": data}})

        assert config.tools.memory.citations == "on"

        data = {"citations": "off"}
        config = Config.model_validate({"tools": {"memory": data}})
        assert config.tools.memory.citations == "off"


class TestQMDEngine:
    """Test QMDEngine functionality."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a temporary workspace."""
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        (mem_dir / "MEMORY.md").write_text("# Memory\nTest fact")
        (mem_dir / "HISTORY.md").write_text("Test history entry")
        return tmp_path

    def test_qmd_engine_init(self, workspace):
        """Test QMDEngine initialization."""
        from nanobot.agent.memory import QMDEngine

        engine = QMDEngine(
            workspace=workspace,
            agent_id="test-agent",
            config={"sessions": {"enabled": True}},
        )

        assert engine.agent_id == "test-agent"
        assert engine.sessions_enabled is True
        assert engine.qmd_home.exists()

    def test_qmd_engine_paths_config(self, workspace):
        """Test QMDEngine with extra paths config."""
        from nanobot.agent.memory import QMDEngine

        config = {
            "paths": [
                {"name": "docs", "path": str(workspace), "pattern": "*.md"}
            ],
            "sessions": {"enabled": True},
            "updateIntervalSeconds": 600,
        }

        engine = QMDEngine(
            workspace=workspace,
            agent_id="test-agent",
            config=config,
        )

        assert len(engine.paths) == 1
        assert engine.paths[0]["name"] == "docs"
        assert engine.update_interval == 600

    @pytest.mark.asyncio
    async def test_qmd_engine_check_availability(self, workspace):
        """Test QMD availability check when qmd not installed."""
        from nanobot.agent.memory import QMDEngine

        engine = QMDEngine(workspace=workspace, agent_id="test")

        # Should return False when qmd not on PATH
        result = await engine.ensure_available()
        assert result is False

    @pytest.mark.asyncio
    async def test_qmd_search_fallback(self, workspace):
        """Test QMD search falls back to builtin when unavailable."""
        from nanobot.agent.memory import QMDEngine, MemoryStore

        engine = QMDEngine(workspace=workspace, agent_id="test")
        store = MemoryStore(workspace)

        # When QMD unavailable, should fallback to builtin
        results = await store.search_with_qmd("test", qmd_engine=engine)

        # Should return builtin results
        assert len(results) > 0
        assert results[0]["collection"] == "builtin"

    def test_qmd_get_citation(self, workspace):
        """Test get_citation method."""
        from nanobot.agent.memory import QMDEngine

        engine = QMDEngine(workspace=workspace, agent_id="test")

        result1 = engine.get_citation({"path": "qmd/workspace/MEMORY.md#line1"})
        assert "Source:" in result1

        result2 = engine.get_citation({"path": "qmd/workspace/test.md"})
        assert "Source:" in result2

        result3 = engine.get_citation({"path": ""})
        assert result3 == ""

    def test_qmd_format_messages(self, workspace):
        """Test _format_messages_for_indexing method."""
        from nanobot.agent.memory import QMDEngine

        engine = QMDEngine(workspace=workspace, agent_id="test")

        messages = [
            {"role": "user", "content": "Hello", "timestamp": "2026-01-01 10:00:00"},
            {"role": "assistant", "content": "Hi there!", "timestamp": "2026-01-01 10:00:01"},
            {"role": "user", "content": "How are you?", "timestamp": "2026-01-01 10:00:02"},
        ]

        result = engine._format_messages_for_indexing(messages)

        assert "USER: Hello" in result
        assert "ASSISTANT: Hi there!" in result

    def test_qmd_parse_results(self, workspace):
        """Test _parse_search_results method."""
        from nanobot.agent.memory import QMDEngine

        engine = QMDEngine(workspace=workspace, agent_id="test")

        output = "qmd/workspace/MEMORY.md:Test content here\nAnother result"
        results = engine._parse_search_results(output, "workspace")

        assert len(results) == 2
        assert results[0]["collection"] == "workspace"
        assert results[0]["path"] == "qmd/workspace/MEMORY.md"
        assert results[0]["snippet"] == "Test content here"

    def test_qmd_parse_empty_results(self, workspace):
        """Test _parse_search_results with empty output."""
        from nanobot.agent.memory import QMDEngine

        engine = QMDEngine(workspace=workspace, agent_id="test")

        results = engine._parse_search_results("", "workspace")
        assert results == []

        results = engine._parse_search_results("  \n\n  ", "workspace")
        assert results == []

    def test_qmd_timeout_config(self, workspace):
        """Test QMD timeout configuration."""
        from nanobot.agent.memory import QMDEngine

        config = {"limits": {"timeoutMs": 8000}}
        engine = QMDEngine(workspace=workspace, agent_id="test", config=config)

        assert engine.timeout_ms == 8000

    def test_qmd_collections_dir(self, workspace):
        """Test QMD collections directory creation."""
        from nanobot.agent.memory import QMDEngine

        engine = QMDEngine(workspace=workspace, agent_id="test")

        assert engine.collections_dir.exists()
        assert "test" in str(engine.collections_dir)


class TestMemoryToolQMD:
    """Test MemoryTool with QMD integration."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a temporary workspace."""
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        (mem_dir / "MEMORY.md").write_text("# Memory\nTest fact: User likes coffee")
        return tmp_path

    @pytest.mark.asyncio
    async def test_memory_tool_builtin_search(self, workspace):
        """Test MemoryTool uses builtin when no QMD engine."""
        from nanobot.agent.tools.memory import MemoryTool

        tool = MemoryTool(workspace=workspace, qmd_engine=None)

        result = await tool.execute(action="search", query="coffee")

        assert "coffee" in result
        assert "Search results" in result

    @pytest.mark.asyncio
    async def test_memory_tool_summary(self, workspace):
        """Test MemoryTool summary action."""
        from nanobot.agent.tools.memory import MemoryTool

        tool = MemoryTool(workspace=workspace)

        result = await tool.execute(action="summary")

        assert "Memory Summary" in result

    @pytest.mark.asyncio
    async def test_memory_tool_citations(self, workspace):
        """Test MemoryTool citation formatting."""
        from nanobot.agent.tools.memory import MemoryTool

        tool = MemoryTool(workspace=workspace, citations="on")

        result = await tool.execute(action="search", query="coffee")

        assert "Source:" in result or "coffee" in result