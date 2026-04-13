"""Telegram channel implementation using python-telegram-bot."""

from __future__ import annotations

import asyncio
import json
import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from loguru import logger
from pydantic import Field
from telegram import (
    Bot,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReactionTypeEmoji,
    ReplyParameters,
    Update,
)
from telegram.error import BadRequest, TimedOut
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    MessageReactionHandler,
    filters,
)
from telegram.request import HTTPXRequest

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.paths import get_media_dir
from nanobot.config.schema import Base
from nanobot.security.network import validate_url_target
from nanobot.utils.helpers import split_message

TELEGRAM_MAX_MESSAGE_LEN = 4000  # Telegram message character limit
TELEGRAM_REPLY_CONTEXT_MAX_LEN = TELEGRAM_MAX_MESSAGE_LEN  # Max length for reply context in user message


def _strip_md(s: str) -> str:
    """Strip markdown inline formatting from text."""
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
    s = re.sub(r'__(.+?)__', r'\1', s)
    s = re.sub(r'~~(.+?)~~', r'\1', s)
    s = re.sub(r'`([^`]+)`', r'\1', s)
    return s.strip()


def _render_table_box(table_lines: list[str]) -> str:
    """Convert markdown pipe-table to compact aligned text for <pre> display."""

    def dw(s: str) -> int:
        return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in s)

    rows: list[list[str]] = []
    has_sep = False
    for line in table_lines:
        cells = [_strip_md(c) for c in line.strip().strip('|').split('|')]
        if all(re.match(r'^:?-+:?$', c) for c in cells if c):
            has_sep = True
            continue
        rows.append(cells)
    if not rows or not has_sep:
        return '\n'.join(table_lines)

    ncols = max(len(r) for r in rows)
    for r in rows:
        r.extend([''] * (ncols - len(r)))
    widths = [max(dw(r[c]) for r in rows) for c in range(ncols)]

    def dr(cells: list[str]) -> str:
        return '  '.join(f'{c}{" " * (w - dw(c))}' for c, w in zip(cells, widths))

    out = [dr(rows[0])]
    out.append('  '.join('─' * w for w in widths))
    for row in rows[1:]:
        out.append(dr(row))
    return '\n'.join(out)


def _markdown_to_telegram_html(text: str) -> str:
    """
    Convert markdown to Telegram-safe HTML.
    """
    if not text:
        return ""

    # 1. Extract and protect code blocks (preserve content from other processing)
    code_blocks: list[str] = []
    def save_code_block(m: re.Match) -> str:
        code_blocks.append(m.group(1))
        return f"\x00CB{len(code_blocks) - 1}\x00"

    text = re.sub(r'```[\w]*\n?([\s\S]*?)```', save_code_block, text)

    # 1.5. Convert markdown tables to box-drawing (reuse code_block placeholders)
    lines = text.split('\n')
    rebuilt: list[str] = []
    li = 0
    while li < len(lines):
        if re.match(r'^\s*\|.+\|', lines[li]):
            tbl: list[str] = []
            while li < len(lines) and re.match(r'^\s*\|.+\|', lines[li]):
                tbl.append(lines[li])
                li += 1
            box = _render_table_box(tbl)
            if box != '\n'.join(tbl):
                code_blocks.append(box)
                rebuilt.append(f"\x00CB{len(code_blocks) - 1}\x00")
            else:
                rebuilt.extend(tbl)
        else:
            rebuilt.append(lines[li])
            li += 1
    text = '\n'.join(rebuilt)

    # 2. Extract and protect inline code
    inline_codes: list[str] = []
    def save_inline_code(m: re.Match) -> str:
        inline_codes.append(m.group(1))
        return f"\x00IC{len(inline_codes) - 1}\x00"

    text = re.sub(r'`([^`]+)`', save_inline_code, text)

    # 3. Headers # Title -> just the title text
    text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)

    # 4. Blockquotes > text -> just the text (before HTML escaping)
    text = re.sub(r'^>\s*(.*)$', r'\1', text, flags=re.MULTILINE)

    # 5. Escape HTML special characters
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # 6. Links [text](url) - must be before bold/italic to handle nested cases
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    # 7. Bold **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)

    # 8. Italic _text_ (avoid matching inside words like some_var_name)
    text = re.sub(r'(?<![a-zA-Z0-9])_([^_]+)_(?![a-zA-Z0-9])', r'<i>\1</i>', text)

    # 9. Strikethrough ~~text~~
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)

    # 10. Bullet lists - item -> • item
    text = re.sub(r'^[-*]\s+', '• ', text, flags=re.MULTILINE)

    # 11. Restore inline code with HTML tags
    for i, code in enumerate(inline_codes):
        # Escape HTML in code content
        escaped = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace(f"\x00IC{i}\x00", f"<code>{escaped}</code>")

    # 12. Restore code blocks with HTML tags
    for i, code in enumerate(code_blocks):
        # Escape HTML in code content
        escaped = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace(f"\x00CB{i}\x00", f"<pre><code>{escaped}</code></pre>")

    return text


_SEND_MAX_RETRIES = 3
_SEND_RETRY_BASE_DELAY = 0.5  # seconds, doubled each retry


@dataclass
class _StreamBuf:
    """Per-chat streaming accumulator for progressive message editing."""
    text: str = ""
    message_id: int | None = None
    last_edit: float = 0.0
    stream_id: str | None = None


class TelegramCapabilities(Base):
    """Telegram capabilities configuration."""

    inline_buttons: Literal["off", "dm", "group", "all", "allowlist"] = "allowlist"


class TelegramActions(Base):
    """Telegram message actions (tool gating)."""

    send_message: bool = True
    delete_message: bool = True
    reactions: bool = True
    sticker: bool = False
    poll: bool = True


class TelegramRetry(Base):
    """Telegram retry configuration for send helpers."""

    attempts: int = 3
    min_delay_seconds: float = 0.5
    max_delay_seconds: float = 5.0
    jitter: bool = True


class TelegramCommands(Base):
    """Telegram command configuration."""

    native: bool = True
    native_skills: bool = True


class TelegramExecApprovals(Base):
    """Telegram exec approvals configuration."""

    enabled: bool = False
    mode: Literal["supervised", "yolo"] = "supervised"
    approvers: list[str] = Field(default_factory=list)
    target: Literal["dm", "channel", "both"] = "dm"
    agent_filter: str | None = None
    session_filter: str | None = None


class TelegramTopicConfig(Base):
    """Per-topic Telegram configuration (inherits from group)."""

    group_policy: Literal["open", "mention", "allowlist", "disabled"] | None = None
    require_mention: bool | None = None
    allow_from: list[str] | None = None
    skills: list[str] | None = None
    system_prompt: str | None = None
    enabled: bool | None = None
    agent_id: str | None = None
    acp_session_key: str | None = None  # ACP session bound to this topic


class TelegramGroupConfig(Base):
    """Per-group Telegram configuration."""

    group_policy: Literal["open", "mention", "allowlist", "disabled"] | None = None
    require_mention: bool | None = None
    allow_from: list[str] | None = None
    skills: list[str] | None = None
    system_prompt: str | None = None
    enabled: bool | None = None
    topics: dict[str, TelegramTopicConfig] = Field(default_factory=dict)


class TelegramConfig(Base):
    """Telegram channel configuration."""

    enabled: bool = False
    token: str = ""
    allow_from: list[str] = Field(default_factory=list)
    proxy: str | None = None
    reply_to_message: bool = False
    react_emoji: str = "👀"
    group_policy: Literal["open", "mention"] = "mention"
    connection_pool_size: int = 32
    pool_timeout: float = 5.0
    streaming: bool = True

    # Access Control
    dm_policy: Literal["allowlist", "open", "disabled"] = "allowlist"
    group_allow_from: list[str] = Field(default_factory=list)

    # Capabilities & Actions
    capabilities: TelegramCapabilities = Field(default_factory=TelegramCapabilities)
    actions: TelegramActions = Field(default_factory=TelegramActions)

    # Delivery & Format
    text_chunk_limit: int = 4000
    chunk_mode: Literal["length", "newline"] = "length"
    link_preview: bool = True
    reply_to_mode: Literal["off", "first", "all"] = "off"

    # Media & Network
    media_max_mb: int = 100
    timeout_seconds: float = 30.0
    retry: TelegramRetry = Field(default_factory=TelegramRetry)

    # Streaming (extended)
    stream_mode: Literal["off", "partial", "block", "progress"] = "partial"

    # Reaction Notifications
    reaction_notifications: Literal["off", "own", "all"] = "own"
    reaction_level: Literal["off", "ack", "minimal", "extensive"] = "minimal"

    # Exec Approvals
    exec_approvals: TelegramExecApprovals = Field(default_factory=TelegramExecApprovals)

    # Error Policy
    error_policy: Literal["reply", "silent"] = "reply"
    error_cooldown_seconds: int = 60

    # Commands
    commands: TelegramCommands = Field(default_factory=TelegramCommands)
    custom_commands: list[dict[str, str]] = Field(default_factory=list)

    # Config Writes
    config_writes: bool = True

    # Per-group and per-topic overrides
    groups: dict[str, TelegramGroupConfig] = Field(default_factory=dict)

    # ACP Thread Bindings
    thread_bindings: bool = False  # Enable ACP thread binding for topics


