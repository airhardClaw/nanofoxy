"""Message tool for sending messages to users."""

from typing import Any, Awaitable, Callable

from nanobot.agent.tools.base import Tool
from nanobot.bus.events import OutboundMessage


class MessageTool(Tool):
    """Tool to send messages to users on chat channels."""

    def __init__(
        self,
        send_callback: Callable[[OutboundMessage], Awaitable[None]] | None = None,
        default_channel: str = "",
        default_chat_id: str = "",
        default_message_id: str | None = None,
        telegram_channel: Any = None,
    ):
        self._send_callback = send_callback
        self._default_channel = default_channel
        self._default_chat_id = default_chat_id
        self._default_message_id = default_message_id
        self._sent_in_turn: bool = False
        self._telegram_channel = telegram_channel

    def set_telegram_channel(self, channel) -> None:
        """Set the Telegram channel reference for direct actions."""
        self._telegram_channel = channel

    def set_context(self, channel: str, chat_id: str, message_id: str | None = None) -> None:
        """Set the current message context."""
        self._default_channel = channel
        self._default_chat_id = chat_id
        self._default_message_id = message_id

    def set_send_callback(self, callback: Callable[[OutboundMessage], Awaitable[None]]) -> None:
        """Set the callback for sending messages."""
        self._send_callback = callback

    def start_turn(self) -> None:
        """Reset per-turn send tracking."""
        self._sent_in_turn = False

    @property
    def name(self) -> str:
        return "message"

    @property
    def description(self) -> str:
        return (
            "Send a message to the user, optionally with file attachments. "
            "This is the ONLY way to deliver files (images, documents, audio, video) to the user. "
            "Use the 'media' parameter with file paths to attach files. "
            "Do NOT use read_file to send files — that only reads content for your own analysis."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The message content to send"
                },
                "channel": {
                    "type": "string",
                    "description": "Optional: target channel (telegram, discord, etc.)"
                },
                "chat_id": {
                    "type": "string",
                    "description": "Optional: target chat/user ID"
                },
                "media": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: list of file paths to attach (images, audio, documents)"
                }
            },
            "required": ["content"]
        }

    async def execute(
        self,
        content: str,
        channel: str | None = None,
        chat_id: str | None = None,
        message_id: str | None = None,
        media: list[str] | None = None,
        buttons: list[list[dict]] | None = None,
        **kwargs: Any
    ) -> str:
        channel = channel or self._default_channel
        chat_id = chat_id or self._default_chat_id
        message_id = message_id or self._default_message_id

        if not channel or not chat_id:
            return "Error: No target channel/chat specified"

        if not self._send_callback:
            return "Error: Message sending not configured"

        msg = OutboundMessage(
            channel=channel,
            chat_id=chat_id,
            content=content,
            media=media or [],
            buttons=buttons or [],
            metadata={
                "message_id": message_id,
            },
        )

        try:
            await self._send_callback(msg)
            if channel == self._default_channel and chat_id == self._default_chat_id:
                self._sent_in_turn = True
            media_info = f" with {len(media)} attachments" if media else ""
            buttons_info = f" with {sum(len(row) for row in buttons)} buttons" if buttons else ""
            return f"Message sent to {channel}:{chat_id}{media_info}{buttons_info}"
        except Exception as e:
            return f"Error sending message: {str(e)}"

    async def telegram_delete_message(self, chat_id: str, message_id: int) -> str:
        """Delete a message in a Telegram chat. Requires chat_id and message_id."""
        if self._default_channel != "telegram" and not self._telegram_channel:
            return "Error: Telegram channel not available"

        tg = self._telegram_channel
        if not tg:
            return "Error: Telegram channel not initialized"

        try:
            success = await tg.telegram_delete_message(chat_id, message_id)
            if success:
                return f"Message {message_id} deleted in chat {chat_id}"
            return f"Failed to delete message {message_id}"
        except Exception as e:
            return f"Error deleting message: {str(e)}"

    async def telegram_send_sticker(self, chat_id: str, file_id: str) -> str:
        """Send a sticker to a Telegram chat. Requires chat_id and file_id (Telegram file ID or URL)."""
        if self._default_channel != "telegram" and not self._telegram_channel:
            return "Error: Telegram channel not available"

        tg = self._telegram_channel
        if not tg:
            return "Error: Telegram channel not initialized"

        try:
            success = await tg.telegram_send_sticker(chat_id, file_id)
            if success:
                return f"Sticker sent to chat {chat_id}"
            return "Failed to send sticker"
        except Exception as e:
            return f"Error sending sticker: {str(e)}"

    async def telegram_send_poll(
        self,
        chat_id: str,
        question: str,
        options: list[str],
        *,
        anonymous: bool = True,
        multiple_choice: bool = False,
        duration: int = 60,
    ) -> str:
        """Send a poll to a Telegram chat. Requires chat_id, question, and options list."""
        if self._default_channel != "telegram" and not self._telegram_channel:
            return "Error: Telegram channel not available"

        tg = self._telegram_channel
        if not tg:
            return "Error: Telegram channel not initialized"

        if len(options) < 2:
            return "Error: Poll requires at least 2 options"
        if len(options) > 10:
            return "Error: Poll cannot have more than 10 options"

        try:
            success = await tg.telegram_send_poll(
                chat_id, question, options,
                anonymous=anonymous,
                multiple_choice=multiple_choice,
                duration=duration,
            )
            if success:
                return f"Poll sent to chat {chat_id}: {question}"
            return "Failed to send poll"
        except Exception as e:
            return f"Error sending poll: {str(e)}"
