# Channels

The channels module implements a plugin architecture for multi-platform messaging. It provides a unified interface for receiving and sending messages across 12 different messaging platforms.

## Files

| File | Description |
|------|-------------|
| `channels/__init__.py` | Module initialization |
| `channels/base.py` | Abstract base class for all channels |
| `channels/manager.py` | Channel manager for coordinating all channels |
| `channels/registry.py` | Auto-discovery system for channels |
| `channels/telegram.py` | Telegram integration |
| `channels/discord.py` | Discord integration |
| `channels/slack.py` | Slack integration |
| `channels/whatsapp.py` | WhatsApp integration |
| `channels/email.py` | Email (IMAP/SMTP) integration |
| `channels/matrix.py` | Matrix protocol integration |
| `channels/feishu.py` | Feishu/Lark integration |
| `channels/dingtalk.py` | DingTalk integration |
| `channels/weixin.py` | WeChat integration |
| `channels/qq.py` | QQ integration |
| `channels/wecom.py` | WeCom (Enterprise WeChat) integration |
| `channels/mochat.py` | MoChat integration |

---

## Base Classes

### BaseChannel

**File:** `channels/base.py`

Abstract base class that all channel implementations inherit from.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | str | Channel identifier (e.g., "telegram", "discord") |
| `display_name` | str | Human-readable name |
| `transcription_api_key` | str | Groq API key for audio transcription |

#### Core Abstract Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `start` | - | None | Begin listening for messages (long-running async task) |
| `stop` | - | None | Clean up resources |
| `send` | msg: OutboundMessage | None | Send message through channel |

#### Optional Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `send_delta` | chat_id, delta, metadata | None | Streaming text chunks |
| `login` | force | None | Interactive login (QR code scan) |

#### Built-in Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `is_allowed` | sender_id | bool | Permission check against `allow_from` list |
| `_handle_message` | ... | None | Validates, creates InboundMessage, publishes to bus |
| `transcribe_audio` | file_path | str | Uses Groq Whisper for voice-to-text |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `supports_streaming` | bool | Property checking if streaming is enabled |

---

### ChannelManager

**File:** `channels/manager.py`

Coordinates all enabled channels.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `_init_channels` | - | None | Discovers channels via pkgutil + entry_points |
| `start_all` | - | None | Starts all channels + outbound dispatcher |
| `stop_all` | - | None | Graceful shutdown |
| `_dispatch_outbound` | - | None | Routes messages to channels with delta coalescing |
| `_send_with_retry` | channel, msg | None | Exponential backoff: 1s, 2s, 4s |
| `get_channel` | name | BaseChannel | Get channel instance |
| `get_status` | - | dict | Status of all channels |

#### Delta Coalescing
Merges consecutive streaming deltas for same (channel, chat_id) to reduce API calls.

---

### ChannelRegistry

**File:** `channels/registry.py`

Auto-discovery system for channels.

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `discover_channel_names` | - | list[str] | Scan package for built-in channels |
| `load_channel_class` | module | type | Import module, return BaseChannel subclass |
| `discover_plugins` | - | dict | Load external plugins via entry_points |
| `discover_all` | - | dict | Merge built-in + external (builtins take priority) |

---

## Platform Implementations

### TelegramChannel

**File:** `channels/telegram.py`

| Feature | Details |
|---------|---------|
| **Protocol** | Long polling via `python-telegram-bot` |
| **Markdown** | `_markdown_to_telegram_html()` converts MD → HTML with table rendering |
| **Streaming** | Progressive message editing with `_StreamBuf` per chat |
| **Group Policy** | `"open"` (respond to all) or `"mention"` (@-required) |
| **Media** | Photos, voice (auto-transcribed), audio, documents |
| **Features** | Typing indicators, emoji reactions, thread support, media group buffering |

#### Key Methods

| Method | Description |
|--------|-------------|
| `start` | Start long polling for updates |
| `stop` | Stop the polling loop |
| `send` | Send message with HTML formatting |
| `send_delta` | Stream message updates |
| `_markdown_to_telegram_html` | Convert markdown to Telegram HTML |

---

### DiscordChannel

**File:** `channels/discord.py`

| Feature | Details |
|---------|---------|
| **Protocol** | Gateway WebSocket + REST |
| **Message Limit** | 2000 chars (auto-split) |
| **Attachments** | Up to 20MB via multipart/form-data |
| **Group Policy** | `"mention"` or `"open"` |

#### Key Methods

| Method | Description |
|--------|-------------|
| `start` | Start Discord client with intents |
| `stop` | Close Discord client |
| `send` | Send message, split if > 2000 chars |

---

### SlackChannel

**File:** `channels/slack.py`

| Feature | Details |
|---------|---------|
| **Protocol** | Socket Mode (WebSocket) |
| **Message Format** | `slackify_markdown` + custom fixes |
| **DM Policy** | `"open"` or `"allowlist"` |
| **Group Policy** | `"mention"`, `"open"`, or `"allowlist"` |
| **Threading** | Auto-reply in threads |

---

### WhatsAppChannel

**File:** `channels/whatsapp.py`

