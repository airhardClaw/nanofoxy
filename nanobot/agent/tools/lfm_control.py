"""Audio/LFM server control tool."""

import asyncio
import shutil
from pathlib import Path
from typing import Any

import aiohttp


class AudioControlTool:
    """Tool to control the LFM audio server (check status, start, stop, restart)."""

    def __init__(
        self,
        model_path: str = "",
        mmproj_path: str = "",
        vocoder_path: str = "",
        tokenizer_path: str = "",
        runner_path: str = "",
        host: str = "127.0.0.1",
        port: int = 2026,
    ):
        self._model_path = model_path or str(Path.home() / ".nanobot" / "lfm2.5-audio-models" / "LFM2.5-Audio-1.5B-Q8_0.gguf")
        self._mmproj_path = mmproj_path or str(Path.home() / ".nanobot" / "lfm2.5-audio-models" / "mmproj-LFM2.5-Audio-1.5B-Q8_0.gguf")
        self._vocoder_path = vocoder_path or str(Path.home() / ".nanobot" / "lfm2.5-audio-models" / "vocoder-LFM2.5-Audio-1.5B-Q8_0.gguf")
        self._tokenizer_path = tokenizer_path or str(Path.home() / ".nanobot" / "lfm2.5-audio-models" / "tokenizer-LFM2.5-Audio-1.5B-Q8_0.gguf")
        self._runner_path = runner_path or str(Path.home() / ".nanobot" / "lfm2.5-audio-models" / "runners" / "llama-liquid-audio-server")
        self._host = host
        self._port = port
        self._url = f"http://{host}:{port}"

    @property
    def name(self) -> str:
        return "audio_control"

    @property
    def description(self) -> str:
        return (
            "Control the LFM audio server. "
            "Use action='check' to verify server is running, "
            "action='start' to start the server, "
            "action='stop' to stop it, "
            "action='restart' to restart it. "
            "Returns server status and information."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: check, start, stop, or restart",
                    "enum": ["check", "start", "stop", "restart"]
                }
            },
            "required": ["action"]
        }

    def to_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if "action" not in params:
            errors.append("Missing required parameter: action")
        elif params["action"] not in ("check", "start", "stop", "restart"):
            errors.append("Invalid action: must be check, start, stop, or restart")
        return errors

    async def execute(self, action: str = "check", **kwargs: Any) -> str:
        """Execute audio control action."""
        if action == "check":
            return await self._check_status()
        elif action == "start":
            return await self._start_server()
        elif action == "stop":
            return await self._stop_server()
        elif action == "restart":
            return await self._restart_server()
        return f"Unknown action: {action}"

    async def _check_status(self) -> str:
        """Check if the LFM server is running."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        return f"Server running at {self._url}"
                    else:
                        return f"Server returned status {response.status}"
        except aiohttp.ClientConnectorError:
            return f"Server not running at {self._url}"
        except Exception as e:
            return f"Error checking server: {str(e)}"

    async def _start_server(self) -> str:
        """Start the LFM server."""
        if shutil.which(self._runner_path) is None:
            return f"Error: Runner not found at {self._runner_path}"

        model = Path(self._model_path)
        if not model.exists():
            return f"Error: Model not found at {self._model_path}"

        try:
            process = await asyncio.create_subprocess_exec(
                self._runner_path,
                "-m", self._model_path,
                "-mm", self._mmproj_path,
                "-mv", self._vocoder_path,
                "-ml", self._tokenizer_path,
                "--host", self._host,
                "--port", str(self._port),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.sleep(2)

            if process.returncode == 0 or process.returncode is None:
                return f"Server starting at {self._url}"
            else:
                return f"Server failed to start (exit code: {process.returncode})"
        except Exception as e:
            return f"Error starting server: {str(e)}"

    async def _stop_server(self) -> str:
        """Stop the LFM server."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "pkill", "-f", "llama-liquid-audio-server",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()
            return "Server stopped"
        except Exception as e:
            return f"Error stopping server: {str(e)}"

    async def _restart_server(self) -> str:
        """Restart the LFM server."""
        await self._stop_server()
        await asyncio.sleep(1)
        return await self._start_server()