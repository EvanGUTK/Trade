import { useEffect, useState } from 'react';

import { api } from '../api/client';
import type { Health } from '../api/types';

type HealthState =
  { kind: 'checking' } | { kind: 'up'; health: Health } | { kind: 'down'; message: string };

function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

/**
 * Gateway health indicator for the top bar. Calls `GET /api/v1/health` once on
 * mount; the text always carries the state so colour is never the only signal.
 */
export function StatusPill() {
  const [state, setState] = useState<HealthState>({ kind: 'checking' });

  useEffect(() => {
    const ctl = new AbortController();
    api
      .health({ signal: ctl.signal })
      .then((health) => {
        if (!ctl.signal.aborted) setState({ kind: 'up', health });
      })
      .catch((e: unknown) => {
        if (!ctl.signal.aborted) setState({ kind: 'down', message: errorMessage(e) });
      });
    return () => ctl.abort();
  }, []);

  let label: string;
  switch (state.kind) {
    case 'checking':
      label = 'Gateway: checking…';
      break;
    case 'up':
      label = `Gateway up · engine ${state.health.engine} · ${state.health.provider}`;
      break;
    case 'down':
      label = 'Gateway down';
      break;
  }

  return (
    <span
      className="status-pill"
      data-state={state.kind}
      role="status"
      title={state.kind === 'down' ? state.message : undefined}
    >
      <span className="status-pill__dot" aria-hidden="true" />
      {label}
    </span>
  );
}
