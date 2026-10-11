"""``python -m trade_strategies`` — the strategy runner CLI.

Phase 0: argparse stub that documents the planned flags. Phase 1 wires it to the
gateway (docs/ARCHITECTURE.md §5): subscribe to bars over WebSocket, run the
strategy in the sandbox subprocess, submit orders over REST.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

DEFAULT_GATEWAY = "http://127.0.0.1:8787"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m trade_strategies",
        description="Run one strategy inside a gateway session (paper money only).",
        epilog="Phase 0: flags are parsed and echoed; the runner itself lands in Phase 1.",
    )
    parser.add_argument(
        "--strategy",
        metavar="MODULE:CLASS",
        default="trade_strategies.examples.sma_cross:SmaCross",
        help="import path of the Strategy class (default: %(default)s)",
    )
    parser.add_argument(
        "--session",
        metavar="ID",
        help="gateway session to trade in; must be mode backtest or paper",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        metavar="SYM",
        help="override the strategy's symbols",
    )
    parser.add_argument(
        "--tf",
        choices=["1m", "5m", "1d"],
        help="override the strategy's timeframe",
    )
    parser.add_argument(
        "--gateway",
        default=DEFAULT_GATEWAY,
        help="gateway base URL, the only network destination the sandbox allows "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="seed handed to the strategy for any randomness (default: %(default)s)",
    )
    parser.add_argument(
        "--bar-budget-ms",
        type=int,
        default=250,
        help="CPU/time budget per on_bar call before the run is rejected (default: %(default)s)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print("planned: the strategy runner is implemented in Phase 1 (docs/ARCHITECTURE.md §5).")
    print(f"  strategy={args.strategy} session={args.session} gateway={args.gateway}")
    print(
        f"  symbols={args.symbols} tf={args.tf} seed={args.seed} bar_budget_ms={args.bar_budget_ms}"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
