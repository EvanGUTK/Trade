# web/ — CLAUDE.md

Inherits the root `CLAUDE.md`; every rule here only tightens it. Read the root file
first, then `docs/ARCHITECTURE.md` §4 (the API this UI consumes), §9, §10, then this.

## 1. Purpose and boundary

`web/` is the broker-style front end: dark, dense, chart-centric, with the kanban
**Strategy Board** as the game surface. It talks to the gateway on port 8787 over
REST and one WebSocket, and to nothing else (ARCHITECTURE §2). Rules:

- No business logic that belongs to the engine or gateway: no fill simulation, no
  P&L math beyond summing fields the gateway already sent, no bar aggregation.
- Money and quantities stay as integer micro-units (`Micro`) through fetch and
  store; formatters at the render edge produce strings (`fmtUsd`, `fmtQty`).
- Look, not brand (root §1.7): we copy layout, density, and palette. The name
  "WeBull", its logo, icons, fonts, screenshots, or CSS never appear in this tree.
- Paper money only. No code path, flag, or copy may suggest a real brokerage.

## 2. Directory layout

```
web/
├── Makefile  package.json  pnpm-lock.yaml  tsconfig.json  vite.config.ts
├── eslint.config.js  .prettierrc  .prettierignore  index.html
└── src/
    ├── main.tsx            React root, StrictMode, imports theme.css
    ├── App.tsx  App.css    shell: top bar, three columns, bottom tab strip
    ├── theme.css           every design token, defined once
    ├── vite-env.d.ts       typed import.meta.env (VITE_GATEWAY_URL)
    ├── api/
    │   ├── types.ts        §3/§4/§8 wire types, Micro, fmtUsd, fmtQty, topics
    │   ├── client.ts       typed fetch, ApiError, api.health
    │   └── ws.ts           (planned) single WS client, reconnect, resubscribe
    ├── store/              (planned) zustand slices: market session board game ui
    ├── components/         shared leaf components (StatusPill, …)
    ├── features/           (planned) one folder per panel, owning its CSS and tests
    │   ├── watchlist/  chart/  ticket/  positions/  orders/  board/  game/
    ├── app/                (planned) routing/tab shell once App.tsx outgrows one file
    └── test/setup.ts       vitest setup (Testing Library cleanup)
```

Cross-feature code goes in `components/`, `store/`, or `api/`, never in another feature.

## 3. Toolchain and setup

| Tool                                    | Version              | Note                                                                         |
| --------------------------------------- | -------------------- | ---------------------------------------------------------------------------- |
| Node / pnpm                             | 24.21 / 12.10        | root §4 pins; `engines` in package.json enforces `>=24`                      |
| TypeScript                              | 6.0.x                | TS 7 (native) is blocked until typescript-eslint peers it                    |
| Vite / plugin-react                     | 8.3 / 6.1            | Rolldown bundler, oxc transform                                              |
| React / react-dom                       | 19.3                 | function components only                                                     |
| vitest / RTL / jsdom                    | 5.0 / 16.3 / 30      | `globals: false`; import from `vitest` explicitly                            |
| eslint / typescript-eslint              | 10.12 / 8.71         | flat config only; `eslint-plugin-react-hooks` 7 (compiler rules on)          |
| prettier                                | 3.9.x                | single quotes, 100 cols, trailing commas                                     |
| zustand / lightweight-charts / @dnd-kit | 5.0 / 5.2 / 6.3+10.0 | state / candlestick+volume (`addSeries(CandlestickSeries, …)`) / kanban drag |

Setup: `cd web && make setup`. CI (`.github/workflows/ci.yml`, job `web`): `pnpm/action-setup@v4`
(`version: 12`), `actions/setup-node@v4` (`node-version: 24`, `cache: pnpm`,
`cache-dependency-path: web/pnpm-lock.yaml`), then `make web-setup && make web-check && make web-test`.
Do not add a `packageManager` field to package.json: `pnpm/action-setup` errors when both are set.

