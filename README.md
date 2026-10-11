# Trade

Paper-money algorithmic-trading simulator with a WeBull-style UI, a kanban strategy
board, real market data, and a separate Claude agent (the Trader) that writes
strategies over MCP and remembers what it learned.

Start with [`CLAUDE.md`](CLAUDE.md), then [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
and [`docs/WORKFLOW.md`](docs/WORKFLOW.md).

```bash
cp .env.example .env
make setup
make check && make test
make dev
```
