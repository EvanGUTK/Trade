/**
 * Wire types for the gateway API (docs/ARCHITECTURE.md §4) and the payloads it
 * relays from the engine (§3) and its SQLite tables (§8).
 *
 * Money and quantities are integer micro-units (1 USD = 1_000_000 micro,
 * 1 share = 1_000_000 micro-shares). They stay in micro-units everywhere in the
 * store; only formatters at the render edge turn them into strings.
 *
 * Fields marked `contract` are spelled out in ARCHITECTURE.md. Fields marked
 * `assumed` follow its naming but are not yet pinned there; keep them in sync
 * with the gateway and propose the doc change through the chief.
 */

// ---------------------------------------------------------------------------
// Micro-units

declare const microBrand: unique symbol;

/** Integer micro-dollars or micro-shares. Construct with `micro()`. */
export type Micro = number & { readonly [microBrand]: 'Micro' };

export const MICRO_PER_UNIT = 1_000_000;

/** Brand an integer as Micro. Throws on non-integers or unsafe magnitudes. */
export function micro(n: number): Micro {
  if (!Number.isSafeInteger(n)) {
    throw new RangeError(`micro(): expected a safe integer, got ${String(n)}`);
  }
  return n as Micro;
}

/** Micro-units from a decimal amount, rounded half away from zero. */
export function toMicro(units: number): Micro {
  const scaled = units * MICRO_PER_UNIT;
  const rounded = scaled < 0 ? -Math.round(-scaled) : Math.round(scaled);
  return micro(rounded);
}

/**
 * Format micro-dollars as US currency with two decimals, e.g. `$1,234.56` or
 * `-$0.50`. Uses integer arithmetic so rounding never depends on float error.
 */
export function fmtUsd(m: Micro): string {
  const negative = m < 0;
  const abs = negative ? -m : m;
  const cents = Math.trunc((abs + 5_000) / 10_000); // round half up at the cent
  const dollars = Math.trunc(cents / 100);
  const rem = cents % 100;
  const body = `$${dollars.toLocaleString('en-US')}.${rem.toString().padStart(2, '0')}`;
  return negative ? `-${body}` : body;
}

/** Format micro-shares as a plain quantity, trimming trailing zeros. */
export function fmtQty(m: Micro): string {
  const whole = Math.trunc(m / MICRO_PER_UNIT);
  const frac = Math.abs(m % MICRO_PER_UNIT);
  if (frac === 0) return whole.toLocaleString('en-US');
  const fracStr = frac.toString().padStart(6, '0').replace(/0+$/, '');
  return `${whole.toLocaleString('en-US')}.${fracStr}`;
}

// ---------------------------------------------------------------------------
// Market data

/** `contract` §5 strategy timeframes and §4 `?tf=` values. */
export type Timeframe = '1m' | '5m' | '1d';

/** `contract` §3 bar shape; prices in micro-dollars, `t` RFC 3339 UTC. */
export interface Bar {
  t: string;
  o: Micro;
  h: Micro;
  l: Micro;
  c: Micro;
  v: number;
}

/** `assumed` shape of `GET /quote/{symbol}`; names follow §8. */
export interface Quote {
  symbol: string;
  t: string;
  last_micro: Micro;
  bid_micro: Micro | null;
  ask_micro: Micro | null;
}

// ---------------------------------------------------------------------------
// Sessions, orders, fills, portfolio

/** `contract` §4 `GET /health`. */
export interface Health {
  status: string;
  engine: 'up' | 'down';
  provider: string;
}

export type SessionMode = 'backtest' | 'paper';

/** `contract` §8 `sessions`. */
export interface Session {
  id: string;
  name: string;
  mode: SessionMode;
  start_cash_micro: Micro;
  start_time: string;
  seed: number;
  created_at: string;
  closed_at: string | null;
}

export type OrderSide = 'buy' | 'sell';
export type OrderType = 'market' | 'limit' | 'stop';
export type Tif = 'day' | 'gtc';

/**
 * `contract` §3 gives `accepted | rejected` at submit time; `filled` and
 * `cancelled` are `assumed` terminal states for the Orders tab.
 */
