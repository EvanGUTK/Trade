# strategies/ — CLAUDE.md

Inherits the root `CLAUDE.md` and `docs/ARCHITECTURE.md` §3 and §5. This file only
tightens them. Read both before editing anything here.

## 1. Purpose and boundary

`strategies/` is the strategy SDK (`trade_strategies.sdk`), the sandboxed runner that
executes strategies against the gateway, and the example strategies. It is the code
the Trader writes, so every rule below assumes strategy source is untrusted.

- Talks to the gateway only: WebSocket for bars and fills, REST for orders. Never the
  engine, never the Anthropic API, never a brokerage (`docs/adr/0003-paper-money-only.md`).
- AI reaches this component only through `mcp/` (`strategy.put`, `strategy.lint`,
  `backtest.run`), never by importing it (`docs/adr/0002-mcp-only-ai-boundary.md`).
- No `live_trading` flag, no brokerage SDK, no order path that bypasses the gateway.

## 2. Directory layout

```
strategies/
├── Makefile                      setup check test fmt run build
├── pyproject.toml                uv project; ruff, mypy --strict, pytest config
├── uv.lock                       committed; regenerate with `uv lock`
├── src/trade_strategies/
│   ├── __init__.py               public re-exports (the SDK surface)
│   ├── sdk.py                    Bar Order Fill Position Portfolio; Strategy + Context protocols
│   ├── indicators.py             pure helpers over int series (sma); Fraction, never float
│   ├── testing.py                RecordingContext: in-memory Context for unit tests
│   ├── examples/sma_cross.py     20/50 SMA crossover, the reference strategy
│   ├── __main__.py               `python -m trade_strategies` (argparse stub until Phase 1)
│   ├── runner/                   (planned) gateway WS/REST client, run loop, sandbox host
│   ├── sandbox/                  (planned) guest process: import allowlist, budgets, RO fs
│   └── lint.py                   (planned) static rules behind MCP `strategy.lint`
└── tests/                        pytest, one file per module, strictly typed
```

## 3. Toolchain and setup

| Tool | Pinned by | Notes |
|---|---|---|
| Python 3.14 | `requires-python = ">=3.14"` | uv resolves the interpreter (`uv python list`) |
| uv 0.12 | root CLAUDE.md §4 | `uv sync` creates `.venv` with runtime + `dev` group |
| ruff 0.17 | `uv.lock` | config in `[tool.ruff]`; line length 100; `target-version = "py314"` |
| mypy 2.4 | `uv.lock` | `[tool.mypy] strict = true`, `pydantic.mypy` plugin, `warn_unreachable` |
| pytest 9 | `uv.lock` | `asyncio_mode = "auto"` (pytest-asyncio) |

Build backend is `uv_build`; the module lives in `src/trade_strategies` and ships `py.typed`.
CI (`.github/workflows/ci.yml`, job `python`) uses `astral-sh/setup-uv@v6` and
`actions/setup-python@v5` with 3.14, then runs `make strategies-setup && make
strategies-check && make strategies-test`. Run exactly that locally before pushing.

## 4. Commands

All targets are real. Run them from `strategies/`, or from the repo root as
`make strategies-<target>`.

| Target | Runs | Use |
|---|---|---|
| `make setup` | `uv sync` | once, and after any `pyproject.toml` change |
| `make check` | `ruff format --check .` · `ruff check .` · `mypy src tests` | before every commit |
| `make test` | `pytest -q` | before every commit |
| `make fmt` | `ruff format .` · `ruff check --fix .` | fix what `check` reports |
| `make run` | `python -m trade_strategies --help` | shows the runner flags (Phase 1 wires them) |
| `make build` | `uv build` | sdist + wheel into `dist/` (gitignored) |

Dependency changes: edit `pyproject.toml`, run `uv lock`, commit `uv.lock` in the
same commit (`build(strategies): …`). Upgrade one package: `uv lock --upgrade-package ruff`.

## 5. Contracts

### 5.1 Units (ARCHITECTURE §3)

| Quantity | Python type | Wire | Helper |
|---|---|---|---|
| money | `int` micro-dollars, 1 USD = 1_000_000 | integer | `to_micro("101.25")`, `from_micro()` for display only |
| shares | `int` micro-shares | integer | `MICRO` = 1_000_000 |
| time | tz-aware UTC `datetime` | RFC 3339 string | naive datetimes are rejected |
| derived values | `fractions.Fraction` | never serialized | `indicators.sma()` |

No `float` crosses any boundary and none appears in `src/`. Two runs over the same
bars must produce byte-identical orders on every machine.

### 5.2 Wire models (`sdk.py`)

All models: `frozen=True`, `extra="forbid"`, accept and emit wire aliases.

