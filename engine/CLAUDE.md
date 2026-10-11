# engine/ — CLAUDE.md

Inherits the root `CLAUDE.md` and `docs/ARCHITECTURE.md` §2–§3. Rules here only
tighten those. Read the root file first, then this one, then your brief.

## 1. Purpose and boundary

The engine is the deterministic simulation core: the same inputs and seed produce
the same event log, byte for byte. It is a child process of the gateway speaking
newline-delimited JSON-RPC 2.0 over stdin/stdout (§5), written in OCaml for algebraic
types, exact integers, and property tests (ADR 0001, `docs/adr/0001-language-split.md`).

Owns:
- **Clock** — the session's simulated time, advanced only by `market.bar`.
- **Paper broker** — order validation, acceptance, and the open-order book per session.
- **Fills and slippage** — the deterministic fill rules of §5.4 and pluggable slippage models.
- **Ledger** — cash, positions, realized and unrealized P&L, in exact integer micro-units.
- **Backtest** — a batch of bars and orders pushed through the same code path as paper-live.
- **Replay** — re-reading an event log to reproduce the final state exactly.
- **Metrics** — return, drawdown, Sharpe, Sortino, win rate, exposure, trade count.

Never does:
- **Network.** No sockets, HTTP, or DNS. The gateway owns every byte to the outside world.
- **Disk**, except reading the replay log at the path handed to `replay.load`. It never
  writes files; the gateway persists the events the engine emits on stdout.
- **Floats for money or quantity.** Everything monetary is `Int64` behind `Money.t`
  (and `Qty.t`, planned). Floats appear only in `Metrics` ratios, computed last.
- **Real orders.** There is no brokerage adapter and there never will be: ADR 0003,
  `docs/adr/0003-paper-money-only.md`. A `live_trading` flag is a rejected change.
- **Threads or domains.** Single-threaded, in-order. Determinism is the product.
- **Calendars.** v0 does not know market hours; the gateway filters bars.

## 2. Directory layout

```
engine/
├── dune-project            manifest: lang dune 3.17, package trade_engine, no opam file
├── .ocamlformat            version = 0.29.0, profile = default
├── Makefile                setup build check test fmt run clean (§4)
├── bin/
│   ├── dune                executable `main`, public name `trade_engine`
│   └── main.ml             stdin loop → Rpc.handle_line → stdout, flush per line; stderr logs
├── lib/                    library `trade_engine` (wrapped: Trade_engine.Money, …)
│   ├── dune
│   ├── money.ml/.mli       Money.t: int64 micro-dollars; checked add/sub/neg; exact mul_qty
│   ├── protocol.ml/.mli    JSON-RPC 2.0 codec: request, responses, notification, error codes
│   ├── rpc.ml/.mli         dispatch table (`ping` today); the only exception catch-all
│   ├── qty.ml/.mli         (planned) Qty.t: int64 micro-shares, signed, checked
│   ├── clock.ml/.mli       (planned) RFC 3339 UTC parse/print; monotonic per session
│   ├── order.ml/.mli       (planned) order record, side/type/tif variants, validation
│   ├── fill.ml/.mli        (planned) fill record; `evaluate : bar -> order -> fill option`
│   ├── slippage.ml/.mli    (planned) `None | Bps | Spread` as a closed variant
│   ├── ledger.ml/.mli      (planned) cash + positions; apply_fill, mark; invariant checks
│   ├── portfolio.ml/.mli   (planned) Portfolio snapshot type and JSON encoder
│   ├── session.ml/.mli     (planned) clock + ledger + open orders + seed + event log
│   ├── backtest.ml/.mli    (planned) run bars through a session; collect fills/marks/metrics
│   ├── replay.ml/.mli      (planned) read an event log, rebuild a session, verify
│   └── metrics.ml/.mli     (planned) Metrics from the mark series and fills
└── test/
    ├── dune                test executable `test_trade_engine` (alcotest)
    ├── test_trade_engine.ml  runner: registers every suite below
    ├── test_money.ml       round-trips, identities, mul_qty scaling, overflow
    ├── test_rpc.ml         ping line, error codes, notifications, never-raises
    ├── gen.ml              (planned) qcheck generators: bars, orders, sessions
    ├── test_ledger.ml      (planned) the §6 invariants as properties
    └── golden/             (planned) recorded event logs with expected final portfolios
```

## 3. Toolchain and setup

