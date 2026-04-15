"""Speak tool for text-to-speech using LFM2.5-Audio CLI."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

LFM_CLI_PATH = "/home/sir-airhard/.nanobot/lfm2.5-audio-models/runners/llama-liquid-audio-ubuntu-x64/llama-liquid-audio-cli"
LFM_MODEL = "/home/sir-airhard/.nanobot/lfm2.5-audio-models/LFM2.5-Audio-1.5B-Q8_0.gguf"
LFM_MMPROJ = "/home/sir-airhard/.nanobot/lfm2.5-audio-models/mmproj-LFM2.5-Audio-1.5B-Q8_0.gguf"
LFM_VOCODER = "/home/sir-airhard/.nanobot/lfm2.5-audio-models/vocoder-LFM2.5-Audio-1.5B-Q8_0.gguf"
LFM_SPEAKER = "/home/sir-airhard/.nanobot/lfm2.5-audio-models/tokenizer-LFM2.5-Audio-1.5B-Q8_0.gguf"


class SpeakTool:
    """Tool to convert text to speech using LFM2.5-Audio CLI."""

    def __init__(self, workspace: str | None = None):
        self._workspace = workspace

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
                    "description": "Optional voice style hint (e.g., 'male', 'female', 'US', 'UK')"
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
        """Execute TTS request using CLI."""
        if not Path(LFM_CLI_PATH).exists():
            return f"Error: LFM CLI not found at {LFM_CLI_PATH}"

        for model_file in [LFM_MODEL, LFM_MMPROJ, LFM_VOCODER, LFM_SPEAKER]:
            if not Path(model_file).exists():
                return f"Error: Model file not found: {model_file}"

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name

        voice_style = voice_style or "US female"
        style_map = {
            "us male": "Perform TTS. Use the US male voice.",
            "us female": "Perform TTS. Use the US female voice.",
            "uk male": "Perform TTS. Use the UK male voice.",
            "uk female": "Perform TTS. Use the UK female voice.",
            "male": "Perform TTS. Use the US male voice.",
            "female": "Perform TTS. Use the US female voice.",
        }
        system_prompt = style_map.get(voice_style.lower(), style_map["us female"])

        cmd = [
            LFM_CLI_PATH,
            "-m", LFM_MODEL,
            "-mm", LFM_MMPROJ,
            "-mv", LFM_VOCODER,
            "--tts-speaker-file", LFM_SPEAKER,
            "-sys", system_prompt,
            "-p", text,
            "-o", output_path,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60.0
            )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                os.unlink(output_path) if os.path.exists(output_path) else None
                return f"TTS error: {error_msg[:200]}"

            if not os.path.exists(output_path):
                return "Error: TTS produced no output file"

            audio_path = output_path
            file_size = os.path.getsize(audio_path)
            if file_size == 0:
                os.unlink(audio_path)
                return "Error: TTS produced empty audio file"

            return f"Audio generated: {audio_path} ({file_size} bytes). Use message tool with media=['{audio_path}'] to send to user."

        except asyncio.TimeoutError:
            if os.path.exists(output_path):
                os.unlink(output_path)
            return "Error: TTS request timed out (>60s)"
        except FileNotFoundError:
            return f"Error: LFM CLI not found. Is the path correct?"
        except Exception as e:
            if os.path.exists(output_path):
                os.unlink(output_path)
            return f"TTS error: {str(e)}"