# ADR 0003 — Paper money only, forever

Status: Accepted (2026-10-10)

## Context
Real market data makes the simulator feel real. The temptation to "just add" a live
brokerage adapter will come up.

## Decision
No component may submit orders to a real brokerage. Provider adapters implement a
read-only `MarketData` trait/protocol with no order methods. There is no
`live_trading` configuration key; adding one is a rejected change regardless of
default value. Session creation validates `mode ∈ {backtest, paper}`.

## Consequences
- Brokerage SDKs are never dependencies.
- The Trader's system prompt states it trades paper money; its tools cannot do
  otherwise.
- The product can be shared freely without financial or regulatory risk.