| Feature | Details |
|---------|---------|
| **Protocol** | Node.js bridge via WebSocket (`ws://localhost:3001`) |
| **Login** | `login()` spawns npm process for QR code |
| **Media** | Bridge downloads images/files |

---

### EmailChannel

**File:** `channels/email.py`

| Feature | Details |
|---------|---------|
| **Inbound** | IMAP polling with `poll_interval_seconds` |
| **Outbound** | SMTP with TLS/SSL |
| **Anti-Spoofing** | DKIM + SPF verification via `Authentication-Results` header |
| **Threading** | Tracks `subject` + `Message-ID` for replies |

#### Key Methods

| Method | Description |
|--------|-------------|
| `_poll_imap` | Poll IMAP server for new emails |
| `_send_smtp` | Send email via SMTP |

---

### MatrixChannel

**File:** `channels/matrix.py`

| Feature | Details |
|---------|---------|
| **Protocol** | `nio` library with long-polling sync |
| **E2EE** | Optional end-to-end encryption |
| **Markdown** | `mistune` → sanitized HTML via `nh3` |
| **Media** | Upload to homeserver, respects server limits |
| **Threads** | m.thread support with `m.relates_to` |

---

### FeishuChannel

**File:** `channels/feishu.py`

| Feature | Details |
|---------|---------|
| **Protocol** | lark-oapi WebSocket long connection |
| **Message Formats** | `text`, `post` (rich text), `interactive` (cards) |
| **Streaming** | CardKit streaming API with typewriter effect |
| **Markdown Detection** | Auto-selects format based on content complexity |
| **Tables** | Special handling (API limits to 1 table/card) |

---

### DingTalkChannel

**File:** `channels/dingtalk.py`

| Feature | Details |
|---------|---------|
| **Protocol** | `dingtalk-stream` SDK Stream Mode |
| **Message Types** | text, markdown, image, file, richText |
| **Access Token** | Auto-refresh with 60s expiry buffer |

---

### WeixinChannel

**File:** `channels/weixin.py`

| Feature | Details |
|---------|---------|
| **Protocol** | ilinkai.weixin.qq.com HTTP long-poll |
| **Login** | QR code with `qrcode` library display |
| **Media** | AES-128-ECB encryption for CDN upload/download |
| **Session Management** | Auto-pause on `ERRCODE_SESSION_EXPIRED` (-14) |

---

### QQChannel

**File:** `channels/qq.py`

| Feature | Details |
|---------|---------|
| **Protocol** | botpy SDK with WebSocket |
| **Message Types** | C2C (direct) and Group |
| **Media** | Base64 upload via rich media API |
| **Download** | Chunked streaming to avoid memory issues |

---

### WecomChannel

**File:** `channels/wecom.py`

| Feature | Details |
|---------|---------|
| **Protocol** | wecom_aibot_sdk WebSocket |
| **Message Types** | text, image, voice, file, mixed |
| **Streaming** | `reply_stream()` with `finish=True` |

---

### MochatChannel

**File:** `channels/mochat.py`

| Feature | Details |
|---------|---------|
| **Protocol** | Socket.IO primary, HTTP polling fallback |
| **Targets** | Sessions (1:1) and Panels (group-like) |
| **Cursor Persistence** | Saves position to `session_cursors.json` |
| **Delay Mode** | `"non-mention"` - delays replies for non-mentions |
| **Fallback** | Auto-enables polling if WebSocket fails |

---

## Message Handling Patterns

### Inbound Flow

```
Platform Event → Parse Message → _handle_message() → 
  is_allowed() check → Create InboundMessage → bus.publish_inbound()
```

### Outbound Flow

```
Agent → bus.publish_outbound() → ChannelManager._dispatch_outbound() → 
  _coalesce_stream_deltas() → channel.send() / send_delta()
```

### Common Patterns

1. **Permission Check:** `is_allowed(sender_id)` against `allow_from` list
2. **Deduplication:** Most channels use OrderedDict to track processed message IDs
3. **Typing Indicators:** Async loop sending periodic typing status
4. **Media Handling:** Download to local storage, transcribe voice
5. **Error Handling:** Retry with exponential backoff
6. **Group Policies:** `"open"`, `"mention"`, `"allowlist"` for group chats

---

## Summary Table

| Channel | Platform | Protocol | Lines |
|---------|----------|----------|-------|
| TelegramChannel | Telegram | python-telegram-bot (long polling) | 951 |
| DiscordChannel | Discord | Gateway WebSocket + REST | 395 |
| SlackChannel | Slack | Socket Mode | 344 |
| WhatsAppChannel | WhatsApp | Node.js bridge (WebSocket) | 301 |
| EmailChannel | Email | IMAP + SMTP | 552 |
| MatrixChannel | Matrix | nio (sync) | 739 |
| FeishuChannel | Feishu/Lark | lark-oapi WebSocket | 1200+ |
| DingTalkChannel | DingTalk | dingtalk-stream SDK | 580 |
| WeixinChannel | WeChat | ilinkai API (HTTP) | 1033 |
| QQChannel | QQ | botpy SDK | 639 |
| WecomChannel | WeCom | wecom_aibot_sdk WebSocket | 371 |
| MochatChannel | MoChat | Socket.IO + polling | 947 |