| Model | Fields (wire alias) | Validation |
|---|---|---|
| `Bar` | `symbol`, `t`, `open(o)`, `high(h)`, `low(l)`, `close(c)`, `volume(v)` | prices > 0, `low <= min(o,c)`, `max(o,c) <= high` |
| `Order` | `client_id`, `symbol`, `side`, `qty_micro`, `order_type(type)`, `limit_micro?`, `stop_micro?`, `tif` | `qty > 0`; limit needs `limit_micro`; stop needs `stop_micro`; market carries neither |
| `Fill` | `order_id`, `symbol`, `side`, `qty_micro`, `price_micro`, `commission_micro`, `t` | engine `fill` event minus `session_id` |
| `Position` | `symbol`, `qty_micro` (signed), `avg_cost_micro`, `mark_micro`, `unrealized_micro` | |
| `Portfolio` | `cash_micro`, `equity_micro`, `realized_micro`, `positions` | `.qty(symbol)`, `.position(symbol)` |

The gateway's `bars:{symbol}:{tf}` payload is `{t,o,h,l,c,v}`; the runner adds `symbol`.

### 5.3 The protocols (ARCHITECTURE §5, verbatim shape)

```python
class Strategy(Protocol):
    name: str
    version: str
    symbols: list[str]
    timeframe: Literal["1m", "5m", "1d"]

    def on_start(self, ctx: Context) -> None: ...
    def on_bar(self, ctx: Context, bar: Bar) -> None: ...
    def on_fill(self, ctx: Context, fill: Fill) -> None: ...
    def on_stop(self, ctx: Context) -> None: ...


class Context(Protocol):
    @property
    def portfolio(self) -> Portfolio: ...
    def buy(
        self,
        symbol: str,
        qty_micro: int,
        *,
        order_type="market",
        limit_micro=None,
        stop_micro=None,
        tif="day",
    ) -> str: ...
    def sell(
        self,
        symbol: str,
        qty_micro: int,
        *,
        order_type="market",
        limit_micro=None,
        stop_micro=None,
        tif="day",
    ) -> str: ...
    def history(self, n: int, symbol: str | None = None) -> list[Bar]: ...
    def log(self, message: str) -> None: ...
```

Semantics the runner guarantees: `on_bar` is called once per bar per subscribed symbol
in time order; `buy`/`sell` return the order's `client_id` and the matching `Fill` (or a
reject) arrives through `on_fill`, at the *next* bar's open for market orders (engine
fill rules); `history(n)` is the last `n` bars seen, oldest first; `log` lines land on
the strategy's kanban card; `portfolio` reflects the engine's latest mark.

### 5.4 Runner flow against the gateway (Phase 1, planned)

1. The gateway's `POST /sessions/{id}/runs` spawns `python -m trade_strategies
   --strategy <id>@<version> --session <id> --gateway http://127.0.0.1:8787` (the
   same flags `make run` prints). `--session` must be a `backtest` or `paper` session.
2. The runner fetches the source via `GET /strategies/{id}/versions`, lints it (§7),
   and starts the sandbox guest (§6) with the source and `--seed`.
3. It opens `ws://127.0.0.1:8787/ws` and sends
   `{"type":"subscribe","topics":["bars:SPY:1d","session:<id>"]}`.
4. Each `bars:*` message becomes a `Bar` → guest `on_bar`; each `session:*` fill → `on_fill`.
5. Orders the guest emits are posted by the *host* to `POST /sessions/{id}/orders` as
   `Order` JSON. The guest never holds a socket.
6. Backtests use the same loop fed from `GET /bars/{symbol}?tf=&from=&to=` in time
   order; the gateway drives the engine's `backtest.run` and stores `Metrics` on the run.

### 5.5 How Trader-written code enters

MCP `strategy.put` (**W**) → gateway `POST /strategies` → a new `strategy_versions`
row (`source`, `sha256`, `created_by="trader"`, `lint_json`) → `strategy.lint` →
`backtest.run`. Source is stored as text; nothing imports it. It executes only
inside the sandbox guest, and only after lint passes.

## 6. Sandbox (ARCHITECTURE §5; Phase 1, planned)

| Control | Rule |
|---|---|
| Process | one guest subprocess per run; host ↔ guest over a pipe with newline-delimited JSON; the guest has no network at all, so "no network except the gateway URL" holds because only the host talks to the gateway |
| Imports | allowlist: `math`, `statistics`, `collections`, `dataclasses`, `fractions`, `numpy`, `pandas`, `trade_strategies`; enforced by a meta-path finder installed before the strategy module loads; anything else raises a violation |
| Budget per bar | wall clock `--bar-budget-ms` (default 250); `RLIMIT_CPU` and `RLIMIT_AS` on the guest; exceeding either is a violation |
| Filesystem | read-only: cwd is an empty temp dir, `RLIMIT_FSIZE=0`, `open()` for write and `os`/`pathlib` writes are violations |
| Clock and randomness | the runner calls `random.seed(seed)` in the guest before `on_start`; strategies must not reseed and must not read the wall clock; `bar.t` is the only time |
| Violation | the host kills the guest, the run ends with status `rejected`, the gateway records a `reject` with the reason on the card; no metrics are produced for a rejected run |

Determinism follows: same source, same bars, same seed ⇒ same orders ⇒ same fills.

## 7. Strategy lint rules (`lint.py`, Phase 1, planned)

Applied by MCP `strategy.lint` and again by the runner before every run. Output is
`{"ok": bool, "findings": [{"rule", "line", "message"}]}`, stored in `strategy_versions.lint_json`.