| Tool | Version on the dev machine | Notes |
|---|---|---|
| OCaml, opam switch `default` | 5.4.1 | `/usr/bin/ocaml` is 5.5.0 but dune uses the switch |
| opam | 2.6.0 | `/usr/local/bin/opam` |
| dune | 3.24.2 | `dune-project` requires ≥ 3.17 |
| ocamlformat | 0.29.0 | must equal `version` in `.ocamlformat` |
| yojson | 3.0.0 | only JSON library allowed |
| alcotest | 1.9.1 | test framework |

Setup once per switch: `make engine-setup` from the repo root (or `make setup` here)
runs `opam install -y dune ocamlformat.0.29.0 yojson alcotest`. It never creates a
switch; create one by hand if you need one and say so in your report. The Makefile
runs every dune command through `opam exec --` when `dune` is not on PATH, so you
do not need `eval $(opam env)`. `dune-project` constrains `ocaml >= 5.0`. Bumping
ocamlformat touches `.ocamlformat`, `OPAM_PKGS`, and the table above in one commit;
adding a library touches `OPAM_PKGS`, `dune-project` `depends`, and a `dune` file.

There is no hosted CI (ADR 0005, `docs/adr/0005-no-hosted-ci.md`): the chief reruns
`make engine-check` and `make engine-test` in your worktree through
`scripts/review-branch.sh` before merging, so run them yourself before every push.

## 4. Commands

Run from the repo root as `make engine-<target>` or from `engine/` as `make <target>`.

| Target | Runs | Use |
|---|---|---|
| `setup` | `opam install -y dune ocamlformat.0.29.0 yojson alcotest` | once per switch |
| `build` | `dune build` | compiles lib, bin, tests |
| `check` | `dune build @fmt` then `dune build` | fails on any formatting diff; required before push |
| `test` | `dune test` | alcotest suites |
| `fmt` | `dune fmt` | rewrites sources; exits 1 when it changed something, rerun to confirm clean |
| `run` | `dune exec trade_engine` | the engine on your terminal's stdin/stdout |
| `clean` | `dune clean` | removes `_build/` |

Smoke test by hand:

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"ping"}' | make -s run
# {"jsonrpc":"2.0","id":1,"result":{"pong":true,"version":"0.0.1"}}
```

## 5. Protocol contract

Restates `docs/ARCHITECTURE.md` §3 in OCaml terms. That document wins on conflict
and changes only with an ADR; this section changes in the same commit.

### 5.1 Transport
- One JSON value per line, `\n`-terminated, UTF-8. Requests arrive on stdin;
  responses and notifications leave on stdout. stderr is logs only.
- Every reply is flushed before the next line is read; the gateway blocks on
  replies, so an unflushed reply is a deadlock. Single-threaded, strictly in order:
  notifications caused by request N precede N's reply, which precedes reading N+1.
- Blank or whitespace-only lines are ignored. EOF on stdin ends the process with exit 0.

### 5.2 Types in OCaml terms

```ocaml
(* Protocol: codec only, no I/O, never raises *)
type request = { id : Yojson.Safe.t option; meth : string; params : Yojson.Safe.t option }
(* id = None is a notification: no reply, even on error. id is echoed verbatim. *)
type error = { code : code; message : string; data : Yojson.Safe.t option }
val parse_request  : string -> (request, Yojson.Safe.t * error) result  (* id to answer with *)
val result_response : id:Yojson.Safe.t -> Yojson.Safe.t -> Yojson.Safe.t
val error_response  : id:Yojson.Safe.t -> error -> Yojson.Safe.t
val notification    : meth:string -> Yojson.Safe.t -> Yojson.Safe.t
(* Rpc: dispatch, the only catch-all *)
val dispatch    : Protocol.request -> (Yojson.Safe.t, Protocol.error) result
val handle_line : string -> string option   (* None: nothing is owed *)
```

Method handlers (planned) have the shape
`Session.registry -> Yojson.Safe.t option -> (Yojson.Safe.t, Protocol.error) result`
and never raise. The registry is the only mutable state and lives in `Rpc`.

### 5.3 Micro-unit convention
- Money: `int64` micro-dollars, `1 USD = 1_000_000`. `Money.of_micro` and `to_micro`
  exist for the boundary; everything else uses `Money.t`.
- Quantity: `int64` micro-shares, `1 share = 1_000_000`, signed (negative is short).
- Position value: `Money.mul_qty price ~qty_micro`, exact and overflow-checked. The
  fractional micro-share remainder truncates toward zero on the magnitude, sign applied
  afterwards, so a buy and a sell of the same quantity at the same price net to zero.
- On the wire these are JSON integers. Decoders (planned, in `Protocol`) accept
  `` `Int `` and `` `Intlit `` and reject `` `Float `` with `-32006`, even `100.0`.
