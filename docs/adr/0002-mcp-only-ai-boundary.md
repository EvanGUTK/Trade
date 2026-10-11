# ADR 0002 — MCP is the only boundary between any AI and the simulator

Status: Accepted (2026-10-10)

## Context
The Trader (a separate Claude) must act on the simulator. Claude Code and claude.ai
should be able to as well. Scattering Anthropic SDK calls or direct DB access across
components would make the AI surface impossible to audit or sandbox.

## Decision
- `mcp/` is the single AI-facing surface. Its tools are schema-validated, mostly
  read-only, and paper-session-only.
- `trader/` is the only component that imports the Anthropic SDK, and it reaches the
  simulator only as an MCP client of `mcp/`.
- Strategy code produced by any AI executes only inside the strategy runner sandbox.

## Consequences
- Adding an AI capability means adding an MCP tool, with a schema and a test.
- The Trader can be swapped for another MCP client without touching the simulator.
- A second hop (trader → mcp → gateway) costs a few milliseconds; acceptable.
