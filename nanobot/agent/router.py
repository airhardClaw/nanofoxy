"""Model Router - Routes between orchestrator and worker models based on message content."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider

# Routing thresholds
USER_SHORT_THRESHOLD = 500  # characters
USER_LONG_THRESHOLD = 2000  # characters


class ModelRouter:
    """Routes between orchestrator and worker models based on message content.
    
    Orchestrator model: Used for planning, routing, decision-making, short user inputs
    Worker model: Used for tool execution, processing long content, tool results
    """
    
    def __init__(
        self,
        provider: LLMProvider,
        orchestrator_model: str,
        worker_model: str,
    ):
        self.provider = provider
        self.orchestrator_model = orchestrator_model
        self.worker_model = worker_model
        
        logger.info(
            "[ModelRouter] Initialized - orchestrator: {}, worker: {}",
            orchestrator_model,
            worker_model,
        )
    
    async def chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Chat using the appropriate model based on message content."""
        selected_model = self._select_model(messages)
        model_type = self._get_model_type(selected_model)
        
        # Log the routing decision
        last_msg = messages[-1] if messages else {}
        preview = last_msg.get("content", "")[:50].replace("\n", " ")
        if len(preview) >= 50:
            preview += "..."
        
        logger.info(
            "[ModelRouter] Using {} for: '{}'",
            model_type,
            preview,
        )
        
        # Override model in kwargs if present
        kwargs = {**kwargs, "model": selected_model}
        
        # Check if streaming is requested (on_content_delta in kwargs)
        on_content_delta = kwargs.pop("on_content_delta", None)
        
        # Use appropriate method based on whether streaming is requested
        if on_content_delta:
            if hasattr(self.provider, 'chat_stream_with_retry'):
                return await self.provider.chat_stream_with_retry(
                    messages, on_content_delta=on_content_delta, **kwargs
                )
            # Fallback to regular chat if streaming not available
            return await self.provider.chat(messages, **kwargs)
        else:
            if hasattr(self.provider, 'chat_with_retry'):
                return await self.provider.chat_with_retry(messages, **kwargs)
            return await self.provider.chat(messages, **kwargs)
    
    def _select_model(self, messages: list[dict[str, Any]]) -> str:
        """Automatically select model based on last message content.
        
        Logic:
        - Tool result → worker model (actual work)
        - Short user message (< 500 chars) → orchestrator model (planning)
        - Long content (> 2000 chars) → worker model (heavy processing)
        - Default → orchestrator model
        """
        if not messages:
            logger.debug("[ModelRouter] No messages, defaulting to orchestrator")
            return self.orchestrator_model
        
        last_msg = messages[-1]
        role = last_msg.get("role", "")
        content = last_msg.get("content", "")
        content_length = len(content)
        
        # Tool result = worker model (actual work being processed)
        if role == "tool":
            logger.debug(
                "[ModelRouter] Tool result detected ({} chars) → worker",
                content_length,
            )
            return self.worker_model
        
        # System message = orchestrator
        if role == "system":
            logger.debug("[ModelRouter] System message → orchestrator")
            return self.orchestrator_model
        
        # User message: decide based on length
        if role == "user":
            if content_length < USER_SHORT_THRESHOLD:
                # Short user input = planning/routing = orchestrator
                logger.debug(
                    "[ModelRouter] Short user input ({} chars) → orchestrator",
                    content_length,
                )
                return self.orchestrator_model
            elif content_length > USER_LONG_THRESHOLD:
                # Long user input = heavy processing = worker
                logger.debug(
                    "[ModelRouter] Long user input ({} chars) → worker",
                    content_length,
                )
                return self.worker_model
            else:
                # Medium length = orchestrator
                logger.debug(
                    "[ModelRouter] Medium user input ({} chars) → orchestrator",
                    content_length,
                )
                return self.orchestrator_model
        
        # Assistant message = orchestrator (response generation)
        if role == "assistant":
            logger.debug("[ModelRouter] Assistant message → orchestrator")
            return self.orchestrator_model
        
        # Default to orchestrator
        logger.debug("[ModelRouter] Unknown role '{}', defaulting to orchestrator", role)
        return self.orchestrator_model
    
    def _get_model_type(self, model: str) -> str:
        """Get human-readable model type."""
        if model == self.orchestrator_model:
            return f"orchestrator ({self.orchestrator_model})"
        return f"worker ({self.worker_model})"
    
    @property
    def default_model(self) -> str:
        """Get the default (orchestrator) model."""
        return self.orchestrator_model
    
    def get_worker_model(self) -> str:
        """Get the worker model for subagents."""
        return self.worker_model
    
    def get_orchestrator_model(self) -> str:
        """Get the orchestrator model."""
        return self.orchestrator_model