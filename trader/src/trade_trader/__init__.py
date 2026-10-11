"""The Trader: a separate Claude agent that plays Trade through MCP.

It is the only component that may import the Anthropic SDK
(docs/adr/0002-mcp-only-ai-boundary.md) and it trades paper money only
(docs/adr/0003-paper-money-only.md).
"""

DEFAULT_MODEL = "claude-opus-5-5"
"""Exact model id from root CLAUDE.md §7. Never append a date suffix."""
