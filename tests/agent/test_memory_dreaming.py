"""Tests for Dreaming memory consolidation system."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.config.schema import (
    Config,
    DreamingConfig,
    DreamingLightConfig,
    DreamingDeepConfig,
    DreamingREMConfig,
)


class TestDreamingConfigSchema:
    """Test Dreaming configuration schema."""

    def test_default_dreaming_config(self):
        """Test default Dreaming configuration values."""
        config = Config()
        dreaming = config.tools.memory.dreaming

        assert dreaming.enabled is True
        assert dreaming.light.cron == "0 */6 * * *"
        assert dreaming.deep.cron == "0 3 * * *"
        assert dreaming.rem.cron == "0 5 * * 0"
        assert dreaming.light.limit == 100
        assert dreaming.deep.min_score == 0.8
        assert dreaming.deep.min_recall_count == 3

    def test_dreaming_config_from_dict(self):
        """Test Dreaming config can be created from dict."""
        data = {
            "dreaming": {
                "enabled": False,
                "timezone": "Asia/Shanghai",
                "light": {
                    "enabled": False,
                    "cron": "0 */12 * * *",
                },
                "deep": {
                    "minScore": 0.9,
                    "minRecallCount": 5,
                },
            }
        }
        config = Config.model_validate({"tools": {"memory": data}})

        assert config.tools.memory.dreaming.enabled is False
        assert config.tools.memory.dreaming.timezone == "Asia/Shanghai"
        assert config.tools.memory.dreaming.light.enabled is False
        assert config.tools.memory.dreaming.deep.min_score == 0.9

    def test_dreaming_recovery_config(self):
        """Test Dreaming recovery configuration."""
        config = Config()
        recovery = config.tools.memory.dreaming.deep.recovery

        assert recovery.enabled is True
        assert recovery.trigger_below_health == 0.35
        assert recovery.lookback_days == 30
        assert recovery.max_recovered_candidates == 20


class TestShortTermRecallStore:
    """Test ShortTermRecallStore functionality."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a temporary workspace."""
        dreams_dir = tmp_path / "memory" / ".dreams"
        dreams_dir.mkdir(parents=True)
        return tmp_path

    def test_recall_store_init(self, workspace):
        """Test recall store initialization."""
        from nanobot.agent.memory.dreaming import ShortTermRecallStore

        store = ShortTermRecallStore(workspace)

        assert store.dreams_dir.exists()
        # Note: recall_file is created when first recall is added

    def test_add_recall(self, workspace):
        """Test adding a recall entry."""
        from nanobot.agent.memory.dreaming import ShortTermRecallStore

        store = ShortTermRecallStore(workspace)
        store.add_recall("entry_1", "test query", 0.9)

        recalls = store.get_recalls()
        assert len(recalls) == 1
        assert recalls[0].entry_id == "entry_1"
        assert recalls[0].query == "test query"

    def test_get_recalls_filtered(self, workspace):
        """Test filtering recall entries."""
        from nanobot.agent.memory.dreaming import ShortTermRecallStore, RecallEntry

        store = ShortTermRecallStore(workspace)

        # Add multiple entries
        store.add_recall("entry_1", "query1", 1.0)
        store.add_recall("entry_2", "query2", 0.8)

        # Filter by entry_id
        recalls = store.get_recalls(entry_id="entry_1")
        assert len(recalls) == 1
        assert recalls[0].entry_id == "entry_1"

    def test_recall_stats(self, workspace):
        """Test getting recall statistics."""
        from nanobot.agent.memory.dreaming import ShortTermRecallStore

        store = ShortTermRecallStore(workspace)

        # Add multiple recalls for same entry
        store.add_recall("entry_1", "query1", 1.0)
        store.add_recall("entry_1", "query2", 0.9)
        store.add_recall("entry_1", "query1", 0.8)

        stats = store.get_recall_stats("entry_1")

        assert stats["count"] == 3
        assert stats["unique_queries"] == 2
        assert 0.8 < stats["avg_score"] < 1.0