export type OrderStatus = 'accepted' | 'rejected' | 'filled' | 'cancelled';

/** `contract` §3 `order.submit` params; the body of `POST /sessions/{id}/orders`. */
export interface NewOrder {
  client_id: string;
  symbol: string;
  side: OrderSide;
  qty_micro: Micro;
  type: OrderType;
  limit_micro?: Micro;
  stop_micro?: Micro;
  tif: Tif;
}

/** `contract` §8 `orders`. */
export interface Order {
  id: string;
  session_id: string;
  client_id: string;
  symbol: string;
  side: OrderSide;
  qty_micro: Micro;
  type: OrderType;
  limit_micro: Micro | null;
  stop_micro: Micro | null;
  tif: Tif;
  status: OrderStatus;
  reason: string | null;
  created_at: string;
}

/** `contract` §8 `fills` and the §3 `fill` event. */
export interface Fill {
  id: string;
  session_id: string;
  order_id: string;
  symbol: string;
  side: OrderSide;
  qty_micro: Micro;
  price_micro: Micro;
  commission_micro: Micro;
  t: string;
}

/** `contract` §3 `Portfolio.positions[]`. */
export interface Position {
  symbol: string;
  qty_micro: Micro;
  avg_cost_micro: Micro;
  mark_micro: Micro;
  unrealized_micro: Micro;
}

/** `contract` §3 `Portfolio`; the body of `GET /sessions/{id}/portfolio`. */
export interface Portfolio {
  cash_micro: Micro;
  equity_micro: Micro;
  positions: Position[];
  realized_micro: Micro;
}

/** `contract` §3 `mark` event. */
export interface Mark {
  session_id: string;
  t: string;
  equity_micro: Micro;
  cash_micro: Micro;
  positions: Position[];
}

/** `contract` §3 `Metrics`. Ratios are plain numbers, not micro. */
export interface Metrics {
  total_return: number;
  max_drawdown: number;
  sharpe: number;
  sortino: number;
  win_rate: number;
  trades: number;
  exposure: number;
}

// ---------------------------------------------------------------------------
// Strategy Board

/** `contract` root CLAUDE.md §9 columns; `assumed` snake_case wire ids. */
export type BoardColumn =
  'backlog' | 'research' | 'backtest' | 'paper_live' | 'review' | 'retired' | 'promoted';

export const BOARD_COLUMNS: readonly BoardColumn[] = [
  'backlog',
  'research',
  'backtest',
  'paper_live',
  'review',
  'retired',
  'promoted',
];

/** `contract` §8 `strategies.owner`. */
export type Owner = 'human' | 'trader';

/** `contract` §8 `cards` joined with its strategy; `metrics` from the last run. */
export interface Card {
  id: string;
  strategy_id: string;
  name: string;
  owner: Owner;
  version: string;
  column: BoardColumn;
  position: number;
  notes: string;
  metrics: Metrics | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// WebSocket

/** `contract` §4 topic grammar. Build names with `topics`, never by hand. */
export const topics = {
  quotes: (symbol: string) => `quotes:${symbol}` as const,
  bars: (symbol: string, tf: Timeframe) => `bars:${symbol}:${tf}` as const,
  session: (id: string) => `session:${id}` as const,
  board: 'board' as const,
  runs: (id: string) => `runs:${id}` as const,
};

/** `contract` §4 client → server. */
export interface WsSubscribe {
  type: 'subscribe';
  topics: string[];
}

/** `assumed` event kinds carried in the §4 `{type, topic, t, payload}` envelope. */
export interface WsPayloads {
  quote: Quote;
  bar: Bar & { symbol: string; tf: Timeframe };
  fill: Fill;
  mark: Mark;
  order: Order;
  card: Card;
  run: { id: string; status: string; metrics: Metrics | null };
}

export type WsEventType = keyof WsPayloads;

/** `contract` §4 server → client envelope, discriminated on `type`. */
export type WsMessage = {
  [K in WsEventType]: { type: K; topic: string; t: string; payload: WsPayloads[K] };
}[WsEventType];

// ---------------------------------------------------------------------------
// Errors

/** `contract` §4 error body. */
export interface ApiErrorBody {
  error: { code: string; message: string };
}
