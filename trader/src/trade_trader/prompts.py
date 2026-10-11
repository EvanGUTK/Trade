"""Loader for the Trader's prompts, shipped as package data under ``prompts/``."""

from __future__ import annotations

from importlib import resources

SYSTEM_PROMPT_RESOURCE = "prompts/system.md"


def load_system_prompt() -> str:
    """The Trader's system prompt, verbatim.

    It is frozen text so that it caches as a stable prefix (root CLAUDE.md §7):
    nothing volatile (clock, portfolio) is ever interpolated into it.
    """
    text = resources.files("trade_trader").joinpath(SYSTEM_PROMPT_RESOURCE).read_text("utf-8")
    if not text.strip():
        raise RuntimeError(f"{SYSTEM_PROMPT_RESOURCE} is empty")
    return text