class TestDailyNoteManager:
    """Test DailyNoteManager functionality."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a temporary workspace."""
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir(parents=True)
        return tmp_path

    def test_daily_note_init(self, workspace):
        """Test daily note manager initialization."""
        from nanobot.agent.memory.dreaming import DailyNoteManager

        manager = DailyNoteManager(workspace, timezone="UTC")

        assert manager.memory_dir.exists()
        assert manager.timezone is not None

    def test_get_today_filename(self, workspace):
        """Test getting today's note filename."""
        from nanobot.agent.memory.dreaming import DailyNoteManager

        manager = DailyNoteManager(workspace)
        today = datetime.now().strftime("%Y-%m-%d")

        assert manager.get_today_filename().name == f"{today}.md"

    def test_append_to_note(self, workspace):
        """Test appending content to daily note."""
        from nanobot.agent.memory.dreaming import DailyNoteManager

        manager = DailyNoteManager(workspace)
        manager.append_to_note("Light Sleep", "- Test candidate")

        note = manager.read_note()
        assert "Light Sleep" in note
        assert "Test candidate" in note


class TestPromotionTracker:
    """Test PromotionTracker functionality."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a temporary workspace."""
        dreams_dir = tmp_path / "memory" / ".dreams"
        dreams_dir.mkdir(parents=True)
        return tmp_path

    def test_mark_promoted(self, workspace):
        """Test marking an entry as promoted."""
        from nanobot.agent.memory.dreaming import PromotionTracker

        tracker = PromotionTracker(workspace)
        tracker.mark_promoted("entry_1")

        assert tracker.is_promoted("entry_1") is True
        assert tracker.is_promoted("entry_2") is False

    def test_get_promoted_count(self, workspace):
        """Test getting promoted count."""
        from nanobot.agent.memory.dreaming import PromotionTracker

        tracker = PromotionTracker(workspace)
        tracker.mark_promoted("entry_1")
        tracker.mark_promoted("entry_2")

        assert tracker.get_promoted_count() == 2


