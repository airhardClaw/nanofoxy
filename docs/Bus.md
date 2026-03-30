# Bus

The bus module provides the message passing infrastructure for nanobot. It handles inter-component communication through an event-based pub/sub system.

## Files

| File | Description |
|------|-------------|
| `bus/__init__.py` | Module initialization |
| `bus/events.py` | Event definitions and event bus |
| `bus/queue.py` | Queue for managing outbound messages |

---

## Events

**File:** `bus/events.py`

### Event Types

| Event Type | Description |
|------------|-------------|
| `INBOUND` | Inbound message received from a channel |
| `OUTBOUND` | Outbound message to be sent |
| `START` | Bot started event |
| `STOP` | Bot stopped event |
| `ERROR` | Error event |

### Event Data Classes

#### InboundMessage

| Field | Type | Description |
|-------|------|-------------|
| `channel` | str | Channel name (e.g., "telegram") |
| `chat_id` | str | Chat/user ID |
| `message_id` | str | Original message ID |
| `sender_id` | str | Sender ID |
| `sender_name` | str | Sender display name |
| `text` | str | Message text |
| `media` | list | Attached media |
| `raw` | dict | Raw platform event |
| `timestamp` | datetime | Message timestamp |

#### OutboundMessage

| Field | Type | Description |
|-------|------|-------------|
| `channel` | str | Target channel |
| `chat_id` | str | Target chat/user ID |
| `content` | str | Message content |
| `reply_to` | str | Message ID to reply to |
| `media` | list | Media to attach |
| `metadata` | dict | Additional metadata |

---

### EventBus

**File:** `bus/events.py`

Pub/Sub event bus for inter-component communication.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `subscribe` | event_type, callback | None | Subscribe to an event type |
| `unsubscribe` | event_type, callback | None | Unsubscribe from an event type |
| `publish` | event_type, data | None | Publish an event with data |
| `publish_inbound` | inbound | None | Publish an inbound message |
| `publish_outbound` | outbound | None | Publish an outbound message |

#### Usage

```python
# Subscribe to inbound messages
def handle_inbound(msg):
    print(f"Received: {msg.text}")

event_bus.subscribe(EventType.INBOUND, handle_inbound)

# Publish an outbound message
event_bus.publish_outbound(OutboundMessage(channel="telegram", chat_id="123", content="Hello"))
```

---

## Queue

**File:** `bus/queue.py`

### MessageQueue

Queue for managing outbound messages with priority support.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `enqueue` | message, priority | None | Add message to queue |
| `dequeue` | - | tuple | Get next message (priority, message) |
| `peek` | - | tuple | Look at next message without removing |
| `size` | - | int | Number of messages in queue |
| `clear` | - | None | Clear all messages |

### Priority Levels

| Level | Value | Description |
|-------|-------|-------------|
| `HIGH` | 0 | High priority (e.g., errors) |
| `NORMAL` | 1 | Normal priority (e.g., responses) |
| `LOW` | 2 | Low priority (e.g., non-urgent) |

---

## Architecture

The bus system follows a pub/sub pattern:

```
Channels (Telegram, Discord, etc.)
    │
    ▼
bus.publish_inbound() ──▶ EventBus
    │                        │
    │                        ▼
    │                   Subscribers
    │                   (Agent, Commands, etc.)
    │                        │
    │                        ▼
    │                   Processing
    │                        │
    │                        ▼
bus.publish_outbound() ──▶ EventBus ──▶ ChannelManager ──▶ Channels
```

### Message Flow

1. **Inbound**: Channel receives message → converts to `InboundMessage` → `event_bus.publish_inbound()` → Agent processes
2. **Outbound**: Agent creates `OutboundMessage` → `event_bus.publish_outbound()` → `ChannelManager` dispatches to appropriate channel