Environment (all optional; root `.env` is Vite's `envDir`):

| Variable            | Read by               | Default                 | Meaning                                                         |
| ------------------- | --------------------- | ----------------------- | --------------------------------------------------------------- |
| `TRADE_WEB_PORT`    | vite.config.ts        | `5173`                  | dev and preview port (`strictPort`)                             |
| `TRADE_GATEWAY_URL` | vite.config.ts        | `http://localhost:8787` | proxy target for `/api` and `/ws`                               |
| `VITE_GATEWAY_URL`  | browser (`client.ts`) | `http://localhost:8787` | REST/WS origin; set to `""` to go same-origin through the proxy |

## 4. Commands

Run from `web/`, or from the repo root as `make web-<target>`.

| Target       | Runs                                                                 |
| ------------ | -------------------------------------------------------------------- |
| `make setup` | `pnpm install --frozen-lockfile`, falling back to `pnpm install`     |
| `make check` | `prettier --check .` then `eslint .` then `tsc --noEmit`             |
| `make test`  | `vitest run`                                                         |
| `make fmt`   | `prettier --write .` then `eslint . --fix`                           |
| `make dev`   | `vite` on `TRADE_WEB_PORT`, proxying `/api` and `/ws` to the gateway |
| `make build` | `vite build` into `dist/` (gitignored)                               |

`make check && make test && make build` must pass before every commit; package.json has the same scripts.

## 5. Design system: the WeBull look

Tokens live in `src/theme.css` and nowhere else. Feature CSS uses `var(--…)` only.

- **Surfaces**: layered navy. `--bg-0 #0b0e11` canvas, `--bg-1 #141a1f` panels,
  `--bg-2 #1b232b` cards/inputs/table heads, `--bg-3 #232d37` hover/selected.
  `--border #262f38` 1px lines between every region; no drop shadows.
- **Text**: `--text #e6edf3`, `--text-muted #8b98a5` (labels, section heads),
  `--text-faint #5c6873` (disabled). Section heads are 12px uppercase muted.
- **Accent**: `--accent #3b8bff` for primary buttons, links, the selected tab
  indicator, focused inputs. Exactly one primary action per panel.
- **Up/down**: `--up #1fbf75`, `--down #f0525f`, with `--up-soft`/`--down-soft` 16%
  tints for row flashes and buy/sell toggles. Colour is never the only signal:
  pair with `▲`/`▼`, a sign, or a word. Never recolour text to grey to mean "flat".
- **Type**: system UI stack, 13px body, 12px dense tables, 11px chips;
  `font-variant-numeric: tabular-nums` globally so quote columns do not jitter.
  Prices and quantities use the `.num` class; monospace only in code/notes.
- **Density**: 28px rows, 8px gutters, 4px radius. Skeleton blocks (`--bg-2`
  pulsing to `--bg-3`) while loading; never a spinner.
- **Motion**: quote updates hold 60 fps: patch the store per symbol, subscribe with
  narrow selectors, flash a row by toggling a class, never re-render the list.
- **Layout**: desktop-first CSS grid, `240px | 1fr | 300px` under a 40px top bar,
  32px bottom tab strip on the centre column. Tablet (≤1024px) hides the
  watchlist (it returns as a drawer later); below 768px is unsupported in Phase 1.

Main screen (chart tab):

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ Trade   paper money · real market                      ● Gateway up · yahoo   │
├──────────────┬───────────────────────────────────────────┬────────────────────┤
│ WATCHLIST    │ AAPL  [1m] 5m 1d     O 188.90  H 189.40   │ ORDER TICKET       │
│ AAPL  189.12 │                      L 188.10  C 189.12   │ [ BUY ] [ SELL ]   │
│   ▲ +1.24%   │ ┌───────────────────────────────────────┐ │ Qty    [ 10     ]  │
│ SPY   512.40 │ │           ▐▌  ▐▌▐▌       ▐▌           │ │ Type   [Market ▾]  │
│   ▼ -0.31%   │ │     ▐▌▐▌ ▐▌  ▐▌    ▐▌▐▌ ▐▌  ▐▌ ▲ fill │ │ Limit  [        ]  │
│ TSLA  241.07 │ │  ▐▌▐▌  ▐▌         ▐▌       ▐▌         │ │ TIF    [Day    ▾]  │
│   ▲ +0.08%   │ │▐▌                                     │ │ Est.    $1,891.20  │
│              │ ├───────────────────────────────────────┤ │ [    Buy AAPL   ]  │
│              │ │ ▂▃▅▂▁▃▆▂▁▂▄▃▂▁▂  volume               │ ├────────────────────┤
│              │ └───────────────────────────────────────┘ │ POSITIONS  Orders  │
│ + Add symbol │                                           │ AAPL  10  +$12.40 ▲│
│              │                                           │ Cash   $98,108.80  │
├──────────────┴───────────────────────────────────────────┴────────────────────┤
│ [ Chart ]   Strategy Board                                                    │
└───────────────────────────────────────────────────────────────────────────────┘
```

Right column: ticket on top (Buy/Sell toggle tinted `--up-soft`/`--down-soft`, qty, type,
limit/stop price, TIF, estimated cost, one primary button), then a tabbed panel
`Positions | Orders | Fills` (planned). The bottom tab strip switches the centre panel.

Strategy Board tab:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ STRATEGY BOARD    Season Oct 2026 · 20 days left      XP 1,240 · Lvl 6   [LB]│
├───────────┬───────────┬───────────┬────────────┬───────────┬─────────────────┤
│BACKLOG 1  │RESEARCH 1 │BACKTEST 2 │PAPER LIVE 1│REVIEW 1   │RETIRED/PROMOTED │
│┌─────────┐│┌─────────┐│┌─────────┐│┌──────────┐│┌─────────┐│┌───────────────┐│
││Gap fade │││Mean rev │││Mom 5m   │││Pairs  v2 │││VWAP  v1 │││Buy&hold [H]  ✓││
││[T]   v1 │││[H]   v2 │││[T]   v3 │││[H] ● live│││[T]      ││└───────────────┘│
││no runs  │││no runs  │││S 1.4    │││S 0.9     │││S -0.2   ││┌───────────────┐│
│└─────────┘│└─────────┘││+$812 58%│││+$140 51% │││-$96 44% │││Scalper  [T]  ✗││
│           │           ││"stops…" ││└──────────┘││"review" ││└───────────────┘│
│           │           │└─────────┘│            │└─────────┘│                 │
│           │           │┌─────────┐│            │           │                 │
│           │           ││ORB   v4 ││            │           │                 │
│           │           ││[T] ⟳    ││            │           │← pending confirm│
│           │           ││→ Paper  ││            │           │                 │
│           │           │└─────────┘│            │           │                 │
├───────────┴───────────┴───────────┴────────────┴───────────┴─────────────────┤
│   Chart   [ Strategy Board ]                                                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 6. The Strategy Board (kanban)

Columns, in order, from root §9: `backlog → research → backtest → paper_live →
review → retired | promoted` (`BOARD_COLUMNS` in `api/types.ts`; the last two render
as one column with a divider). Column wire ids are snake_case; the gateway owns them.

Card anatomy (`features/board/Card.tsx`): name; owner badge `[H]` human / `[T]` Trader
(`Card.owner`); version chip; metric chips from `Card.metrics` (Sharpe, PnL via
`fmtUsd`, win rate) or "no runs"; last note, two lines, ellipsised; a status ribbon
for `paper_live` (`● live`) or a pending move (`⟳ → Paper`).

Drag rules (dnd-kit):

- `DndContext` with `PointerSensor` and `KeyboardSensor` (`sortableKeyboardCoordinates`),
  one `SortableContext` per column, `useSortable` per card. Provide
  `accessibility.announcements` so screen readers hear "Moved Momentum 5m to Backtest".
- `onDragEnd` applies the move optimistically to the `board` slice, then calls
  `PATCH /board/cards/{id}` with `{column, position}`. On error: restore the
  snapshot taken before the move and toast the gateway message.
- A drop into `paper_live` is **human-only** and always confirmed by a dialog that
  names the strategy, version, and session. Escape cancels; the card snaps back.
- The Trader never moves a card to `paper_live` (ARCHITECTURE §7). Its proposals
  arrive on the `board` topic and render in the card's current column with a
  pending ribbon and Confirm/Reject buttons. Confirm performs the human PATCH;
  Reject writes a note. Pending cards cannot be dragged.
- Within-column reordering is free; moves to earlier columns (demotions) need no confirmation.

Game surface (Phase 3): XP toast bottom-right for 4s naming the source (`+25 review
written`), season banner in the board header (`GET /game/season`), leaderboard panel
(`[LB]`, `GET /game/leaderboard`) human vs Trader. Display only; the gateway awards XP.

## 7. Data flow and state

One zustand store, five slices, each in `src/store/<slice>.ts` with its selectors:

| Slice     | Holds                                                                  | Hydrated by                              | Patched by WS topic           |
| --------- | ---------------------------------------------------------------------- | ---------------------------------------- | ----------------------------- |
| `market`  | watchlist symbols, `quotes[symbol]`, `bars[symbol][tf]`                | `GET /quote/{s}`, `GET /bars/{s}?tf=`    | `quotes:{s}`, `bars:{s}:{tf}` |
| `session` | active session, portfolio, `orders[id]`, `fills[id]`                   | `GET /sessions/{id}/{portfolio,fills}`   | `session:{id}`                |
| `board`   | `cards[id]`, per-column id order, pending moves, snapshot for rollback | `GET /board`                             | `board`                       |
| `game`    | profile, season, leaderboard                                           | `GET /game/{profile,season,leaderboard}` | — (refetch after actions)     |
| `ui`      | active tab, selected symbol, timeframe, dialogs, toasts                | —                                        | —                             |

Rules:

- **REST hydrates, WS patches.** A panel mounts → fetch the snapshot → subscribe.
  A WS message with `t` older than the stored value for the same key is dropped.
- **One socket.** `src/api/ws.ts` owns the only `WebSocket`. Features call
  `ws.subscribe(topics)` and get an unsubscribe function; the client refcounts
  topics, sends one `{type:"subscribe", topics}` per change, reconnects with
  exponential backoff (500 ms → 10 s, ±20% jitter), resubscribes on open, parses
  once, and dispatches by `type` to a slice's `applyWs(msg)`. Topic strings come
  from `topics.*`, never string literals.
- **Cheap selectors.** Select `s.market.quotes[symbol]`, never a whole slice; lists select id arrays, rows by id.
- **Micro at the edge.** Store and compare `Micro`; call `fmtUsd`/`fmtQty` in JSX.
  Divide by `MICRO_PER_UNIT` only when a library demands floats (charts).
- **Errors are data.** `ApiError {status, code, message}` goes into `ui.toasts`;
  no `console.log` in app code (`no-console` lint allows `warn`/`error`).

## 8. Charts

`features/chart/Chart.tsx` wraps lightweight-charts 5:

- `createChart(el, { autoSize: true, layout: { background: {color: --bg-0}, textColor: --text-muted }, grid: {--border}, timeScale: { timeVisible: true, secondsVisible: false } })`.
  Read token values with `getComputedStyle(document.documentElement)` once.
- Candles: `chart.addSeries(CandlestickSeries, { upColor: --up, downColor: --down, borderVisible: false, wickUpColor, wickDownColor })`.
  Volume: `chart.addSeries(HistogramSeries, { priceScaleId: 'volume', priceFormat: {type:'volume'} })`
  with `chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })`.
- Data mapping in `features/chart/toCandle.ts`: `time = Math.floor(Date.parse(bar.t) / 1000)` as `UTCTimestamp`, prices `micro / MICRO_PER_UNIT`. Pure, unit-tested.
- Hydrate with `series.setData(bars.map(toCandle))`. Live: `series.update(candle)`;
  same `time` replaces the forming bar, newer appends. Never `setData` on every tick.
- Timeframe switch (`1m | 5m | 1d`): unsubscribe the old `bars:` topic, fetch
  `GET /bars/{symbol}?tf=`, `setData`, subscribe the new topic; keep the visible range.
- Fill markers: `createSeriesMarkers(series, fills.map(toMarker))`; buy `▲` below in `--up`, sell `▼` above in `--down`, text `qty @ price`.
- Crosshair: `chart.subscribeCrosshairMove` drives an OHLCV legend in the chart header (no floating tooltip); values via `fmtUsd`.
- Disposal: effect cleanup calls `chart.remove()`. Hold the chart in a `useRef`, never in state.

## 9. Code conventions

- TypeScript `strict` + `noUncheckedIndexedAccess` + `verbatimModuleSyntax`. No `any`,
  no non-null `!` outside tests, no type assertions except `as const` and brand casts
  inside `api/types.ts`. Narrow with type guards.
- Function components, named exports except `App`. Props are an `interface <Name>Props`
  declared above the component. No `React.FC`, no default props.
- Hooks: `eslint-plugin-react-hooks` recommended (includes React Compiler rules such
  as `set-state-in-effect`); fix the code, do not disable the rule. Effects do I/O
  and subscriptions only; derive everything else during render or in selectors.
- Files: `PascalCase.tsx` for components, `camelCase.ts` for modules, `*.test.ts(x)`
  beside the unit, one CSS file per feature named like the folder (`board.css`).
  Imports: external packages, blank line, internal; `import type` for types
  (lint-enforced). No barrel `index.ts` re-exports inside `features/`.
- CSS: plain CSS with tokens, no CSS modules, no CSS-in-JS, no Tailwind. Class names
  are `block__element--modifier`, prefixed by feature (`board-card__chip--up`). No
  hex colours outside `theme.css`.
- Accessibility baseline: every control operable by keyboard (ticket submits on Enter,
  board drags with Space/arrows), `role="tab"`/`aria-selected` for tab strips, `role="status"`
  for live pills, `:focus-visible` ring, colour never the sole signal, `aria-label` on icon buttons.

## 10. Testing

- **vitest** (`make test`): formatters, `toCandle`, selectors, slice reducers, `ws.ts`
  (fake `WebSocket` class), optimistic move + rollback. Pure functions get table tests.
- **Testing Library**: render against a stubbed `fetch` (`vi.stubGlobal('fetch', vi.fn(...))`,
  `vi.unstubAllGlobals()` in `afterEach`). Query by role and name, never by class.
- **Playwright smoke** (planned, Phase 3): three journeys against `make dev` with a
  running gateway: load the chart for `SPY`, place a paper market order and see the
  fill in Positions, drag a card from Backtest to Review. Screenshots on failure.
- Every slice reducer and formatter has a test; every bug fix adds the test that would have caught it.

## 11. Recipes

**Add a feature panel**

1. Create `src/features/<name>/<Name>Panel.tsx` and `<name>.css` (tokens only).
2. If it needs state, add `src/store/<slice>.ts` with selectors and `applyWs` if WS-fed.
3. Hydrate in a `useEffect` with an `AbortController`; `ws.subscribe` and return the unsubscribe.
4. Mount it in `App.tsx` in its column; add a tab if it lives in a tabbed panel.
5. Write `<Name>Panel.test.tsx` (render with stubbed fetch) and a reducer test.
6. `make check && make test && make build`; screenshot if visible.

**Add a WS topic to the store**

1. Add the builder to `topics` and the payload to `WsPayloads` in `src/api/types.ts`.
2. Add a case in the owning slice's `applyWs(msg)`; drop messages with stale `t`.
3. Subscribe from the feature with `ws.subscribe([topics.x(...)])` in an effect.
4. Test the reducer with a fixture `WsMessage` and an out-of-order one.
5. If the topic is not in ARCHITECTURE §4, propose the doc change in your report.

**Add a kanban column**

1. Extend `BoardColumn` and `BOARD_COLUMNS` in `src/api/types.ts` (order matters).
2. Add its label and any move rule in `src/features/board/columns.ts` / `rules.ts`.
3. The board renders from `BOARD_COLUMNS`; verify widths still fit at 1280px.
4. Update board tests and the wireframe above; agree the wire id with the gateway via the chief.

**Add a chart overlay**

1. Create `src/features/chart/overlays/<name>.ts` exporting pure `compute(bars): LineData[]`
   and `attach(chart, data)` returning a dispose function.
2. Register it in `overlays/index.ts`; add a toggle chip in the chart header.
3. Call dispose in the chart effect cleanup and on toggle-off.
4. Table-test `compute` with fixture bars, including a window shorter than the period.

## 12. Pitfalls

- **lightweight-charts needs a sized container.** The parent must have a definite
  height (`flex: 1; min-height: 0` in the column grid). Use `autoSize: true`; if you
  size manually, own a `ResizeObserver` and call `applyOptions({width, height})`.
- **StrictMode double-invokes effects** in dev. Per-component sockets would open
  twice; that is why `ws.ts` is a module singleton with refcounted topics and every
  fetch effect uses an `AbortController` and checks `signal.aborted` before `setState`.
- **dnd-kit and virtualization do not mix.** Sortable measures real DOM nodes; a
  virtualised column unmounts items mid-drag. Collapse `retired` past ~100 cards instead.
- **`Intl.NumberFormat` is locale-dependent** and may emit non-breaking spaces, so
  `fmtUsd`/`fmtQty` fix `en-US` and use integer math. Tabular numerals need a font
  with `tnum`; the system stack has it, custom fonts may not.
- **Micro is a JS number.** Safe to ±2^53 micro (≈ $9 billion). `micro()` throws
  beyond that; if the gateway ever sends larger values, move to `bigint` at the edge.
- **Proxy vs CORS.** The default `VITE_GATEWAY_URL` hits `localhost:8787` directly and
  needs CORS on the gateway; `""` goes same-origin through the Vite proxy (`/api`, `/ws`).
- **Only `VITE_`-prefixed vars reach the browser**, and all of them do. `envDir` is
  the repo root, where provider keys live; never prefix a secret with `VITE_`.
- **pnpm 12 minimum release age.** Fresh npm releases are rejected for a cooling
  period; pnpm may write a `pnpm-workspace.yaml` exclusion on its own. Do not commit
  that file. Widen the range so an older release resolves, or wait.

## 13. Definition of done (web change)

- [ ] `make check`, `make test`, `make build` pass in `web/` (CI runs the first two).
- [ ] Visual change: screenshot at 1440px in the report (`make dev` or `vite preview`).
- [ ] Types in `api/types.ts` match the gateway; any §4 gap is proposed, not patched around.
- [ ] No hex colours, font names, or brand assets outside `theme.css`; no `any`.
- [ ] Keyboard path verified for any new control; colour is not the only signal.
- [ ] This file updated if a command, convention, layout, or recipe changed.
- [ ] Commits atomic, Conventional (`feat(web): …`), attributed, rebased on `origin/main`.

## 14. Phase plan

- **Phase 1** — chart (`GET /bars`, `bars:` topic, timeframe switch, fill markers),
  watchlist with live quotes, order ticket against `POST /sessions/{id}/orders`,
  positions/orders/fills from the `session:` topic, `ws.ts`, `market`/`session`/`ui` slices.
- **Phase 2** — Strategy Board wired to `GET /board` and `PATCH /board/cards/{id}`,
  dnd-kit drag with confirmation and rollback, owner badges, Trader notes and pending
  proposals, strategy source viewer (`GET /strategies/{id}/versions`), run status.
- **Phase 3** — XP toasts, season banner, leaderboard panel, achievements; Playwright
  smoke suite in CI; tablet drawer for the watchlist.