class TestDreamingService:
    """Test DreamingService functionality."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a temporary workspace with memory dir."""
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir(parents=True)
        (mem_dir / "MEMORY.md").write_text("# Memory\nTest fact")
        return tmp_path

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.get_default_model.return_value = "test-model"
        return provider

    def test_dreaming_service_init(self, workspace, mock_provider):
        """Test DreamingService initialization."""
        from nanobot.agent.memory.dreaming import DreamingService

        config = {"enabled": True, "light": {"enabled": True}}
        service = DreamingService(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            config=config,
        )

        assert service.enabled is True
        assert service.recall_store is not None
        assert service.daily_notes is not None
        assert service.promotion_tracker is not None

    def test_dreaming_disabled(self, workspace, mock_provider):
        """Test DreamingService when disabled."""
        from nanobot.agent.memory.dreaming import DreamingService

        config = {"enabled": False}
        service = DreamingService(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            config=config,
        )

        assert service.enabled is False

    @pytest.mark.asyncio
    async def test_run_light_phase(self, workspace, mock_provider):
        """Test Light phase execution."""
        from nanobot.agent.memory.dreaming import DreamingService

        # Add some recall entries first
        store = workspace / "memory" / ".dreams"
        store.mkdir(parents=True, exist_ok=True)
        (store / "short-term-recall.json").write_text(json.dumps([
            {"entry_id": "entry_1", "query": "test query", "score": 1.0, "timestamp": datetime.now().isoformat()},
        ]))

        config = {
            "enabled": True,
            "light": {"enabled": True, "limit": 10},
        }
        service = DreamingService(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            config=config,
        )

        count = await service.run_light_phase()
        # May be 0 if no content to stage, but should not raise

    @pytest.mark.asyncio
    async def test_run_deep_phase_no_promotions(self, workspace, mock_provider):
        """Test Deep phase with no eligible candidates."""
        from nanobot.agent.memory.dreaming import DreamingService

        config = {
            "enabled": True,
            "deep": {"enabled": True, "minScore": 0.8, "minRecallCount": 3},
        }
        service = DreamingService(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            config=config,
        )

        count = await service.run_deep_phase()
        # Should be 0 with no recall data
        assert count == 0

    def test_get_stats(self, workspace, mock_provider):
        """Test getting dreaming statistics."""
        from nanobot.agent.memory.dreaming import DreamingService

        config = {"enabled": True}
        service = DreamingService(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            config=config,
        )

        stats = service.get_stats()

        assert "short_term_recalls" in stats
        assert "promoted_count" in stats
        assert "enabled" in stats

    def test_calculate_promotion_score(self, workspace, mock_provider):
        """Test promotion score calculation."""
        from nanobot.agent.memory.dreaming import DreamingService

        config = {"enabled": True}
        service = DreamingService(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            config=config,
        )

        # High recall count should give higher score
        stats_high = {"count": 10, "avg_score": 0.9, "unique_queries": 5}
        score_high = service._calculate_promotion_score(stats_high, 30)
        assert score_high > 0.5

        # Low recall count should give lower score
        stats_low = {"count": 1, "avg_score": 0.5, "unique_queries": 1}
        score_low = service._calculate_promotion_score(stats_low, 30)
        assert score_low < score_high

    def test_detect_themes(self, workspace, mock_provider):
        """Test theme detection from daily notes."""
        from nanobot.agent.memory.dreaming import DreamingService

        config = {"enabled": True}
        service = DreamingService(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            config=config,
        )

        notes = [
            (datetime.now(), "- topic1: content\n- topic2: more"),
            (datetime.now() - timedelta(days=1), "- topic1: different\n- topic3: stuff"),
        ]

        themes = service._detect_themes(notes, 0.5, 10)

        # topic1 appears in both notes, should be detected
        assert any("topic1" in t for t in themes)

    def test_dedupe_and_rank(self, workspace, mock_provider):
        """Test deduplication and ranking of recalls."""
        from nanobot.agent.memory.dreaming import DreamingService
        from nanobot.agent.memory.dreaming import RecallEntry

        config = {"enabled": True}
        service = DreamingService(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            config=config,
        )

        recalls = [
            RecallEntry("entry_1", "query1", 1.0),
            RecallEntry("entry_1", "query1", 0.9),
            RecallEntry("entry_2", "query2", 0.8),
        ]

        result = service._dedupe_and_rank(recalls, 0.9, 10)

        assert len(result) == 2
        assert result[0].entry_id == "entry_1"

    @pytest.mark.asyncio
    async def test_run_rem_phase_disabled(self, workspace, mock_provider):
        """Test REM phase when disabled."""
        from nanobot.agent.memory.dreaming import DreamingService

        config = {
            "enabled": True,
            "rem": {"enabled": False},
        }
        service = DreamingService(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            config=config,
        )

        count = await service.run_rem_phase()
        assert count == 0

    @pytest.mark.asyncio
    async def test_run_light_phase_disabled(self, workspace, mock_provider):
        """Test Light phase when disabled."""
        from nanobot.agent.memory.dreaming import DreamingService

        config = {
            "enabled": True,
            "light": {"enabled": False},
        }
        service = DreamingService(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            config=config,
        )

        count = await service.run_light_phase()
        assert count == 0

    def test_dreaming_with_timezone(self, workspace, mock_provider):
        """Test DreamingService with timezone configuration."""
        from nanobot.agent.memory.dreaming import DreamingService

        config = {
            "enabled": True,
            "timezone": "Asia/Shanghai",
        }
        service = DreamingService(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            config=config,
        )

        assert service.timezone == "Asia/Shanghai"


