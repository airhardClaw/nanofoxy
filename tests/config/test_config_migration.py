import json

import pytest

from nanobot.config.loader import load_config, save_config


def test_load_config_keeps_max_tokens_and_ignores_legacy_memory_window(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "agents": {
                    "defaults": {
                        "maxTokens": 1234,
                        "memoryWindow": 42,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.agents.defaults.max_tokens == 1234
    assert config.agents.defaults.context_window_tokens == 32_000  # Optimized for Liquid AI LFM2.5
    assert not hasattr(config.agents.defaults, "memory_window")


def test_save_config_writes_context_window_tokens_but_not_memory_window(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "agents": {
                    "defaults": {
                        "maxTokens": 2222,
                        "memoryWindow": 30,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)
    save_config(config, config_path)
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    defaults = saved["agents"]["defaults"]

    assert defaults["maxTokens"] == 2222


def test_default_memory_config(tmp_path) -> None:
    """Test default memory configuration values."""
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    config = load_config(config_path)

    assert config.tools.memory.backend == "builtin"
    assert config.tools.memory.dreaming.enabled is True
    assert config.tools.memory.dreaming.light.cron == "0 */6 * * *"
    assert config.tools.memory.dreaming.deep.cron == "0 3 * * *"
    assert config.tools.memory.dreaming.rem.cron == "0 5 * * 0"


def test_memory_dreaming_config_parsing(tmp_path) -> None:
    """Test parsing of memory.dreaming configuration."""
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "tools": {
                    "memory": {
                        "backend": "qmd",
                        "dreaming": {
                            "enabled": False,
                            "timezone": "Asia/Tokyo",
                            "deep": {
                                "minScore": 0.9,
                                "minRecallCount": 5,
                            },
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.tools.memory.backend == "qmd"
    assert config.tools.memory.dreaming.enabled is False
    assert config.tools.memory.dreaming.timezone == "Asia/Tokyo"
    assert config.tools.memory.dreaming.deep.min_score == 0.9
    assert config.tools.memory.dreaming.deep.min_recall_count == 5


def test_save_and_load_memory_config(tmp_path) -> None:
    """Test saving and loading memory configuration."""
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    config = load_config(config_path)

    config.tools.memory.backend = "qmd"
    config.tools.memory.dreaming.enabled = True
    config.tools.memory.dreaming.light.cron = "0 */3 * * *"

    save_config(config, config_path)

    loaded = load_config(config_path)

    assert loaded.tools.memory.backend == "qmd"
    assert loaded.tools.memory.dreaming.enabled is True
    assert loaded.tools.memory.dreaming.light.cron == "0 */3 * * *"


def test_onboard_does_not_crash_with_legacy_memory_window(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    workspace = tmp_path / "workspace"
    config_path.write_text(
        json.dumps(
            {
                "agents": {
                    "defaults": {
                        "maxTokens": 3333,
                        "memoryWindow": 50,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("nanobot.config.loader.get_config_path", lambda: config_path)
    monkeypatch.setattr("nanobot.cli.commands.get_workspace_path", lambda _workspace=None: workspace)

    from typer.testing import CliRunner
    from nanobot.cli.commands import app
    runner = CliRunner()
    result = runner.invoke(app, ["onboard"], input="n\n")

    assert result.exit_code == 0


def test_onboard_refresh_backfills_missing_channel_fields(tmp_path, monkeypatch) -> None:
    from types import SimpleNamespace

    config_path = tmp_path / "config.json"
    workspace = tmp_path / "workspace"
    config_path.write_text(
        json.dumps(
            {
                "channels": {
                    "qq": {
                        "enabled": False,
                        "appId": "",
                        "secret": "",
                        "allowFrom": [],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("nanobot.config.loader.get_config_path", lambda: config_path)
    monkeypatch.setattr("nanobot.cli.commands.get_workspace_path", lambda _workspace=None: workspace)
    monkeypatch.setattr(
        "nanobot.channels.registry.discover_all",
        lambda: {
            "qq": SimpleNamespace(
                default_config=lambda: {
                    "enabled": False,
                    "appId": "",
                    "secret": "",
                    "allowFrom": [],
                    "msgFormat": "plain",
                }
            )
        },
    )

    from typer.testing import CliRunner
    from nanobot.cli.commands import app
    runner = CliRunner()
    result = runner.invoke(app, ["onboard"], input="n\n")

    assert result.exit_code == 0
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["channels"]["qq"]["msgFormat"] == "plain"
