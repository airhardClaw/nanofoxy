"""Web UI module for nanobot dashboard."""

__version__ = "0.1.0"

from nanobot.web.api import create_app, run_server

__all__ = ["create_app", "run_server"]
