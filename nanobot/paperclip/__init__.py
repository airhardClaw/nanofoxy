"""Paperclip task management integration for nanobot."""

from nanobot.paperclip.client import PaperclipClient
from nanobot.paperclip.models import Issue, IssueComment
from nanobot.paperclip.poller import PaperclipTaskPoller

__all__ = [
    "PaperclipClient",
    "PaperclipTaskPoller",
    "Issue",
    "IssueComment",
]