- Times: RFC 3339 UTC strings with a `Z` suffix, e.g. `2026-10-10T14:30:00Z`.
  `Clock` (planned) parses once into an integer instant and compares integers.

### 5.4 Fill rules (v0)

| Order | Fills when | At |
|---|---|---|
| `market` | the next `market.bar` after acceptance | that bar's open, plus slippage |
| `limit` buy / sell | bar `l <= limit` / bar `h >= limit` | the limit price |
| `stop` | the bar range crosses the stop | triggers, then fills as market on the next bar's open plus slippage |

- No partial fills. Shorting allowed with 100% margin: cash must cover the full notional.
- Commission per fill: `max (mul_qty per_share_micro ~qty_micro:|qty|) min_micro`
  (engine reading of `commission: {per_share_micro, min_micro}`).
- `tif`: `day` orders expire at the first bar whose UTC date differs from the
  acceptance bar; `gtc` persists until filled or cancelled (engine reading, not yet
  in ARCHITECTURE §3; propose there before implementing).
- Rejections are results, not errors: `order.submit` returns `status: "rejected"` with
  a `reason` for insufficient cash or margin, unknown symbol (no bar seen yet),
  `qty_micro <= 0`, or a missing `limit_micro`/`stop_micro` for the type.
- Slippage models: `none`, `bps` (fixed basis points against the side), `spread`
  (half the bar's high-low range against the side). All deterministic; the session
  `seed` is reserved for a future randomized model and must feed a session-owned PRNG.

### 5.5 Ordering guarantees
Within one `market.bar`, in this order: advance the clock (`-32004` if `t` is older
than the session clock), expire `day` orders, evaluate open orders against the bar in
acceptance order (ascending `order_id`) emitting one `fill` notification each, mark
the portfolio emitting one `mark`, then write the `{fills, mark}` reply.
`order.submit` never fills on the submitting call; fills happen on bars only. Order ids are
a per-session counter, never time or randomness. Event-log, stdout, and replay order coincide.

### 5.6 Error codes

| Code | `Protocol.code` | Meaning | Emitted today |
|---|---|---|---|
| -32700 | `Parse_error` | line is not valid JSON | yes |
| -32600 | `Invalid_request` | valid JSON but not a JSON-RPC 2.0 request object | yes |
| -32601 | `Method_not_found` | unknown method | yes |
| -32602 | `Invalid_params` | params fail the method's schema | planned |
| -32603 | `Internal_error` | an exception escaped a handler; always a bug | yes, via the `Rpc` catch-all |
| -32000 | `Invariant_violation` | a ledger invariant failed; the session is poisoned | planned |
| -32001 | `Unknown_session` | no such `session_id` | planned |
| -32002 | `Session_exists` | `session.create` with a live id | planned |
| -32003 | `Unknown_order` | `order.cancel` on an id that is not open | planned |
| -32004 | `Clock_regression` | bar `t` older than the session clock | planned |
| -32005 | `Replay_failed` | log unreadable or final state did not verify | planned |
| -32006 | `Invalid_amount` | money or quantity field is not a 64-bit integer | planned |
| -32007..-32099 | — | reserved; allocate here and in `Protocol.code` in the same commit | — |

## 6. Core invariants and how they are tested

| Invariant | Statement | Tested now | Planned |
|---|---|---|---|
| Equity identity | at every mark, `equity = cash + Σ mul_qty mark_price qty` | — | qcheck: random bars and orders, checked after every `market.bar` |
| Fills sum to position | per symbol, `Σ signed fill qty = position qty` | — | qcheck, plus unit cases for long→short flips |
| Conservation | `Δcash = -(Σ fill value + commission)`; no money created or destroyed | `test_money.ml`: buy + sell net to zero, add/sub identities | qcheck over fill sequences |
| Replay | replaying the event log yields the live `Portfolio` exactly | — | golden logs in `test/golden/` through `Replay.load` |
| Determinism | same inputs and seed produce byte-identical stdout | — | run a backtest twice in-process, compare event logs |
| No overflow | arithmetic never wraps | `test_money.ml`: `max + 1`, `min - 1`, `neg min`, `mul_qty` overflow | qcheck on `Money` and `Qty` |
| Robust protocol | malformed input never kills the process | `test_rpc.ml`: never-raises, every error code | fuzz corpus |

Framework: alcotest now (`make test`); `qcheck` and `qcheck-alcotest` are planned and
enter `OPAM_PKGS`, `dune-project`, and `test/dune` with the first property. At runtime
the ledger checks the equity identity after every mark; on failure the session is
poisoned and every later call on it returns `-32000`. Never patch a ledger silently.

## 7. Code conventions

Tightens root §6.
- Every module in `lib/` has an `.mli`, and every `val` in it has a doc comment. Types
  that cross the protocol document their JSON shape there.
- `result` at every boundary. Exceptions do not cross `Rpc`: `Rpc.handle_line` has the
  only catch-all. Inside the library, exceptions are allowed only for invariant
  violations impossible with valid inputs (`Money.Overflow`), documented at the raise site.
- `Int64` is hidden behind `Money.t` and `Qty.t` (planned). No `Int64.*` on money
  outside `money.ml`. No `float` in any type that holds money or quantity.
- No `Obj.magic`, no `Marshal`, no `Stdlib.compare` or `=` on records or variants with
  payloads: use `Money.equal`, `Int64.equal`, `String.equal`, or a hand-written
  `equal`. Polymorphic equality on `Yojson.Safe.t` is acceptable in tests only.
- Naming: modules are nouns (`Ledger`), functions verbs (`apply_fill`), constructors
  `Capitalized_snake`, JSON fields exactly as ARCHITECTURE (`qty_micro`), every micro-unit
  integer suffixed `_micro`. Variants are closed; `_` wildcards only over `Yojson.Safe.t`.
- `lib/` does no I/O. `bin/main.ml` owns stdin and stdout; `Replay` (planned) is the
  one library module that may open a file, read-only, at the path it is given.
- Yojson: build with `` `Assoc `` lists in the field order ARCHITECTURE lists; decode
  by pattern matching. `Yojson.Safe.Util` raises, so it is for tests only.
- Formatting: ocamlformat default profile, version pinned; `make check` fails on any
  diff. No `[@@@ocamlformat "disable"]`. Warnings are errors under dune's dev profile;
  no `[@warning "-…"]` without a comment saying why.
- Tests: one `test_<module>.ml` per module, registered in `test_trade_engine.ml`. Test
  names state the property ("buy + sell = 0"), not the function name.

## 8. Recipes

### Add a JSON-RPC method
1. Make sure the method, params, and result are in `docs/ARCHITECTURE.md` §3. If not,
   that is a protocol change: ADR first, doc and code in the same commit.
2. Define the params and result types with their decoder and encoder in the owning
   module (`lib/order.ml` for `order.*`). Decoders return `(t, Protocol.error) result`
   with `Invalid_params` and a message naming the field.
3. Add a case to `Rpc.dispatch` in `lib/rpc.ml`. The handler never raises.
4. Add tests in `test/test_rpc.ml`: one happy path, one `-32602`, and, if the method
   emits notifications, one case checking their order relative to the reply (§5.5).
5. Bump `Rpc.version` if the wire contract changed. `make check && make test`.

### Add an order type
1. Extend the closed variant `Order.kind` in `lib/order.ml` and `.mli` plus its JSON
   codec; a missing price for the type is a `status: "rejected"` result.
2. Add the fill rule to `Fill.evaluate` in `lib/fill.ml` (`bar -> order -> fill option`),
   total and pure. Update the table in §5.4 here and ARCHITECTURE §3 in the same commit.
3. Add `test/test_fill.ml` cases for fill, no fill, and the boundary where the bar
   touches the price exactly; add the type to the qcheck generator in `test/gen.ml`.

### Add a slippage model
1. Add a constructor to `Slippage.model` in `lib/slippage.ml` and its decoding from the
   `slippage: {model, bps?}` object of `session.create`.
2. Implement `Slippage.apply : model -> side -> bar -> Money.t -> Money.t` (reference
   price to fill price). Pure; randomness, if any, comes from the session PRNG state.
3. Property in `test/test_slippage.ml`: a buy never fills below the reference price, a
   sell never above it. Document the model in §5.4 and ARCHITECTURE §3.

### Add an invariant test
1. Add the invariant to the §6 table first, in words.
2. Write or extend the generator in `test/gen.ml`: bars with `l <= min o c`,
   `h >= max o c`, positive prices; orders drawn from every type.
3. Fold the generated inputs through `Session`, check the invariant after every
   `market.bar`, and on failure print the event log so the case is replayable.
4. Register with `QCheck_alcotest.to_alcotest` in `test_trade_engine.ml`. Keep
   `count` at 1000 and the whole suite under 10 seconds.

## 9. Pitfalls

- **`mul_qty` overflow.** `price_micro × qty_micro` overflows `int64` once the notional
  passes about $9.2 million, which is routine. `Money.mul_qty` splits the quantity into
  whole and fractional shares to stay exact. Never reimplement it with `Int64.mul`.
- **Floats from yojson.** `Yojson.Safe.from_string "100.0"` yields `` `Float ``, and so
  does `"1e6"`. Decode money only from `` `Int `` and `` `Intlit `` (a number beyond
  OCaml's 63-bit `int`); parse `Intlit` with `Int64.of_string_opt`, `None` is `-32006`.
- **Stdout buffering.** OCaml buffers stdout. Every reply ends with `flush stdout`; a
  forgotten flush looks like a hung engine from the gateway's side.
- **Partial lines.** `In_channel.input_line` returns only complete lines, so a request
  split across pipe writes is parsed once, when its `\n` arrives. Never read into a
  fixed buffer and parse fragments. A final line without `\n` is still delivered.
- **Timezones.** All timestamps are RFC 3339 UTC with `Z`. Reject offsets such as
  `+02:00` rather than converting; the gateway normalizes. Never use `Unix.localtime`.
- **`_build/` is gitignored**, as are `_opam/` and `*.install`. Stage with
  `git add -A -- engine`, never `git add .` from the repo root.
- **ocamlformat version drift.** `make check` fails with a version mismatch when the
  switch has a different ocamlformat than `.ocamlformat`. Fix the switch
  (`opam install ocamlformat.0.29.0`), not the file.
- **`dune fmt` exits 1** after changing files. That is not a build failure; rerun.
- **Wrong compiler.** If a build error mentions OCaml 5.5.0, dune ran outside the
  switch. Use the Makefile or `opam exec -- dune`.

## 10. Definition of done (engine change)

Root §8 plus:
- [ ] `make engine-check && make engine-test` pass from the repo root.
- [ ] No new `float`, no `Int64.*` outside `money.ml` and `qty.ml`, no `Obj.magic`, no
      `raise` outside the documented exceptions. `grep -n 'Int64\.' lib/*.ml` is the check.
- [ ] Protocol-affecting change: `docs/ARCHITECTURE.md` §3 and §5 here updated in the
      same commit, `Rpc.version` bumped, ADR written if the contract changed.
- [ ] New method, order type, or model has tests under `test/`; if it touches the
      ledger, the §6 invariant tests still pass.
- [ ] Determinism preserved: no `Random.self_init`, `Unix.time`, `Sys.time`, or
      `Hashtbl` iteration order in anything that reaches the event log.
- [ ] The report lists the exact commands run and the opam switch they ran in.

## 11. Phase plan

Root §10 for the engine:

- **Phase 1 — ledger, fills, backtest end to end.** `Qty`, `Clock`, `Order`, `Fill`,
  `Slippage` (`none`, `bps`, `spread`), `Ledger`, `Portfolio`, `Session`. Methods
  `session.create`, `session.close`, `market.bar`, `order.submit`, `order.cancel`,
  `portfolio.get`, `orders.list`, `fills.list`, `backtest.run`. Notifications `fill`,
  `reject`, `mark`. `Metrics` with all seven fields of ARCHITECTURE §3. qcheck
  properties for the three ARCHITECTURE invariants. Coverage ≥ 80% on `lib/`.
  `Rpc.version` becomes `0.1.0`.
- **Phase 2 — MCP and the Trader.** `Replay.load` with golden logs; `since` on
  `fills.list` and `status` on `orders.list`; per-session event sequence numbers that
  match the gateway's `events(seq)` column. Nothing Trader-specific: the engine sees
  only orders and never learns who is trading.
- **Phase 3 — game layer, providers, smoke.** Season scoring inputs in `Metrics`
  (risk-adjusted return against a benchmark series passed to `backtest.run`); a
  performance pass so a multi-year 1-minute backtest runs in seconds; a fuzz corpus
  for `Protocol`; multi-session isolation tests.

## Verification status

Every §4 command was run on 2026-10-10 in the `default` switch (OCaml 5.4.1, dune
3.24.2, ocamlformat 0.29.0, yojson 3.0.0, alcotest 1.9.1): `make check` passes, `make
test` runs 17 tests green, the §4 smoke test printed the line shown. No other compiler
has been tried; there is no hosted CI (ADR 0005), so the chief's review is the rerun.
