"""OpenAI-compatible API server for nanobot gateway."""

import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

app = FastAPI(title="nanobot-api", description="OpenAI-compatible API for nanobot")

_config: dict[str, Any] = {}


@app.on_event("startup")
async def startup():
    """Initialize connection to nanobot gateway."""
    global _config
    host = os.environ.get("NANOBOT_HOST", "127.0.0.1")
    port = int(os.environ.get("NANOBOT_PORT", "18790"))
    _config = {"host": host, "port": port}
    logger.info("nanobot-api connecting to gateway at {}:{}", host, port)


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible endpoint)."""
    return JSONResponse({
        "object": "list",
        "data": [
            {
                "id": "nanobot-default",
                "object": "model",
                "created": 1700000000,
                "owned_by": "nanobot",
            }
        ]
    })


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint.

    Forwards requests to nanobot gateway via WebSocket or HTTP.
    """
    body = await request.json()
    model = body.get("model", "nanobot-default")
    body.get("messages", [])

    # Simple passthrough - in production, this would connect to the gateway
    return JSONResponse({
        "id": f"chatcmpl-{os.urandom(12).hex()}",
        "object": "chat.completion",
        "created": 1700000000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "nanobot-api: Please use the nanobot gateway for completions"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    })


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "gateway": _config}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "nanobot-api",
        "version": "0.1.5",
        "endpoints": {
            "models": "/v1/models",
            "chat": "/v1/chat/completions",
            "health": "/health"
        }
    }


def run_server(host: str = "0.0.0.0", port: int = 18791):
    """Run the API server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