| Rule | Rejects |
|---|---|
| S001 | any import outside the §6 allowlist |
| S002 | no class satisfying `Strategy` (all four attributes, all four methods) |
| S003 | `version` not semver, or equal to an existing version of the same strategy |
| S004 | `exec`, `eval`, `__import__`, `compile`, `open`, `getattr` with a string literal |
| S005 | wall clock or unseeded randomness (`time.time`, `datetime.now`, `random.random` before `seed`) |
| S006 | `float` literals or `/` on values passed to `buy`/`sell` (money and quantity are ints) |
| S007 | network, subprocess, threading, signal, ctypes |
| S008 | source over 2000 lines, or `on_bar` body missing |

## 8. Code conventions

- ruff rule set in `pyproject.toml` (`E W F I N UP B A C4 SIM PT ANN RUF`), line length 100,
  `from __future__ import annotations` in every module, full annotations (`ANN`).
- mypy strict on `src` *and* `tests`; `pydantic.mypy` plugin with `init_typed`.
- pydantic only at boundaries: wire models live in `sdk.py`; nothing builds raw dicts.
- Strategies are synchronous and pure. The runner (planned) is `asyncio`; it never
  calls strategy code from the event loop thread, always through the guest pipe.
- Logging: `logging.getLogger("trade_strategies.<module>")`; INFO is one line per run
  event; never log full gateway payloads above DEBUG; guest stdout/stderr is captured
  line by line into the run log and capped.
- Naming: class `CamelCase`; `name` snake_case and unique per owner; `version` semver.

## 9. Testing

- `tests/test_sdk.py` model validation and alias round trips; `tests/test_sma_cross.py`
  protocol satisfaction (`isinstance` with `runtime_checkable`), a buy then a sell on a
  synthetic series, determinism; `tests/test_cli.py` the stub.
- Use `RecordingContext` (`testing.py`) for *which orders* a strategy emits. It fills at
  the last close, charges no commission, applies no slippage, and is long-only; never
  assert money with it. Money is the engine's job and is tested by a backtest session.
- Planned with the runner: golden tests from recorded WebSocket fixtures (bars in →
  expected orders out), sandbox violation tests, and a coverage gate at 80% (root §6).

## 10. Recipes

**Write a strategy.** Copy `examples/sma_cross.py`. Declare `name`, `version`,
`symbols`, `timeframe: Timeframe` (annotate it, or mypy infers `str`). Keep state in
`__init__`, derive everything from `on_bar` arguments and `ctx`, never from imports of
`time` or `random`. Test it with `RecordingContext().run(MyStrategy(), bars)`.

**Add an indicator helper.** A pure function in `indicators.py` over `Sequence[int]`
returning `Fraction` or `int`; raise `ValueError` on a short window instead of returning
a partial value; add hand-computed cases to `tests/test_indicators.py`; export it from
`__init__.py` only if strategies need it.

**Run the example on synthetic data.**
```bash
cd strategies && uv run python -c "
from trade_strategies.examples.sma_cross import SmaCross
from trade_strategies.testing import RecordingContext
from tests.test_sma_cross import synthetic_series
ctx = RecordingContext(); ctx.run(SmaCross(), synthetic_series()); print(ctx.orders)"
```

**Change a dependency.** Edit `pyproject.toml` → `uv lock` → `make check && make test`
→ commit `pyproject.toml` and `uv.lock` together.

## 11. Pitfalls

- `timeframe = "1d"` without the `Timeframe` annotation does not satisfy the protocol.
- `runtime_checkable` `isinstance` checks attribute presence, not signatures; mypy is the real check.
- `Order(order_type="limit", ...)` in Python, `"type"` on the wire; `model_dump()` emits wire names.
- `//` floors toward negative infinity; mind signed micro values in short positions.
- `make check` type-checks tests too; an untyped fixture fails the build.
- `uv run` must be executed inside `strategies/`; from the root use `make strategies-<target>`.
- `symbols: list[str] = [...]` on a class needs `# noqa: RUF012`; never mutate it.

## 12. Definition of done

- [ ] `make check` and `make test` pass in `strategies/`; CI's `python` job is green.
- [ ] No `float`, no wall clock, no network, no `open()` in `src/` strategy paths.
- [ ] New wire fields appear in `sdk.py`, `docs/ARCHITECTURE.md` §3/§5, and this file in one commit.
- [ ] New lint rule: implementation, test, and the §7 table row in one commit.
- [ ] Commits are atomic and Conventional (`feat|fix|test|docs|build(strategies): …`) with the attribution footer.

## 13. Phase plan

| Phase | Deliverable |
|---|---|
| 0 (done) | SDK models and protocols, `indicators.sma`, `RecordingContext`, SMA example, CLI stub, this file |
| 1 | `runner/` (WS + REST client, run loop), `sandbox/` (guest, allowlist, budgets), `lint.py`, backtest end to end against the gateway, golden tests, coverage gate |
| 2 | `strategy.put` → lint → run contract tests with `mcp/`; Trader-written strategies through the full path |
| 3 | more indicators, multi-symbol examples, budget tuning from real runs |