class TestMemoryConsolidatorDreaming:
    """Test MemoryConsolidator with Dreaming integration."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a temporary workspace."""
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir(parents=True)
        return tmp_path

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.get_default_model.return_value = "test-model"
        provider.generation.max_tokens = 4096
        return provider

    @pytest.fixture
    def mock_sessions(self):
        """Create a mock session manager."""
        sessions = MagicMock()
        return sessions

    def test_consolidator_with_dreaming(self, workspace, mock_provider, mock_sessions):
        """Test consolidator initializes with dreaming config."""
        from nanobot.agent.memory import MemoryConsolidator

        dreaming_config = {"enabled": True, "light": {"enabled": True}}

        consolidator = MemoryConsolidator(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            sessions=mock_sessions,
            context_window_tokens=65536,
            build_messages=lambda **k: [],
            get_tool_definitions=lambda: [],
            max_completion_tokens=4096,
            dreaming_config=dreaming_config,
        )

        assert consolidator.dreaming is not None
        assert consolidator.dreaming.enabled is True

    def test_consolidator_without_dreaming(self, workspace, mock_provider, mock_sessions):
        """Test consolidator without dreaming config."""
        from nanobot.agent.memory import MemoryConsolidator

        consolidator = MemoryConsolidator(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            sessions=mock_sessions,
            context_window_tokens=65536,
            build_messages=lambda **k: [],
            get_tool_definitions=lambda: [],
            max_completion_tokens=4096,
        )

        assert consolidator.dreaming is None

    def test_get_dreaming_stats(self, workspace, mock_provider, mock_sessions):
        """Test getting dreaming stats from consolidator."""
        from nanobot.agent.memory import MemoryConsolidator

        dreaming_config = {"enabled": True}

        consolidator = MemoryConsolidator(
            workspace=workspace,
            provider=mock_provider,
            model="test-model",
            sessions=mock_sessions,
            context_window_tokens=65536,
            build_messages=lambda **k: [],
            get_tool_definitions=lambda: [],
            max_completion_tokens=4096,
            dreaming_config=dreaming_config,
        )

        stats = consolidator.get_dreaming_stats()

        assert stats["enabled"] is True
        assert "short_term_recalls" in stats


class TestMemoryToolDreaming:
    """Test MemoryTool with Dreaming integration."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a temporary workspace."""
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir(parents=True)
        return tmp_path

    @pytest.fixture
    def mock_consolidator(self):
        """Create a mock consolidator with dreaming."""
        from nanobot.agent.memory import MemoryConsolidator

        consolidator = MagicMock()
        consolidator.dreaming = MagicMock()
        consolidator.dreaming.recall_store = MagicMock()
        consolidator.get_dreaming_stats.return_value = {
            "enabled": True,
            "short_term_recalls": 5,
            "promoted_count": 2,
        }
        return consolidator

    @pytest.mark.asyncio
    async def test_memory_tool_dreaming_action(self, workspace, mock_consolidator):
        """Test MemoryTool dreaming action."""
        from nanobot.agent.tools.memory import MemoryTool

        tool = MemoryTool(
            workspace=workspace,
            consolidator=mock_consolidator,
        )

        result = await tool.execute(action="dreaming")

        assert "Dreaming Status" in result
        assert "Short-term recalls: 5" in result
        assert "Promoted entries: 2" in result

    @pytest.mark.asyncio
    async def test_memory_tool_recall_tracking(self, workspace, mock_consolidator):
        """Test MemoryTool tracks recalls on search."""
        from nanobot.agent.tools.memory import MemoryTool

        tool = MemoryTool(
            workspace=workspace,
            consolidator=mock_consolidator,
        )

        await tool.execute(action="search", query="test")

        # Verify recall was tracked
        mock_consolidator.dreaming.recall_store.add_recall.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_tool_dreaming_disabled(self, workspace):
        """Test MemoryTool when dreaming is not enabled."""
        from nanobot.agent.tools.memory import MemoryTool
        from nanobot.agent.memory import MemoryConsolidator

        consolidator = MagicMock()
        consolidator.dreaming = None

        tool = MemoryTool(workspace=workspace, consolidator=consolidator)

        result = await tool.execute(action="dreaming")

        assert result == "Dreaming is not enabled"