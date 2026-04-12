"""Langfuse integration for production observability."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from loguru import logger

_langfuse_client: Any = None
_langfuse_initialized: bool = False


def get_langfuse() -> Any | None:
    """Get the Langfuse client instance."""
    global _langfuse_client
    return _langfuse_client


def is_enabled() -> bool:
    """Check if Langfuse is enabled and initialized."""
    global _langfuse_initialized
    return _langfuse_initialized and _langfuse_client is not None


def init_langfuse(
    public_key: str,
    secret_key: str,
    host: str = "https://cloud.langfuse.com",
    release: str | None = None,
) -> bool:
    """Initialize Langfuse client.

    Args:
        public_key: Langfuse public key.
        secret_key: Langfuse secret key.
        host: Langfuse host URL.
        release: Release version for tracing.

    Returns:
        True if initialized successfully.
    """
    global _langfuse_client, _langfuse_initialized

    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            release=release,
        )
        _langfuse_initialized = True
        logger.info("Langfuse initialized: {}", host)
        return True
    except ImportError:
        logger.warning("langfuse not installed, skipping observability")
        return False
    except Exception as e:
        logger.warning("Failed to initialize Langfuse: {}", e)
        return False


def flush() -> None:
    """Flush pending Langfuse events."""
    if _langfuse_client:
        try:
            _langfuse_client.flush()
        except Exception:
            pass


class LangfuseTracer:
    """Context manager for tracing LLM calls."""

    def __init__(self, name: str, metadata: dict[str, Any] | None = None):
        self.name = name
        self.metadata = metadata or {}
        self.trace: Any = None
        self.generation: Any = None

    def __enter__(self) -> "LangfuseTracer":
        if not is_enabled():
            return self

        try:
            self.trace = get_langfuse().trace(
                name=self.name,
                metadata=self.metadata,
            )
        except Exception as e:
            logger.debug("Langfuse trace error: {}", e)

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if not is_enabled():
            return

        try:
            if self.generation:
                if exc_type:
                    self.generation.update(
                        status="error",
                        error={"name": exc_type.__name__, "message": str(exc_val)},
                    )
                self.generation.end()
        except Exception:
            pass

        try:
            if self.trace:
                self.trace.end()
        except Exception:
            pass

    def log_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        response: str,
        usage: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a completion to Langfuse.

        Args:
            model: Model name.
            messages: Input messages.
            response: Model response.
            usage: Token usage information.
            metadata: Additional metadata.
        """
        if not is_enabled() or not self.trace:
            return

        try:
            self.generation = self.trace.generation(
                model=model,
                messages=messages,
                completion=response,
                usage=usage,
                metadata=metadata,
            )
        except Exception as e:
            logger.debug("Langfuse generation error: {}", e)

    def log_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: str | None = None,
        error: str | None = None,
    ) -> None:
        """Log a tool call to Langfuse.

        Args:
            tool_name: Name of the tool.
            arguments: Tool arguments.
            result: Tool result.
            error: Error message if any.
        """
        if not is_enabled() or not self.trace:
            return

        try:
            self.trace.span(
                name=f"tool:{tool_name}",
                metadata={"arguments": arguments, "result": result, "error": error},
            )
        except Exception as e:
            logger.debug("Langfuse span error: {}", e)


@asynccontextmanager
async def async_langfuse_trace(name: str, metadata: dict[str, Any] | None = None):
    """Async context manager for Langfuse traces.

    Usage:
        async with async_langfuse_trace("my-task", {"user": "user123"}) as trace:
            trace.log_completion(...)
    """
    tracer = LangfuseTracer(name, metadata)
    tracer.__enter__()
    try:
        yield tracer
    finally:
        tracer.__exit__(None, None, None)


def create_trace(
    name: str,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> LangfuseTracer | None:
    """Create a new Langfuse trace.

    Args:
        name: Trace name.
        user_id: User identifier.
        session_id: Session identifier.
        metadata: Additional metadata.

    Returns:
        LangfuseTracer instance or None if disabled.
    """
    if not is_enabled():
        return None

    meta = metadata or {}
    if user_id:
        meta["user_id"] = user_id
    if session_id:
        meta["session_id"] = session_id

    return LangfuseTracer(name, meta)