class TelegramChannel(BaseChannel):
    """
    Telegram channel using long polling.

    Simple and reliable - no webhook/public IP needed.

    Supports subagent mentions via @subagent_name.
    Subagent configs are loaded from workspace/.subagents/
    """

    name = "telegram"
    display_name = "Telegram"

    # Commands registered with Telegram's command menu
    BOT_COMMANDS = [
        BotCommand("start", "Start the bot"),
        BotCommand("new", "Start a new conversation"),
        BotCommand("stop", "Stop the current task"),
        BotCommand("restart", "Restart the bot"),
        BotCommand("status", "Show bot status"),
        BotCommand("skills", "List available skills"),
        BotCommand("help", "Show available commands"),
    ]

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return TelegramConfig().model_dump(by_alias=True)

    _STREAM_EDIT_INTERVAL = 0.6  # min seconds between edit_message_text calls

    def __init__(self, config: Any, bus: MessageBus, workspace: str | None = None):
        if isinstance(config, dict):
            config = TelegramConfig.model_validate(config)
        super().__init__(config, bus)
        self.config: TelegramConfig = config
        self.workspace = Path(workspace) if workspace else None
        self._app: Application | None = None
        self._chat_ids: dict[str, int] = {}  # Map sender_id to chat_id for replies
        self._typing_tasks: dict[str, asyncio.Task] = {}  # chat_id -> typing loop task
        self._media_group_buffers: dict[str, dict] = {}
        self._media_group_tasks: dict[str, asyncio.Task] = {}
        self._message_threads: dict[tuple[str, int], int] = {}
        self._bot_user_id: int | None = None
        self._bot_username: str | None = None
        self._stream_bufs: dict[str, _StreamBuf] = {}  # chat_id -> streaming state
        self._subagent_configs: dict[str, dict] = {}
        self._subagent_apps: dict[str, "Application"] = {}  # subagent_id -> Application (for polling)
        self._last_error_time: dict[str, float] = {}  # chat_id -> last error timestamp
        self._pending_approvals: dict[str, dict] = {}  # request_id -> approval request data
        self._exec_approval_cleanup_task: asyncio.Task | None = None

    def is_allowed(self, sender_id: str) -> bool:
        """Preserve Telegram's legacy id|username allowlist matching."""
        if super().is_allowed(sender_id):
            return True

        allow_list = getattr(self.config, "allow_from", [])
        if not allow_list or "*" in allow_list:
            return False

        sender_str = str(sender_id)
        if sender_str.count("|") != 1:
            return False

        sid, username = sender_str.split("|", 1)
        if not sid.isdigit() or not username:
            return False

        return sid in allow_list or username in allow_list

    async def start(self) -> None:
        """Start the Telegram bot with long polling."""
        if not self.config.token:
            logger.error("Telegram bot token not configured")
            return

        self._running = True

        proxy = self.config.proxy or None

        # Separate pools so long-polling (getUpdates) never starves outbound sends.
        api_request = HTTPXRequest(
            connection_pool_size=self.config.connection_pool_size,
            pool_timeout=self.config.pool_timeout,
            connect_timeout=30.0,
            read_timeout=30.0,
            proxy=proxy,
        )
        poll_request = HTTPXRequest(
            connection_pool_size=4,
            pool_timeout=self.config.pool_timeout,
            connect_timeout=30.0,
            read_timeout=30.0,
            proxy=proxy,
        )
        builder = (
            Application.builder()
            .token(self.config.token)
            .request(api_request)
            .get_updates_request(poll_request)
        )
        self._app = builder.build()
        self._app.add_error_handler(self._on_error)

        # Load subagent configurations and initialize subagent bots
        await self._init_subagent_bots()

        # Load config overrides from file
        await self._load_config_overrides()

        # Add command handlers
        self._app.add_handler(CommandHandler("start", self._on_start))
        self._app.add_handler(CommandHandler("new", self._forward_command))
        self._app.add_handler(CommandHandler("stop", self._forward_command))
        self._app.add_handler(CommandHandler("restart", self._forward_command))
        self._app.add_handler(CommandHandler("status", self._forward_command))
        self._app.add_handler(CommandHandler("skills", self._forward_command))
        self._app.add_handler(CommandHandler("help", self._on_help))

        # Add config commands if enabled
        if self.config.config_writes:
            self._app.add_handler(CommandHandler("config", self._on_config))

        # Add exec approval commands if enabled
        if self.config.exec_approvals.enabled and self.config.exec_approvals.mode == "supervised":
            self._app.add_handler(CommandHandler("approve", self._on_approve))
            self._app.add_handler(CommandHandler("deny", self._on_deny))
            # Start approval cleanup task
            self._exec_approval_cleanup_task = asyncio.create_task(self._cleanup_expired_approvals())

        # Add callback query handler for inline buttons
        self._app.add_handler(CallbackQueryHandler(self._on_callback_query))

        # Add message reaction handler if enabled
        if self.config.reaction_notifications != "off":
            self._app.add_handler(MessageReactionHandler(self._on_message_reaction))

        # Add message handler for text, photos, voice, documents
        self._app.add_handler(
            MessageHandler(
                (filters.TEXT | filters.PHOTO | filters.VOICE | filters.AUDIO | filters.Document.ALL)
                & ~filters.COMMAND,
                self._on_message
            )
        )

        logger.info("Starting Telegram bot (polling mode)...")

        # Initialize and start polling
        await self._app.initialize()
        await self._app.start()

        # Get bot info and register command menu
        bot_info = await self._app.bot.get_me()
        self._bot_user_id = getattr(bot_info, "id", None)
        self._bot_username = getattr(bot_info, "username", None)
        logger.info("Telegram bot @{} connected", bot_info.username)

        # Register commands (native + custom)
        await self._register_commands()

        # Start polling with appropriate allowed_updates
        allowed_updates = ["message"]
        if self.config.reaction_notifications != "off":
            allowed_updates.append("message_reaction")

        await self._app.updater.start_polling(
            allowed_updates=allowed_updates,
            drop_pending_updates=True  # Ignore old messages on startup
        )

        # Keep running until stopped
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop the Telegram bot."""
        self._running = False

        # Cancel all typing indicators
        for chat_id in list(self._typing_tasks):
            self._stop_typing(chat_id)

        for task in self._media_group_tasks.values():
            task.cancel()
        self._media_group_tasks.clear()
        self._media_group_buffers.clear()

        # Cancel exec approval cleanup task
        if self._exec_approval_cleanup_task:
            self._exec_approval_cleanup_task.cancel()
            self._exec_approval_cleanup_task = None

        if self._app:
            logger.info("Stopping Telegram bot...")
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            self._app = None

        # Stop all subagent bots
        for subagent_id in list(self._subagent_apps.keys()):
            await self._stop_subagent_bot(subagent_id)

    async def _init_subagent_bots(self) -> None:
        """Initialize subagent bots from workspace/.subagents/ config."""
        if not self.workspace:
            return

        import json
        subagent_dir = self.workspace / ".subagents"

        if not subagent_dir.exists():
            return

        # Load main config
        config_file = subagent_dir / "config.json"
        group_chat = ""
        if config_file.exists():
            try:
                main_config = json.loads(config_file.read_text(encoding="utf-8"))
                group_chat = main_config.get("group_chat", "")
            except json.JSONDecodeError:
                pass

        # Load individual subagent configs and START EACH BOT
        for config_file in subagent_dir.glob("*.json"):
            if config_file.name == "config.json" or config_file.name.startswith("_"):
                continue
            try:
                subagent_config = json.loads(config_file.read_text(encoding="utf-8"))
                subagent_id = config_file.stem

                # Check if subagent is enabled and has a bot token
                if subagent_config.get("enabled", True) and subagent_config.get("bot_token"):
                    bot_token = subagent_config["bot_token"]
                    if bot_token and bot_token != "MANUELL_EINTRAGEN":
                        # Start the subagent bot with its own polling loop
                        await self._start_subagent_bot(subagent_id, bot_token, subagent_config, group_chat)
                        logger.info("Subagent bot {} started", subagent_id)
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse subagent config {}: {}", config_file.name, e)

    async def _start_subagent_bot(
        self,
        subagent_id: str,
        bot_token: str,
        subagent_config: dict,
        group_chat: str
    ) -> None:
        """Create and start a subagent bot with its own polling loop."""
        from telegram.ext import Application, CommandHandler, MessageHandler, filters

        proxy = self.config.proxy or None

        # Create HTTP request with proxy support
        request = HTTPXRequest(
            connection_pool_size=4,
            pool_timeout=5.0,
            connect_timeout=10.0,
            read_timeout=30.0,
            proxy=proxy,
        )

        # Create the Application (like main bot)
        app = (
            Application.builder()
            .token(bot_token)
            .request(request)
            .build()
        )

        # Add message handler for this subagent
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            lambda u, c: self._subagent_on_message(u, c, subagent_id)
        ))

        # Add command handlers for this subagent
        app.add_handler(CommandHandler("start", lambda u, c: self._subagent_on_command(u, c, subagent_id, "start")))
        app.add_handler(CommandHandler("help", lambda u, c: self._subagent_on_command(u, c, subagent_id, "help")))
        app.add_handler(CommandHandler("new", lambda u, c: self._subagent_on_command(u, c, subagent_id, "new")))
        app.add_handler(CommandHandler("stop", lambda u, c: self._subagent_on_command(u, c, subagent_id, "stop")))
        app.add_handler(CommandHandler("restart", lambda u, c: self._subagent_on_command(u, c, subagent_id, "restart")))
        app.add_handler(CommandHandler("status", lambda u, c: self._subagent_on_command(u, c, subagent_id, "status")))
        app.add_handler(CommandHandler("skills", lambda u, c: self._subagent_on_command(u, c, subagent_id, "skills")))

        # Store the app for this subagent
        self._subagent_apps[subagent_id] = app

        # Store config
        self._subagent_configs[subagent_id] = {
            **subagent_config,
            "group_chat": group_chat,
        }

        # Start polling for this subagent
        await app.initialize()
        await app.start()
        await app.updater.start_polling(
            allowed_updates=["message"],
            drop_pending_updates=True
        )

        # Create Bot instance for this subagent to register commands
        subagent_bot = Bot(token=bot_token, request=request)

        # Register bot commands for this subagent
        try:
            await subagent_bot.set_my_commands(self.BOT_COMMANDS)
            logger.info("Subagent bot {} commands registered", subagent_id)
        except Exception as e:
            logger.warning("Failed to register commands for subagent {}: {}", subagent_id, e)

        logger.info("Subagent bot {} polling started", subagent_id)

    async def _subagent_on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, subagent_id: str) -> None:
        """Handle incoming message for a subagent bot."""
        if not update.message or not update.effective_user:
            return

        message = update.message
        user = update.effective_user
        chat_id = str(message.chat_id)
        sender_id = self._sender_id(user)

        # Get subagent config
        subagent_config = self._subagent_configs.get(subagent_id, {})
        allowed_chats = subagent_config.get("allowed_chats", [])
        allowed_from = subagent_config.get("allow_from", [])

        # Check if sender is allowed
        sender_id_clean = sender_id.split("|")[0] if "|" in sender_id else sender_id

        # Check chat permission
        if allowed_chats and chat_id not in allowed_chats:
            logger.debug("Subagent {}: chat {} not allowed", subagent_id, chat_id)
            return

        # Check sender permission
        if allowed_from and sender_id_clean not in allowed_from:
            logger.debug("Subagent {}: sender {} not allowed", subagent_id, sender_id_clean)
            return

        # Get task content (everything after the bot mention)
        task = message.text or ""

        # Route to subagent via message bus
        metadata = {
            "_subagent_id": subagent_id,
            "_subagent_role": subagent_config.get("role", ""),
            "_subagent_task": task,
            "message_id": message.message_id,
        }

        await self._handle_message(
            sender_id=sender_id,
            chat_id=chat_id,
            content=f"[Subagent: {subagent_id}]\n{task}",
            metadata=metadata,
        )

        # Start typing indicator
        self._start_typing(chat_id)

    async def _subagent_on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, subagent_id: str, command: str) -> None:
        """Handle command for a subagent bot."""
        if not update.message or not update.effective_user:
            return

        message = update.message
        user = update.effective_user
        chat_id = str(message.chat_id)
        sender_id = self._sender_id(user)

        subagent_config = self._subagent_configs.get(subagent_id, {})
        allowed_from = subagent_config.get("allow_from", [])

        sender_id_clean = sender_id.split("|")[0] if "|" in sender_id else sender_id

        # Check sender permission
        if allowed_from and sender_id_clean not in allowed_from:
            return

        task = f"/{command}"
        metadata = {
            "_subagent_id": subagent_id,
            "_subagent_role": subagent_config.get("role", ""),
            "_subagent_task": task,
            "message_id": message.message_id,
        }

        await self._handle_message(
            sender_id=sender_id,
            chat_id=chat_id,
            content=f"[Subagent: {subagent_id}]\n{task}",
            metadata=metadata,
        )

        self._start_typing(chat_id)

    async def _stop_subagent_bot(self, subagent_id: str) -> None:
        """Stop a subagent bot."""
        if subagent_id in self._subagent_apps:
            app = self._subagent_apps[subagent_id]
            try:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
            except Exception as e:
                logger.warning("Error stopping subagent bot {}: {}", subagent_id, e)
            del self._subagent_apps[subagent_id]

        if subagent_id in self._subagent_configs:
            del self._subagent_configs[subagent_id]

        logger.info("Subagent bot {} stopped", subagent_id)

    def _extract_subagent_mention(self, text: str) -> str | None:
        """Extract @subagent_name from message text.

        Handles:
        - Regular mentions: "@coding_expert help me"
        - Bot username: "@XRP4uBot help me" (bot_username from config)
        - Bot commands: "/help@coding_expert" or "/help@XRP4uBot"

        Returns subagent_id if found, None otherwise.
        """
        match = re.search(r'@(\w+)', text)
        if not match:
            return None

        username = match.group(1).lower()

        # Check if it matches a known subagent
        for subagent_id, config in self._subagent_configs.items():
            # 1. Compare with subagent_id (with/without underscores)
            if (subagent_id.lower().replace("_", "") == username.replace("_", "") or
                subagent_id.lower() == username):
                return subagent_id

            # 2. Compare with bot_username (e.g., "XRP4uBot")
            bot_username = (config.get("bot_username") or "").lower().replace("@", "")
            if bot_username and bot_username == username:
                return subagent_id

        return None

    async def _route_to_subagent(
        self,
        subagent_id: str,
        message_text: str,
        chat_id: str,
        sender_id: str,
        metadata: dict,
    ) -> bool:
        """Route a message to a specific subagent.

        Returns True if message was routed to subagent, False otherwise.
        """
        if subagent_id not in self._subagent_configs:
            return False

        subagent_config = self._subagent_configs[subagent_id]

        # Check if sender is allowed
        allowed_from = subagent_config.get("allow_from", [])
        allowed_chats = subagent_config.get("allowed_chats", [])

        # Check chat permission
        if allowed_chats and chat_id not in allowed_chats:
            logger.warning("Subagent {}: chat {} not allowed", subagent_id, chat_id)
            return False

        # Check sender permission (if allow_from is set)
        if allowed_from:
            # Parse sender_id (format: "id|username" or just "id")
            sender_id_clean = sender_id.split("|")[0] if "|" in sender_id else sender_id
            if sender_id_clean not in allowed_from:
                logger.warning("Subagent {}: sender {} not allowed", subagent_id, sender_id)
                return False

        # Check if subagent responds to mentions
        if not subagent_config.get("respond_to_mentions", True):
            return False

        # Extract the task from the message (remove @subagent_name)
        import re
        task = re.sub(r'@\w+\s*', '', message_text, count=1).strip()

        if not task:
            # Just mention without task - send help info
            task = "Zeige deine Fähigkeiten und Rolle"

        # Route to chief agent with subagent context
        logger.info("Routing message to subagent {} in chat {}", subagent_id, chat_id)

        # Build metadata with subagent info
        subagent_metadata = {
            **metadata,
            "_subagent_id": subagent_id,
            "_subagent_role": subagent_config.get("role", ""),
            "_subagent_task": task,
        }

        # Forward to message bus
        await self._handle_message(
            sender_id=sender_id,
            chat_id=chat_id,
            content=f"[Subagent: {subagent_id}]\n{task}",
            metadata=subagent_metadata,
        )

        return True

    @staticmethod
    def _get_media_type(path: str) -> str:
        """Guess media type from file extension."""
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if ext in ("jpg", "jpeg", "png", "gif", "webp"):
            return "photo"
        if ext == "ogg":
            return "voice"
        if ext in ("mp3", "m4a", "wav", "aac"):
            return "audio"
        return "document"

    @staticmethod
    def _is_remote_media_url(path: str) -> bool:
        return path.startswith(("http://", "https://"))

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through Telegram."""
        logger.debug("TelegramChannel.send() called: chat_id={}, from_subagent={}, subagent_id={}",
            msg.chat_id, msg.metadata.get("_from_subagent"), msg.metadata.get("_subagent_id"))

        # Check if sending messages is allowed
        if not self.can_send_message():
            logger.warning("Sending messages is disabled in config")
            return

        # Determine which bot to use: subagent or chief
        bot = self._app.bot  # Default: chief bot

        # Check if this is a subagent response
        if msg.metadata.get("_from_subagent"):
            # Get subagent role (e.g., "information-expert")
            subagent_role = msg.metadata.get("_subagent_id", "")
            if not subagent_role:
                subagent_role = msg.metadata.get("_subagent_label", "").replace(" ", "-").lower()

            logger.debug("Looking for subagent with role: {}", subagent_role)

            # Try to find subagent by matching role in configs - with proper fallback
            found_subagent = None
            for sa_id, sa_config in self._subagent_configs.items():
                config_role = sa_config.get("role", "").replace(" ", "-").lower()
                if config_role == subagent_role:
                    if sa_id in self._subagent_apps:
                        found_subagent = sa_id
                        break

            if found_subagent:
                bot = self._subagent_apps[found_subagent].bot
                logger.info("Sending response via subagent bot: {} (role={})", found_subagent, subagent_role)
            else:
                logger.warning("Subagent bot not found for role: '{}', using chief bot", subagent_role)

        if not self._app:
            logger.warning("Telegram bot not running")
            return

        # Only stop typing indicator for final responses
        if not msg.metadata.get("_progress", False):
            self._stop_typing(msg.chat_id)

        try:
            chat_id = int(msg.chat_id)
        except ValueError:
            logger.error("Invalid chat_id: {}", msg.chat_id)
            return
        reply_to_message_id = msg.metadata.get("message_id")
        message_thread_id = msg.metadata.get("message_thread_id")
        if message_thread_id is None and reply_to_message_id is not None:
            message_thread_id = self._message_threads.get((msg.chat_id, reply_to_message_id))

        # Handle reply_to_mode
        thread_kwargs = {}
        if message_thread_id is not None:
            thread_kwargs["message_thread_id"] = message_thread_id

        # Determine reply parameters based on reply_to_mode
        reply_params = None
        if self.config.reply_to_message or self.config.reply_to_mode != "off":
            if reply_to_message_id:
                reply_params = ReplyParameters(
                    message_id=reply_to_message_id,
                    allow_sending_without_reply=True
                )

        # Build inline keyboard if buttons are provided
        reply_markup = None
        if msg.buttons:
            keyboard = []
            for row in msg.buttons:
                button_row = []
                for button in row:
                    if isinstance(button, dict):
                        button_row.append(InlineKeyboardButton(
                            text=button.get("text", ""),
                            callback_data=button.get("callback_data") or button.get("data", "")
                        ))
                    else:
                        # Assume simple string, convert to button
                        button_row.append(InlineKeyboardButton(text=str(button), callback_data=str(button)))
                keyboard.append(button_row)
            if keyboard:
                reply_markup = InlineKeyboardMarkup(keyboard)

        # Send media files
        for media_path in (msg.media or []):
            try:
                # Check media size limit
                media_size = 0
                if not self._is_remote_media_url(media_path):
                    try:
                        media_size = Path(media_path).stat().st_size
                    except Exception:
                        pass

                if media_size > self.config.media_max_mb * 1024 * 1024:
                    logger.warning("Media too large ({}MB limit): {}", self.config.media_max_mb, media_path)
                    continue

                media_type = self._get_media_type(media_path)
                sender = {
                    "photo": bot.send_photo,
                    "voice": bot.send_voice,
                    "audio": bot.send_audio,
                }.get(media_type, bot.send_document)
                param = "photo" if media_type == "photo" else media_type if media_type in ("voice", "audio") else "document"

                # Telegram Bot API accepts HTTP(S) URLs directly for media params.
                if self._is_remote_media_url(media_path):
                    ok, error = validate_url_target(media_path)
                    if not ok:
                        raise ValueError(f"unsafe media URL: {error}")
                    await self._call_with_retry(
                        sender,
                        chat_id=chat_id,
                        **{param: media_path},
                        reply_parameters=reply_params,
                        reply_markup=reply_markup,
                        **thread_kwargs,
                    )
                    continue

                with open(media_path, "rb") as f:
                    await sender(
                        chat_id=chat_id,
                        **{param: f},
                        reply_parameters=reply_params,
                        reply_markup=reply_markup,
                        **thread_kwargs,
                    )
                # Clear reply_markup after first media send (only show buttons on first message)
                reply_markup = None
            except Exception as e:
                filename = media_path.rsplit("/", 1)[-1]
                logger.error("Failed to send media {}: {}", media_path, e)
                try:
                    await self._app.bot.send_message(
                        chat_id=chat_id,
                        text=f"[Failed to send: {filename}]",
                        reply_parameters=reply_params,
                        **thread_kwargs,
                    )
                except Exception as e2:
                    logger.error("Failed to send error notification: {}", e2)

        # Send text content with chunking based on chunk_mode
        if msg.content and msg.content != "[empty message]":
            if self.config.chunk_mode == "newline":
                chunks = self._split_message_on_newlines(msg.content, self.config.text_chunk_limit)
            else:
                chunks = split_message(msg.content, self.config.text_chunk_limit)

            for i, chunk in enumerate(chunks):
                # Only add reply_markup to first chunk
                chunk_reply_markup = reply_markup if i == 0 else None
                try:
                    await self._send_text(
                        bot, chat_id, chunk, reply_params, thread_kwargs,
                        reply_markup=chunk_reply_markup
                    )
                except Exception as e:
                    await self._handle_send_error(str(chat_id), e)
                    raise

    async def _send_text(
        self,
        bot,
        chat_id: int,
        text: str,
        reply_params=None,
        thread_kwargs: dict | None = None,
        reply_markup=None,
    ) -> None:
        """Send a plain text message with HTML fallback."""

        async def send_with_retry(send_fn, **kwargs):
            """Simple retry loop for sending messages."""
            for attempt in range(1, _SEND_MAX_RETRIES + 1):
                try:
                    return await send_fn(**kwargs)
                except TimedOut:
                    if attempt == _SEND_MAX_RETRIES:
                        raise
                    delay = _SEND_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning("Telegram timeout (attempt {}/{}), retrying in {:.1f}s", attempt, _SEND_MAX_RETRIES, delay)
                    await asyncio.sleep(delay)

        try:
            html = _markdown_to_telegram_html(text)
            await send_with_retry(
                bot.send_message,
                chat_id=chat_id, text=html, parse_mode="HTML",
                reply_parameters=reply_params,
                reply_markup=reply_markup,
                disable_web_page_preview=not self.config.link_preview,
                **(thread_kwargs or {}),
            )
        except Exception as e:
            logger.warning("HTML parse failed, falling back to plain text: {}", e)
            try:
                await send_with_retry(
                    bot.send_message,
                    chat_id=chat_id,
                    text=text,
                    reply_parameters=reply_params,
                    reply_markup=reply_markup,
                    **(thread_kwargs or {}),
                )
            except Exception as e2:
                logger.error("Error sending Telegram message: {}", e2)
                raise

    @staticmethod
    def _is_not_modified_error(exc: Exception) -> bool:
        return isinstance(exc, BadRequest) and "message is not modified" in str(exc).lower()

    async def _call_with_retry(self, func, *args, **kwargs):
        """Call a function with exponential backoff retry on Telegram errors."""
        for attempt in range(1, _SEND_MAX_RETRIES + 1):
            try:
                return await func(*args, **kwargs)
            except TimedOut:
                if attempt == _SEND_MAX_RETRIES:
                    raise
                delay = _SEND_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning("Telegram timeout (attempt {}/{}), retrying in {:.1f}s",
                    attempt, _SEND_MAX_RETRIES, delay)
                await asyncio.sleep(delay)
            except Exception:
                raise

    async def send_delta(self, chat_id: str, delta: str, metadata: dict[str, Any] | None = None) -> None:
        """Progressive message editing: send on first delta, edit on subsequent ones."""
        if not self._app:
            return
        meta = metadata or {}
        int_chat_id = int(chat_id)
        stream_id = meta.get("_stream_id")

        if meta.get("_stream_end"):
            buf = self._stream_bufs.get(chat_id)
            if not buf or not buf.message_id or not buf.text:
                return
            if stream_id is not None and buf.stream_id is not None and buf.stream_id != stream_id:
                return
            self._stop_typing(chat_id)
            try:
                html = _markdown_to_telegram_html(buf.text)
                await self._call_with_retry(
                    self._app.bot.edit_message_text,
                    chat_id=int_chat_id, message_id=buf.message_id,
                    text=html, parse_mode="HTML",
                )
            except Exception as e:
                if self._is_not_modified_error(e):
                    logger.debug("Final stream edit already applied for {}", chat_id)
                    self._stream_bufs.pop(chat_id, None)
                    return
                logger.debug("Final stream edit failed (HTML), trying plain: {}", e)
                try:
                    await self._call_with_retry(
                        self._app.bot.edit_message_text,
                        chat_id=int_chat_id, message_id=buf.message_id,
                        text=buf.text,
                    )
                except Exception as e2:
                    if self._is_not_modified_error(e2):
                        logger.debug("Final stream plain edit already applied for {}", chat_id)
                        self._stream_bufs.pop(chat_id, None)
                        return
                    logger.warning("Final stream edit failed: {}", e2)
                    raise  # Let ChannelManager handle retry
            self._stream_bufs.pop(chat_id, None)
            return

        buf = self._stream_bufs.get(chat_id)
        if buf is None or (stream_id is not None and buf.stream_id is not None and buf.stream_id != stream_id):
            buf = _StreamBuf(stream_id=stream_id)
            self._stream_bufs[chat_id] = buf
        elif buf.stream_id is None:
            buf.stream_id = stream_id
        buf.text += delta

        if not buf.text.strip():
            return

        now = time.monotonic()
        if buf.message_id is None:
            try:
                sent = await self._call_with_retry(
                    self._app.bot.send_message,
                    chat_id=int_chat_id, text=buf.text,
                )
                buf.message_id = sent.message_id
                buf.last_edit = now
            except Exception as e:
                logger.warning("Stream initial send failed: {}", e)
                raise  # Let ChannelManager handle retry
        elif (now - buf.last_edit) >= self._STREAM_EDIT_INTERVAL:
            try:
                await self._call_with_retry(
                    self._app.bot.edit_message_text,
                    chat_id=int_chat_id, message_id=buf.message_id,
                    text=buf.text,
                )
                buf.last_edit = now
            except Exception as e:
                if self._is_not_modified_error(e):
                    buf.last_edit = now
                    return
                logger.warning("Stream edit failed: {}", e)
                raise  # Let ChannelManager handle retry

    async def _on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not update.message or not update.effective_user:
            return

        user = update.effective_user
        await update.message.reply_text(
            f"👋 Hi {user.first_name}! I'm nanobot.\n\n"
            "Send me a message and I'll respond!\n"
            "Type /help to see available commands."
        )

    async def _on_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command, bypassing ACL so all users can access it."""
        if not update.message:
            return

        # Build help text based on enabled features
        help_text = (
            "🐈 nanobot commands:\n"
            "/new — Start a new conversation\n"
            "/stop — Stop the current task\n"
            "/restart — Restart the bot\n"
            "/status — Show bot status\n"
            "/skills — List available skills\n"
            "$<name> — Activate a skill inline (e.g. $weather what's the forecast)\n"
            "/help — Show available commands"
        )

        # Add config commands if enabled
        if self.config.config_writes:
            help_text += "\n/config — View or modify config"

        # Add exec approval commands if enabled
        if self.config.exec_approvals.enabled and self.config.exec_approvals.mode == "supervised":
            help_text += "\n/approve <id> — Approve exec request\n/deny <id> — Deny exec request"

        await update.message.reply_text(help_text)

    @staticmethod
    def _sender_id(user) -> str:
        """Build sender_id with username for allowlist matching."""
        sid = str(user.id)
        return f"{sid}|{user.username}" if user.username else sid

    @staticmethod
    def _derive_topic_session_key(message) -> str | None:
        """Derive topic-scoped session key for non-private Telegram chats."""
        message_thread_id = getattr(message, "message_thread_id", None)
        if message.chat.type == "private" or message_thread_id is None:
            return None
        return f"telegram:{message.chat_id}:topic:{message_thread_id}"

    @staticmethod
    def _build_message_metadata(message, user) -> dict:
        """Build common Telegram inbound metadata payload."""
        reply_to = getattr(message, "reply_to_message", None)
        return {
            "message_id": message.message_id,
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "is_group": message.chat.type != "private",
            "message_thread_id": getattr(message, "message_thread_id", None),
            "is_forum": bool(getattr(message.chat, "is_forum", False)),
            "reply_to_message_id": getattr(reply_to, "message_id", None) if reply_to else None,
        }

    @staticmethod
    def _extract_reply_context(message) -> str | None:
        """Extract text from the message being replied to, if any."""
        reply = getattr(message, "reply_to_message", None)
        if not reply:
            return None
        text = getattr(reply, "text", None) or getattr(reply, "caption", None) or ""
        if len(text) > TELEGRAM_REPLY_CONTEXT_MAX_LEN:
            text = text[:TELEGRAM_REPLY_CONTEXT_MAX_LEN] + "..."
        return f"[Reply to: {text}]" if text else None

    async def _download_message_media(
        self, msg, *, add_failure_content: bool = False
    ) -> tuple[list[str], list[str]]:
        """Download media from a message (current or reply). Returns (media_paths, content_parts)."""
        media_file = None
        media_type = None
        if getattr(msg, "photo", None):
            media_file = msg.photo[-1]
            media_type = "image"
        elif getattr(msg, "voice", None):
            media_file = msg.voice
            media_type = "voice"
        elif getattr(msg, "audio", None):
            media_file = msg.audio
            media_type = "audio"
        elif getattr(msg, "document", None):
            media_file = msg.document
            media_type = "file"
        elif getattr(msg, "video", None):
            media_file = msg.video
            media_type = "video"
        elif getattr(msg, "video_note", None):
            media_file = msg.video_note
            media_type = "video"
        elif getattr(msg, "animation", None):
            media_file = msg.animation
            media_type = "animation"
        if not media_file or not self._app:
            return [], []
        try:
            file = await self._app.bot.get_file(media_file.file_id)
            ext = self._get_extension(
                media_type,
                getattr(media_file, "mime_type", None),
                getattr(media_file, "file_name", None),
            )
            media_dir = get_media_dir("telegram")
            unique_id = getattr(media_file, "file_unique_id", media_file.file_id)
            file_path = media_dir / f"{unique_id}{ext}"
            await file.download_to_drive(str(file_path))
            path_str = str(file_path)
            if media_type in ("voice", "audio"):
                transcription = await self.transcribe_audio(file_path)
                if transcription:
                    logger.info("Transcribed {}: {}...", media_type, transcription[:50])
                    return [path_str], [f"[transcription: {transcription}]"]
                return [path_str], [f"[{media_type}: {path_str}]"]
            return [path_str], [f"[{media_type}: {path_str}]"]
        except Exception as e:
            logger.warning("Failed to download message media: {}", e)
            if add_failure_content:
                return [], [f"[{media_type}: download failed]"]
            return [], []

    async def _ensure_bot_identity(self) -> tuple[int | None, str | None]:
        """Load bot identity once and reuse it for mention/reply checks."""
        if self._bot_user_id is not None or self._bot_username is not None:
            return self._bot_user_id, self._bot_username
        if not self._app:
            return None, None
        bot_info = await self._app.bot.get_me()
        self._bot_user_id = getattr(bot_info, "id", None)
        self._bot_username = getattr(bot_info, "username", None)
        return self._bot_user_id, self._bot_username

    @staticmethod
    def _has_mention_entity(
        text: str,
        entities,
        bot_username: str,
        bot_id: int | None,
    ) -> bool:
        """Check Telegram mention entities against the bot username."""
        handle = f"@{bot_username}".lower()
        for entity in entities or []:
            entity_type = getattr(entity, "type", None)
            if entity_type == "text_mention":
                user = getattr(entity, "user", None)
                if user is not None and bot_id is not None and getattr(user, "id", None) == bot_id:
                    return True
                continue
            if entity_type != "mention":
                continue
            offset = getattr(entity, "offset", None)
            length = getattr(entity, "length", None)
            if offset is None or length is None:
                continue
            if text[offset : offset + length].lower() == handle:
                return True
        return handle in text.lower()

    async def _is_group_message_for_bot(self, message) -> bool:
        """Allow group messages when policy is open, @mentioned, or replying to the bot."""
        if message.chat.type == "private" or self.config.group_policy == "open":
            return True

        bot_id, bot_username = await self._ensure_bot_identity()
        if bot_username:
            text = message.text or ""
            caption = message.caption or ""
            if self._has_mention_entity(
                text,
                getattr(message, "entities", None),
                bot_username,
                bot_id,
            ):
                return True
            if self._has_mention_entity(
                caption,
                getattr(message, "caption_entities", None),
                bot_username,
                bot_id,
            ):
                return True

        reply_user = getattr(getattr(message, "reply_to_message", None), "from_user", None)
        return bool(bot_id and reply_user and reply_user.id == bot_id)

    def _remember_thread_context(self, message) -> None:
        """Cache topic thread id by chat/message id for follow-up replies."""
        message_thread_id = getattr(message, "message_thread_id", None)
        if message_thread_id is None:
            return
        key = (str(message.chat_id), message.message_id)
        self._message_threads[key] = message_thread_id
        if len(self._message_threads) > 1000:
            self._message_threads.pop(next(iter(self._message_threads)))

    async def _forward_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Forward slash commands to the bus for unified handling in AgentLoop."""
        if not update.message or not update.effective_user:
            return
        message = update.message
        user = update.effective_user
        self._remember_thread_context(message)

        # Check if this command is directed at a subagent (e.g., /start@coding_expert)
        command_text = message.text or ""
        subagent_id = self._extract_subagent_mention(command_text)

        if subagent_id:
            # Route to subagent
            if await self._route_to_subagent(
                subagent_id,
                command_text.replace(f"@{self._get_subagent_username(subagent_id)}", "").strip(),
                str(message.chat_id),
                self._sender_id(user),
                self._build_message_metadata(message, user),
            ):
                return

        # Default: forward to chief agent
        await self._handle_message(
            sender_id=self._sender_id(user),
            chat_id=str(message.chat_id),
            content=message.text or "",
            metadata=self._build_message_metadata(message, user),
            session_key=self._derive_topic_session_key(message),
        )

    def _get_subagent_username(self, subagent_id: str) -> str | None:
        """Get the username for a subagent from config."""
        config = self._subagent_configs.get(subagent_id, {})
        # Use bot_username from config, fallback to derived from subagent_id
        bot_username = config.get("bot_username", "")
        if bot_username:
            return bot_username.replace("@", "")
        return subagent_id.replace("_", "")

    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages (text, photos, voice, documents)."""
        if not update.message or not update.effective_user:
            return

        message = update.message
        user = update.effective_user
        chat_id = message.chat_id
        sender_id = self._sender_id(user)
        self._remember_thread_context(message)

        # Store chat_id for replies
        self._chat_ids[sender_id] = chat_id

        if not await self._is_group_message_for_bot(message):
            return

        # Build content from text and/or media
        content_parts = []
        media_paths = []

        # Text content
        if message.text:
            content_parts.append(message.text)
        if message.caption:
            content_parts.append(message.caption)

        # Download current message media
        current_media_paths, current_media_parts = await self._download_message_media(
            message, add_failure_content=True
        )
        media_paths.extend(current_media_paths)
        content_parts.extend(current_media_parts)
        if current_media_paths:
            logger.debug("Downloaded message media to {}", current_media_paths[0])

        # Reply context: text and/or media from the replied-to message
        reply = getattr(message, "reply_to_message", None)
        if reply is not None:
            reply_ctx = self._extract_reply_context(message)
            reply_media, reply_media_parts = await self._download_message_media(reply)
            if reply_media:
                media_paths = reply_media + media_paths
                logger.debug("Attached replied-to media: {}", reply_media[0])
            tag = reply_ctx or (f"[Reply to: {reply_media_parts[0]}]" if reply_media_parts else None)
            if tag:
                content_parts.insert(0, tag)
        content = "\n".join(content_parts) if content_parts else "[empty message]"

        logger.debug("Telegram message from {}: {}...", sender_id, content[:50])

        str_chat_id = str(chat_id)
        metadata = self._build_message_metadata(message, user)
        session_key = self._derive_topic_session_key(message)

        # Telegram media groups: buffer briefly, forward as one aggregated turn.
        if media_group_id := getattr(message, "media_group_id", None):
            key = f"{str_chat_id}:{media_group_id}"
            if key not in self._media_group_buffers:
                self._media_group_buffers[key] = {
                    "sender_id": sender_id, "chat_id": str_chat_id,
                    "contents": [], "media": [],
                    "metadata": metadata,
                    "session_key": session_key,
                }
                self._start_typing(str_chat_id)
                await self._add_reaction(str_chat_id, message.message_id, self.config.react_emoji)
            buf = self._media_group_buffers[key]
            if content and content != "[empty message]":
                buf["contents"].append(content)
            buf["media"].extend(media_paths)
            if key not in self._media_group_tasks:
                self._media_group_tasks[key] = asyncio.create_task(self._flush_media_group(key))
            return

        # Start typing indicator before processing
        self._start_typing(str_chat_id)
        await self._add_reaction(str_chat_id, message.message_id, self.config.react_emoji)

        # Check for subagent mentions (@subagent_name)
        subagent_id = self._extract_subagent_mention(content)
        if subagent_id:
            # Check if this is a direct subagent request
            # (the subagent is mentioned AND the sender is allowed)
            subagent_config = self._subagent_configs.get(subagent_id, {})
            allowed_from = subagent_config.get("allow_from", [])
            sender_id_clean = sender_id.split("|")[0] if "|" in sender_id else sender_id

            # Check if sender is allowed for this subagent
            can_access = not allowed_from or sender_id_clean in allowed_from

            if can_access and subagent_config.get("respond_to_mentions", True):
                # Route to subagent
                if await self._route_to_subagent(subagent_id, content, str_chat_id, sender_id, metadata):
                    return

        # Forward to the message bus (default chief agent)
        await self._handle_message(
            sender_id=sender_id,
            chat_id=str_chat_id,
            content=content,
            media=media_paths,
            metadata=metadata,
            session_key=session_key,
        )

    async def _flush_media_group(self, key: str) -> None:
        """Wait briefly, then forward buffered media-group as one turn."""
        try:
            await asyncio.sleep(0.6)
            if not (buf := self._media_group_buffers.pop(key, None)):
                return
            content = "\n".join(buf["contents"]) or "[empty message]"
            await self._handle_message(
                sender_id=buf["sender_id"], chat_id=buf["chat_id"],
                content=content, media=list(dict.fromkeys(buf["media"])),
                metadata=buf["metadata"],
                session_key=buf.get("session_key"),
            )
        finally:
            self._media_group_tasks.pop(key, None)

    def _start_typing(self, chat_id: str) -> None:
        """Start sending 'typing...' indicator for a chat."""
        # Cancel any existing typing task for this chat
        self._stop_typing(chat_id)
        self._typing_tasks[chat_id] = asyncio.create_task(self._typing_loop(chat_id))

    def _stop_typing(self, chat_id: str) -> None:
        """Stop the typing indicator for a chat."""
        task = self._typing_tasks.pop(chat_id, None)
        if task and not task.done():
            task.cancel()

    async def _add_reaction(self, chat_id: str, message_id: int, emoji: str) -> None:
        """Add emoji reaction to a message (best-effort, non-blocking)."""
        if not self._app or not emoji:
            return
        try:
            await self._app.bot.set_message_reaction(
                chat_id=int(chat_id),
                message_id=message_id,
                reaction=[ReactionTypeEmoji(emoji=emoji)],
            )
        except Exception as e:
            logger.debug("Telegram reaction failed: {}", e)

    async def _typing_loop(self, chat_id: str) -> None:
        """Repeatedly send 'typing' action until cancelled."""
        try:
            while self._app:
                await self._app.bot.send_chat_action(chat_id=int(chat_id), action="typing")
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("Typing indicator stopped for {}: {}", chat_id, e)

    async def _on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log polling / handler errors instead of silently swallowing them."""
        from telegram.error import NetworkError, TimedOut

        if isinstance(context.error, (NetworkError, TimedOut)):
            logger.warning("Telegram network issue: {}", str(context.error))
        else:
            logger.error("Telegram error: {}", context.error)

    # ==================== Inline Buttons ====================

    async def _on_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline button callback queries."""
        query = update.callback_query
        if not query or not query.from_user or not query.message:
            return

        # Answer the callback query immediately (required by Telegram)
        try:
            await query.answer()
        except Exception as e:
            logger.debug("Callback query answer failed: {}", e)

        # Check if inline buttons are allowed for this chat
        chat_type = query.message.chat.type
        if not self._inline_buttons_allowed(chat_type):
            await query.edit_message_text("❌ Inline buttons not allowed in this chat.")
            return

        # Forward callback data as text to agent
        sender_id = self._sender_id(query.from_user)
        await self._handle_message(
            sender_id=sender_id,
            chat_id=str(query.message.chat_id),
            content=f"[callback: {query.data}]",
            metadata={
                "callback_data": query.data,
                "message_id": query.message.message_id,
                "chat_type": chat_type,
            },
        )

    def _inline_buttons_allowed(self, chat_type: str) -> bool:
        """Check if inline buttons are allowed for the given chat type."""
        mode = self.config.capabilities.inline_buttons
        if mode == "off":
            return False
        if mode == "all":
            return True
        if mode == "dm" and chat_type == "private":
            return True
        if mode == "group" and chat_type in ("group", "supergroup"):
            return True
        # "allowlist" - for now allow all (could be extended with explicit chat IDs)
        return mode == "allowlist"

    # ==================== Reaction Notifications ====================

    async def _on_message_reaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle message reaction updates."""
        reaction = update.message_reaction
        if not reaction:
            return

        chat = reaction.chat
        if not chat:
            return

        # Check reaction_notifications setting
        if self.config.reaction_notifications == "off":
            return

        # Get the user who reacted
        user = reaction.user
        if not user:
            return

        # For "own" mode, only notify on reactions to bot's messages
        if self.config.reaction_notifications == "own":
            # We need to track which messages were sent by the bot
            # For now, skip this check (could be implemented with sent message cache)
            pass

        # Get reaction emoji
        emoji = ""
        if reaction.new_reaction:
            for reaction_type in reaction.new_reaction:
                if isinstance(reaction_type, ReactionTypeEmoji):
                    emoji = reaction_type.emoji
                    break

        if not emoji:
            return

        # Build notification content based on reaction_level
        if self.config.reaction_level == "off":
            return
        elif self.config.reaction_level == "ack":
            # Minimal acknowledgment, no message to agent
            return
        elif self.config.reaction_level == "minimal":
            content = f"👍 {emoji}"
        elif self.config.reaction_level == "extensive":
            username = user.username or user.first_name or "Unknown"
            content = f"Telegram reaction added: {emoji} by @{username} on msg {reaction.message_id}"
        else:
            content = f"Reaction: {emoji}"

        # Send notification to agent
        sender_id = self._sender_id(user)
        await self._handle_message(
            sender_id=sender_id,
            chat_id=str(chat.id),
            content=f"[reaction: {content}]",
            metadata={
                "message_id": reaction.message_id,
                "reaction_emoji": emoji,
                "is_reaction": True,
            },
        )

    # ==================== Exec Approvals ====================

    async def _on_approve(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /approve command."""
        if not update.message or not update.effective_user:
            return

        user = update.effective_user
        sender_id = str(user.id)

        # Check if user is an approver
        if not self._is_approver(sender_id):
            await update.message.reply_text("❌ You are not authorized to approve requests.")
            return

        # Parse request ID from command args or reply
        request_id = self._parse_approval_args(context.args, update.message.reply_to_message)

        if not request_id:
            await update.message.reply_text(
                "Usage: /approve <request_id> or reply to an approval message with /approve"
            )
            return

        # Process the approval
        await self._process_approval(request_id, approved=True, approver_id=sender_id)

        await update.message.reply_text(f"✅ Request {request_id} approved.")

        # Send notification to channel if target is "both" or "channel"
        if self.config.exec_approvals.target in ("both", "channel"):
            try:
                await self._app.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=f"✅ Request {request_id} approved by @{user.username or user.first_name}.",
                )
            except Exception as e:
                logger.warning("Failed to send approval notification to channel: {}", e)

    async def _on_deny(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /deny command."""
        if not update.message or not update.effective_user:
            return

        user = update.effective_user
        sender_id = str(user.id)

        # Check if user is an approver
        if not self._is_approver(sender_id):
            await update.message.reply_text("❌ You are not authorized to deny requests.")
            return

        # Parse request ID from command args or reply
        request_id = self._parse_approval_args(context.args, update.message.reply_to_message)

        if not request_id:
            await update.message.reply_text(
                "Usage: /deny <request_id> or reply to an approval message with /deny"
            )
            return

        # Process the denial
        await self._process_approval(request_id, approved=False, approver_id=sender_id)

        await update.message.reply_text(f"❌ Request {request_id} denied.")

        # Send notification to channel if target is "both" or "channel"
        if self.config.exec_approvals.target in ("both", "channel"):
            try:
                await self._app.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=f"❌ Request {request_id} denied by @{user.username or user.first_name}.",
                )
            except Exception as e:
                logger.warning("Failed to send denial notification to channel: {}", e)

    def _is_approver(self, sender_id: str) -> bool:
        """Check if sender is an authorized approver."""
        # Clean sender_id (remove username part if present)
        sender_id_clean = sender_id.split("|")[0] if "|" in sender_id else sender_id

        # Check against configured approvers
        for approver in self.config.exec_approvals.approvers:
            if approver == sender_id_clean:
                return True

        # Also allow if sender is in allow_from (for single-owner bots)
        for allowed in self.config.allow_from:
            if allowed == sender_id_clean or allowed == "*":
                return True

        return False

    def _parse_approval_args(self, args: list[str], reply_to_message: Message | None) -> str | None:
        """Parse request ID from command arguments or reply."""
        # Try args first
        if args and args[0]:
            return args[0]

        # Try reply to message
        if reply_to_message and reply_to_message.text:
            # Extract request ID from approval message (format: "Request: XXX" or similar)
            import re
            match = re.search(r'(?:Request[:\s]+)?([a-zA-Z0-9_-]+)', reply_to_message.text)
            if match:
                return match.group(1)

        return None

    async def _process_approval(self, request_id: str, approved: bool, approver_id: str) -> None:
        """Process an approval or denial."""
        # Remove from pending approvals
        if request_id in self._pending_approvals:
            approval = self._pending_approvals.pop(request_id)

            # Send approval result to the agent system via message bus
            # This would integrate with the exec approval system
            content = f"[exec_approval] {request_id} {'approved' if approved else 'denied'} by {approver_id}"
            await self._handle_message(
                sender_id=approver_id,
                chat_id=approval.get("chat_id", ""),
                content=content,
                metadata={
                    "_exec_approval": True,
                    "request_id": request_id,
                    "approved": approved,
                    "approver_id": approver_id,
                },
            )

    async def _cleanup_expired_approvals(self) -> None:
        """Periodically clean up expired approval requests."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute
                now = time.time()
                expired = [
                    req_id for req_id, data in self._pending_approvals.items()
                    if now - data.get("created_at", 0) > 1800  # 30 minutes
                ]
                for req_id in expired:
                    self._pending_approvals.pop(req_id, None)
                    logger.info("Expired approval request: {}", req_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Approval cleanup error: {}", e)

    def add_pending_approval(self, request_id: str, chat_id: str, content: str) -> None:
        """Add a pending approval request."""
        self._pending_approvals[request_id] = {
            "chat_id": chat_id,
            "content": content,
            "created_at": time.time(),
        }

    # ==================== Config Writes ====================

    async def _on_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /config command for viewing and modifying config."""
        if not update.message:
            return

        # Check if sender is authorized (approver or owner)
        user = update.effective_user
        sender_id = str(user.id)

        # Allow if user is in allow_from or is an approver
        is_authorized = self._is_approver(sender_id) or sender_id in self.config.allow_from
        if not is_authorized and "*" not in self.config.allow_from:
            await update.message.reply_text("❌ You are not authorized to use config commands.")
            return

        args = context.args
        if not args:
            # Show current config
            await self._show_config(update.message)
            return

        subcommand = args[0].lower() if args else ""

        if subcommand == "set":
            await self._config_set(update.message, args[1:])
        elif subcommand == "unset":
            await self._config_unset(update.message, args[1:])
        elif subcommand == "show":
            await self._show_config(update.message)
        elif subcommand == "list":
            await self._show_config(update.message)
        else:
            await update.message.reply_text(
                "Usage:\n"
                "/config show - Show current config\n"
                "/config set <key> <value> - Set a config value\n"
                "/config unset <key> - Remove a config value"
            )

    async def _show_config(self, message) -> None:
        """Show current Telegram config."""
        lines = ["📋 Telegram Config:", ""]

        # Show key settings
        lines.append(f"• dm_policy: {self.config.dm_policy}")
        lines.append(f"• group_policy: {self.config.group_policy}")
        lines.append(f"• stream_mode: {self.config.stream_mode}")
        lines.append(f"• reaction_notifications: {self.config.reaction_notifications}")
        lines.append(f"• reaction_level: {self.config.reaction_level}")
        lines.append(f"• link_preview: {self.config.link_preview}")
        lines.append(f"• text_chunk_limit: {self.config.text_chunk_limit}")
        lines.append(f"• chunk_mode: {self.config.chunk_mode}")

        if self.config.groups:
            lines.append("")
            lines.append(f"• groups configured: {len(self.config.groups)}")

        await message.reply_text("\n".join(lines))

    async def _config_set(self, message, args: list[str]) -> None:
        """Set a config value."""
        if len(args) < 2:
            await message.reply_text("Usage: /config set <key> <value>")
            return

        key = args[0]
        value = args[1]

        # Validate and set the value
        success, error = await self._set_config_value(key, value)

        if success:
            await message.reply_text(f"✅ Set {key} = {value}")
            # Persist to file
            await self._persist_config()
        else:
            await message.reply_text(f"❌ Error: {error}")

    async def _config_unset(self, message, args: list[str]) -> None:
        """Unset a config value."""
        if not args:
            await message.reply_text("Usage: /config unset <key>")
            return

        key = args[0]
        success, error = await self._unset_config_value(key)

        if success:
            await message.reply_text(f"✅ Removed {key}")
            await self._persist_config()
        else:
            await message.reply_text(f"❌ Error: {error}")

    async def _set_config_value(self, key: str, value: str) -> tuple[bool, str | None]:
        """Validate and set a config value."""
        # Map of allowed keys and their types
        allowed_keys = {
            "dm_policy": ["allowlist", "open", "disabled"],
            "group_policy": ["open", "mention", "allowlist", "disabled"],
            "stream_mode": ["off", "partial", "block", "progress"],
            "reaction_notifications": ["off", "own", "all"],
            "reaction_level": ["off", "ack", "minimal", "extensive"],
            "link_preview": ["true", "false"],
            "reply_to_mode": ["off", "first", "all"],
            "chunk_mode": ["length", "newline"],
            "error_policy": ["reply", "silent"],
        }

        if key not in allowed_keys:
            return False, f"Unknown key: {key}. Allowed: {', '.join(allowed_keys.keys())}"

        # Check if value is valid for this key
        valid_values = allowed_keys[key]
        if value not in valid_values:
            return False, f"Invalid value for {key}. Allowed: {', '.join(valid_values)}"

        # Set the value
        if hasattr(self.config, key):
            setattr(self.config, key, value)
            return True, None

        return False, f"Key {key} not found in config"

    async def _unset_config_value(self, key: str) -> tuple[bool, str | None]:
        """Unset a config value (reset to default)."""
        # Keys that can be unset (reset to default)
        reset_to_default = {
            "dm_policy": "allowlist",
            "group_policy": "mention",
            "stream_mode": "partial",
            "reaction_notifications": "own",
            "reaction_level": "minimal",
            "link_preview": True,
            "reply_to_mode": "off",
            "chunk_mode": "length",
            "error_policy": "reply",
        }

        if key not in reset_to_default:
            return False, f"Cannot unset {key}"

        if hasattr(self.config, key):
            default = reset_to_default[key]
            setattr(self.config, key, default)
            return True, None

        return False, f"Key {key} not found"

    async def _persist_config(self) -> None:
        """Persist config to .nanobot/telegram-config.json."""
        if not self.workspace:
            logger.debug("No workspace, skipping config persistence")
            return

        config_file = self.workspace.parent / "telegram-config.json"

        # Load existing overrides
        overrides = {}
        if config_file.exists():
            try:
                overrides = json.loads(config_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                overrides = {}

        # Update with current config values
        overrides["dm_policy"] = self.config.dm_policy
        overrides["group_policy"] = self.config.group_policy
        overrides["stream_mode"] = self.config.stream_mode
        overrides["reaction_notifications"] = self.config.reaction_notifications
        overrides["reaction_level"] = self.config.reaction_level
        overrides["link_preview"] = self.config.link_preview
        overrides["text_chunk_limit"] = self.config.text_chunk_limit
        overrides["chunk_mode"] = self.config.chunk_mode
        overrides["reply_to_mode"] = self.config.reply_to_mode
        overrides["error_policy"] = self.config.error_policy
        overrides["groups"] = {k: v.model_dump() for k, v in self.config.groups.items()}

        # Write to file
        try:
            config_file.write_text(json.dumps(overrides, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info("Config persisted to {}", config_file)
        except Exception as e:
            logger.warning("Failed to persist config: {}", e)

    async def _load_config_overrides(self) -> None:
        """Load config overrides from .nanobot/telegram-config.json."""
        if not self.workspace:
            return

        config_file = self.workspace.parent / "telegram-config.json"

        if not config_file.exists():
            return

        try:
            overrides = json.loads(config_file.read_text(encoding="utf-8"))

            # Apply overrides
            for key, value in overrides.items():
                if key == "groups":
                    # Load group configs
                    for group_id, group_data in value.items():
                        if group_id not in self.config.groups:
                            self.config.groups[group_id] = TelegramGroupConfig.model_validate(group_data)
                elif hasattr(self.config, key):
                    setattr(self.config, key, value)

            logger.info("Loaded config overrides from {}", config_file)
        except Exception as e:
            logger.warning("Failed to load config overrides: {}", e)

    def _handle_group_migration(self, old_chat_id: str, new_chat_id: str) -> None:
        """Handle group migration (supergroup upgrade)."""
        # If old chat_id is in groups, update to new chat_id
        if old_chat_id in self.config.groups:
            group_config = self.config.groups.pop(old_chat_id)
            self.config.groups[new_chat_id] = group_config
            logger.info("Migrated group config from {} to {}", old_chat_id, new_chat_id)

    # ==================== Custom Commands ====================

    async def _register_commands(self) -> None:
        """Register bot commands (native + custom)."""
        all_commands = []

        # Add native commands if enabled
        if self.config.commands.native:
            all_commands.extend(self.BOT_COMMANDS)

        # Add custom commands
        if self.config.custom_commands:
            native_command_names = {cmd.command for cmd in self.BOT_COMMANDS}
            for cmd in self.config.custom_commands:
                command = cmd.get("command", "").lower().strip()
                description = cmd.get("description", "")

                # Validate command name
                if not self._validate_command(command):
                    logger.warning("Invalid custom command: {}", command)
                    continue

                # Skip if conflicts with native commands
                if command in native_command_names:
                    logger.debug("Skipping custom command {} (conflicts with native)", command)
                    continue

                # Skip duplicates
                if any(c.command == command for c in all_commands):
                    logger.debug("Skipping duplicate custom command: {}", command)
                    continue

                all_commands.append(BotCommand(command, description))

        try:
            await self._app.bot.set_my_commands(all_commands)
            logger.debug("Telegram bot commands registered ({} total)", len(all_commands))
        except Exception as e:
            logger.warning("Failed to register bot commands: {}", e)

    @staticmethod
    def _validate_command(command: str) -> bool:
        """Validate command name (a-z, 0-9, _, length 1-32)."""
        return bool(re.match(r'^[a-z][a-z0-9_]{0,31}$', command))

    # ==================== Error Policy ====================

    async def _handle_send_error(self, chat_id: str, error: Exception) -> None:
        """Handle send errors based on error policy."""
        if not self._app:
            return

        if self.config.error_policy == "silent":
            return

        # Check cooldown
        last_error = self._last_error_time.get(chat_id, 0)
        cooldown_seconds = self.config.error_cooldown_seconds
        if time.time() - last_error < cooldown_seconds:
            return

        self._last_error_time[chat_id] = time.time()

        # Send friendly error message
        error_msg = f"⚠️ Error: {self._get_error_message(error)}"
        try:
            await self._app.bot.send_message(chat_id=int(chat_id), text=error_msg)
        except Exception as e:
            logger.warning("Failed to send error message: {}", e)

    @staticmethod
    def _get_error_message(error: Exception) -> str:
        """Get user-friendly error message."""
        error_str = str(error).lower()

        if "timeout" in error_str:
            return "Request timed out. Please try again."
        elif "network" in error_str:
            return "Network error. Please check your connection."
        elif "forbidden" in error_str:
            return "Access denied."
        elif "not found" in error_str:
            return "Resource not found."
        else:
            return "An error occurred. Please try again later."

    # ==================== Message Actions Gating ====================

    def can_send_message(self) -> bool:
        """Check if sending messages is allowed."""
        return self.config.actions.send_message

    def can_delete_message(self) -> bool:
        """Check if deleting messages is allowed."""
        return self.config.actions.delete_message

    def can_react(self) -> bool:
        """Check if reactions are allowed."""
        return self.config.actions.reactions

    def can_send_sticker(self) -> bool:
        """Check if sending stickers is allowed."""
        return self.config.actions.sticker

    def can_send_poll(self) -> bool:
        """Check if sending polls is allowed."""
        return self.config.actions.poll

    # ==================== Direct Telegram Actions ====================

    async def telegram_delete_message(self, chat_id: str, message_id: int) -> bool:
        """Delete a message via Telegram bot."""
        if not self.can_delete_message():
            logger.warning("Delete message action is disabled")
            return False
        if not self._app:
            logger.warning("Telegram bot not running")
            return False
        try:
            await self._app.bot.delete_message(chat_id=int(chat_id), message_id=message_id)
            logger.info("Deleted message {} in chat {}", message_id, chat_id)
            return True
        except Exception as e:
            logger.error("Failed to delete message: {}", e)
            return False

    async def telegram_send_sticker(self, chat_id: str, file_id: str) -> bool:
        """Send a sticker via Telegram bot."""
        if not self.can_send_sticker():
            logger.warning("Sticker action is disabled")
            return False
        if not self._app:
            logger.warning("Telegram bot not running")
            return False
        try:
            await self._app.bot.send_sticker(chat_id=int(chat_id), sticker=file_id)
            logger.info("Sent sticker to chat {}", chat_id)
            return True
        except Exception as e:
            logger.error("Failed to send sticker: {}", e)
            return False

    async def telegram_send_poll(
        self,
        chat_id: str,
        question: str,
        options: list[str],
        *,
        anonymous: bool = True,
        multiple_choice: bool = False,
        duration: int = 60,
    ) -> bool:
        """Send a poll via Telegram bot."""
        if not self.can_send_poll():
            logger.warning("Poll action is disabled")
            return False
        if not self._app:
            logger.warning("Telegram bot not running")
            return False
        try:
            await self._app.bot.send_poll(
                chat_id=int(chat_id),
                question=question,
                options=options,
                is_anonymous=anonymous,
                allows_multiple_answers=multiple_choice,
                open_period=duration,
            )
            logger.info("Sent poll to chat {}", chat_id)
            return True
        except Exception as e:
            logger.error("Failed to send poll: {}", e)
            return False

    # ==================== Per-group/topic Config ====================

    def get_effective_group_config(self, chat_id: str) -> dict[str, Any]:
        """Get effective group config with inheritance: global -> wildcard -> specific."""
        result = {}

        # Start with global config
        for key in ["group_policy", "require_mention", "allow_from", "skills", "system_prompt", "enabled"]:
            val = getattr(self.config, key, None)
            if val is not None:
                result[key] = val

        # Apply wildcard group config if exists
        if "*" in self.config.groups:
            wildcard = self.config.groups["*"]
            for key in ["group_policy", "require_mention", "allow_from", "skills", "system_prompt", "enabled"]:
                val = getattr(wildcard, key, None)
                if val is not None:
                    result[key] = val

        # Apply specific group config (overrides wildcard)
        if chat_id in self.config.groups:
            specific = self.config.groups[chat_id]
            for key in ["group_policy", "require_mention", "allow_from", "skills", "system_prompt", "enabled"]:
                val = getattr(specific, key, None)
                if val is not None:
                    result[key] = val

        return result

    def get_effective_topic_config(self, chat_id: str, thread_id: int) -> dict[str, Any]:
        """Get effective topic config with inheritance: global -> group -> topic."""
        # Start with group config
        result = self.get_effective_group_config(chat_id)

        # Apply topic config overrides
        if chat_id in self.config.groups:
            group = self.config.groups[chat_id]
            thread_id_str = str(thread_id)
            if thread_id_str in group.topics:
                topic = group.topics[thread_id_str]
                for key in ["group_policy", "require_mention", "allow_from", "skills", "system_prompt", "enabled", "agent_id"]:
                    val = getattr(topic, key, None)
                    if val is not None:
                        result[key] = val

        return result

    def get_effective_config_for_message(self, chat_id: str, thread_id: int | None = None) -> dict[str, Any]:
        """Get effective config for a message (topic or group level)."""
        if thread_id is not None and thread_id > 1:  # Topic 1 is "General", not a real topic
            return self.get_effective_topic_config(chat_id, thread_id)
        return self.get_effective_group_config(chat_id)

    def _is_group_enabled_for_message(self, chat_id: str, thread_id: int | None = None) -> bool:
        """Check if bot is enabled for this chat/topic."""
        config = self.get_effective_config_for_message(chat_id, thread_id)
        # If enabled is explicitly False, block
        if config.get("enabled") is False:
            return False
        return True

    def _get_group_policy_for_message(self, chat_id: str, thread_id: int | None = None) -> str:
        """Get effective group policy for this chat/topic."""
        config = self.get_effective_config_for_message(chat_id, thread_id)
        return config.get("group_policy", self.config.group_policy)

    def _get_allow_from_for_message(self, chat_id: str, thread_id: int | None = None) -> list[str]:
        """Get effective allow_from for this chat/topic."""
        config = self.get_effective_config_for_message(chat_id, thread_id)
        if "allow_from" in config:
            return config["allow_from"]
        # Fall back to global group_allow_from, then global allow_from
        return self.config.group_allow_from or self.config.allow_from

    def _get_skills_for_message(self, chat_id: str, thread_id: int | None = None) -> list[str] | None:
        """Get effective skills for this chat/topic."""
        config = self.get_effective_config_for_message(chat_id, thread_id)
        return config.get("skills")

    def _get_system_prompt_for_message(self, chat_id: str, thread_id: int | None = None) -> str | None:
        """Get effective system_prompt for this chat/topic."""
        config = self.get_effective_config_for_message(chat_id, thread_id)
        return config.get("system_prompt")

    def _get_agent_id_for_message(self, chat_id: str, thread_id: int) -> str | None:
        """Get agent_id for topic routing (only applies to topics, not groups)."""
        if thread_id is not None and thread_id > 1:
            config = self.get_effective_topic_config(chat_id, thread_id)
            return config.get("agent_id")
        return None

    def _get_require_mention_for_message(self, chat_id: str, thread_id: int | None = None) -> bool:
        """Check if mention is required for this chat/topic."""
        config = self.get_effective_config_for_message(chat_id, thread_id)
        if "require_mention" in config:
            return config["require_mention"]
        # Default: mention required unless group_policy is "open"
        return config.get("group_policy", self.config.group_policy) != "open"

    # ==================== ACP Topic Binding ====================

    def is_acp_thread_binding_enabled(self) -> bool:
        """Check if ACP thread bindings are enabled."""
        return self.config.thread_bindings

    def get_topic_acp_session_key(self, chat_id: str, thread_id: int) -> str | None:
        """Get the ACP session key bound to a topic."""
        if chat_id not in self.config.groups:
            return None

        group = self.config.groups[chat_id]
        thread_id_str = str(thread_id)

        if thread_id_str not in group.topics:
            return None

        topic = group.topics[thread_id_str]
        return topic.acp_session_key

    def bind_topic_to_acp_session(self, chat_id: str, thread_id: int, acp_session_key: str) -> bool:
        """Bind a topic to an ACP session."""
        if chat_id not in self.config.groups:
            # Create group config first
            self.config.groups[chat_id] = TelegramGroupConfig()

        group = self.config.groups[chat_id]
        thread_id_str = str(thread_id)

        if thread_id_str not in group.topics:
            group.topics[thread_id_str] = TelegramTopicConfig()

        group.topics[thread_id_str].acp_session_key = acp_session_key
        logger.info("Bound topic {}/{} to ACP session {}", chat_id, thread_id, acp_session_key)
        return True

    def unbind_topic_from_acp_session(self, chat_id: str, thread_id: int) -> bool:
        """Unbind a topic from its ACP session."""
        if chat_id not in self.config.groups:
            return False

        group = self.config.groups[chat_id]
        thread_id_str = str(thread_id)

        if thread_id_str not in group.topics:
            return False

        old_key = group.topics[thread_id_str].acp_session_key
        group.topics[thread_id_str].acp_session_key = None
        logger.info("Unbound topic {}/{} from ACP session {}", chat_id, thread_id, old_key)
        return True

    def get_active_acp_sessions(self) -> list[dict[str, str]]:
        """Get all active ACP session bindings."""
        sessions = []

        for chat_id, group in self.config.groups.items():
            for thread_id_str, topic in group.topics.items():
                if topic.acp_session_key:
                    sessions.append({
                        "chat_id": chat_id,
                        "thread_id": thread_id_str,
                        "session_key": topic.acp_session_key,
                    })

        return sessions

    def _route_to_acp_session(self, chat_id: str, thread_id: int, content: str) -> str | None:
        """Check if message should be routed to ACP session. Returns session key if routed."""
        if not self.is_acp_thread_binding_enabled():
            return None

        session_key = self.get_topic_acp_session_key(chat_id, thread_id)
        if session_key:
            logger.info("Routing message to ACP session: {}", session_key)
            return session_key

        return None

    def _split_message_on_newlines(self, text: str, max_length: int) -> list[str]:
        """Split message on paragraph boundaries (blank lines) before length limit."""
        if len(text) <= max_length:
            return [text]

        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_length:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # If single paragraph exceeds max_length, split by lines
                if len(para) > max_length:
                    lines = para.split("\n")
                    for line in lines:
                        if len(current_chunk) + len(line) + 1 <= max_length:
                            current_chunk = (current_chunk + "\n" + line) if current_chunk else line
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = line
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text]

    def _get_extension(
        self,
        media_type: str,
        mime_type: str | None,
        filename: str | None = None,
    ) -> str:
        """Get file extension based on media type or original filename."""
        if mime_type:
            ext_map = {
                "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
                "audio/ogg": ".ogg", "audio/mpeg": ".mp3", "audio/mp4": ".m4a",
            }
            if mime_type in ext_map:
                return ext_map[mime_type]

        type_map = {"image": ".jpg", "voice": ".ogg", "audio": ".mp3", "file": ""}
        if ext := type_map.get(media_type, ""):
            return ext

        if filename:
            from pathlib import Path

            return "".join(Path(filename).suffixes)

        return ""
