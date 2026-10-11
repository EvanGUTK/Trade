"""``python -m trade_trader`` — the Trader's two entry points.

``run``    the propose loop: write or revise one strategy, thesis first.
``review`` the post-mortem loop for one run: review row, memory update, at most
           one new version.

Phase 0: both print the intended flow and exit 0 (so ``make trader-run`` is
quiet). Neither imports the Anthropic SDK yet, so this module cannot make a
live API call by accident.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from trade_trader.config import TraderSettings

PROPOSE_FLOW = (
    "load settings and open the memory store (bootstrap default files)",
    "reread /memories/mistakes.md, then lessons.md and playbook.md",
    "connect to mcp/ as an MCP client; read board.get and journal.query (recent)",
    "tool-runner loop on TRADER_MODEL, effort high: choose one hypothesis",
    "strategy.put (new version) -> strategy.lint -> backtest.run",
    "journal.write kind=thesis referencing the run id, before reading results",
    "report; never board.move to Paper Live",
)

REVIEW_FLOW = (
    "load settings and open the memory store",
    "journal.query the thesis for --run-id; run.get, run.metrics, session.fills",
    "tool-runner loop on TRADER_MODEL, effort medium: compare outcome to thesis",
    "journal.write kind=review (outcome, metrics, cause, lesson, next change)",
    "update memory: lessons.md / mistakes.md / symbols/<SYM>.md",
    "at most one strategy.put + board.move (never to Paper Live); then stop",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m trade_trader",
        description="The Trader: a separate Claude agent that plays Trade over MCP.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="propose loop: write or revise one strategy (thesis first)")
    review = sub.add_parser("review", help="post-mortem loop for one run")
    review.add_argument("--run-id", required=True, help="run to review (journal thesis must exist)")
    return parser


def describe(settings: TraderSettings) -> str:
    """One line of config for logs. Never includes the key itself."""
    key = "set" if settings.has_api_key else "unset"
    return (
        f"model={settings.trader_model} data_dir={settings.trade_data_dir} "
        f"memory_dir={settings.memory_dir} api_key={key}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = TraderSettings()
    print(f"planned: trader {args.command} lands in Phase 2 (docs/ARCHITECTURE.md §7).")
    print(f"  {describe(settings)}")
    steps = PROPOSE_FLOW if args.command == "run" else REVIEW_FLOW
    if args.command == "review":
        print(f"  run_id={args.run_id}")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
