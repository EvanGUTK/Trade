import { useState } from 'react';

import './App.css';
import { StatusPill } from './components/StatusPill';

type Tab = 'chart' | 'board';

const TABS: ReadonlyArray<{ id: Tab; label: string }> = [
  { id: 'chart', label: 'Chart' },
  { id: 'board', label: 'Strategy Board' },
];

/**
 * Application shell: top bar, three columns (watchlist | centre | ticket and
 * positions), and a bottom tab strip that switches the centre panel. Panels
 * are empty placeholders until their feature lands (see web/CLAUDE.md §14).
 */
export default function App() {
  const [tab, setTab] = useState<Tab>('chart');

  return (
    <div className="shell">
      <header className="topbar">
        <h1 className="topbar__brand">Trade</h1>
        <span className="topbar__note muted">paper money · real market</span>
        <StatusPill />
      </header>

      <main className="columns">
        <aside className="col col--left" aria-label="Watchlist">
          <h2>Watchlist</h2>
          <p className="placeholder muted">No symbols yet.</p>
        </aside>

        <section className="col col--center">
          <div className="panel" role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
            {tab === 'chart' ? (
              <>
                <h2>Chart</h2>
                <p className="placeholder muted">Select a symbol to load bars.</p>
              </>
            ) : (
              <>
                <h2>Strategy Board</h2>
                <p className="placeholder muted">
                  Backlog · Research · Backtest · Paper Live · Review · Retired/Promoted
                </p>
              </>
            )}
          </div>
          <nav className="tabs" role="tablist" aria-label="Centre panel">
            {TABS.map((t) => (
              <button
                key={t.id}
                id={`tab-${t.id}`}
                role="tab"
                type="button"
                className="tabs__tab"
                aria-selected={tab === t.id}
                aria-controls={`panel-${t.id}`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </section>

        <aside className="col col--right" aria-label="Order ticket and positions">
          <section className="panel">
            <h2>Order Ticket</h2>
            <p className="placeholder muted">Buy / Sell · qty · price · TIF</p>
          </section>
          <section className="panel">
            <h2>Positions</h2>
            <p className="placeholder muted">No open positions.</p>
          </section>
        </aside>
      </main>
    </div>
  );
}
