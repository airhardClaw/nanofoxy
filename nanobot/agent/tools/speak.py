"""Speak tool for text-to-speech using LFM2.5-Audio."""

import asyncio
import tempfile
from typing import Any

import aiohttp


class SpeakTool:
    """Tool to convert text to speech using LFM2.5-Audio."""

    def __init__(self, tts_url: str = "http://127.0.0.1:2026"):
        self._tts_url = tts_url

    @property
    def name(self) -> str:
        return "speak"

    @property
    def description(self) -> str:
        return (
            "Convert text to speech audio using LFM2.5-Audio TTS. "
            "Use this to speak responses aloud to the user. "
            "Returns the path to the audio file which can be sent via the message tool."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to convert to speech"
                },
                "voice_style": {
                    "type": "string",
                    "description": "Optional voice style (e.g., 'UK male', 'US female')"
                }
            },
            "required": ["text"]
        }

    def to_schema(self) -> dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def cast_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Cast parameters to correct types."""
        return params

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """Validate parameters."""
        errors = []
        if "text" not in params:
            errors.append("Missing required parameter: text")
        return errors

    async def execute(
        self,
        text: str,
        voice_style: str | None = None,
        **kwargs: Any
    ) -> str:
        """Execute TTS request."""
        prompt = "Perform TTS. Respond with natural speech."
        if voice_style:
            prompt = f"Perform TTS. Use a {voice_style} voice. Respond with natural speech."

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._tts_url}/tts",
                    json={"text": text, "prompt": prompt},
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return f"TTS error ({response.status}): {error_text}"

                    audio_data = await response.read()

                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        f.write(audio_data)
                        audio_path = f.name

                    return f"Audio generated: {audio_path}. Use message tool with media=['{audio_path}'] to send to user."

        except asyncio.TimeoutError:
            return "Error: TTS request timed out"
        except aiohttp.ClientConnectorError:
            return "Error: Cannot connect to TTS server. Is it running on port 2026?"
        except Exception as e:
            return f"TTS error: {str(e)}"
