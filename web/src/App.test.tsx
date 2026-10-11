import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import type { Health } from './api/types';

const healthOk: Health = { status: 'ok', engine: 'up', provider: 'yahoo' };

function stubFetch(body: unknown, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async () =>
        new Response(JSON.stringify(body), {
          status,
          headers: { 'content-type': 'application/json' },
        }),
    ),
  );
}

describe('App shell', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('mounts the three columns, the tab strip, and the gateway status pill', async () => {
    stubFetch(healthOk);
    render(<App />);

    expect(screen.getByRole('heading', { name: 'Watchlist' })).toBeDefined();
    expect(screen.getByRole('heading', { name: 'Chart' })).toBeDefined();
    expect(screen.getByRole('heading', { name: 'Order Ticket' })).toBeDefined();
    expect(screen.getByRole('heading', { name: 'Positions' })).toBeDefined();
    expect(screen.getByRole('tab', { name: 'Chart' })).toBeDefined();
    expect(screen.getByRole('tab', { name: 'Strategy Board' })).toBeDefined();

    const pill = await screen.findByText(/gateway up · engine up · yahoo/i);
    expect(pill.getAttribute('data-state')).toBe('up');
  });

  it('switches the centre panel from the bottom tab strip', () => {
    stubFetch(healthOk);
    render(<App />);

    fireEvent.click(screen.getByRole('tab', { name: 'Strategy Board' }));
    expect(screen.getByRole('heading', { name: 'Strategy Board' })).toBeDefined();
    expect(screen.queryByRole('heading', { name: 'Chart' })).toBeNull();
    expect(screen.getByRole('tab', { name: 'Strategy Board' }).getAttribute('aria-selected')).toBe(
      'true',
    );
  });

  it('reports the gateway as down when health fails', async () => {
    stubFetch({ error: { code: 'engine_down', message: 'engine exited' } }, 503);
    render(<App />);

    const pill = await screen.findByText(/gateway down/i);
    expect(pill.getAttribute('data-state')).toBe('down');
    expect(pill.getAttribute('title')).toBe('engine exited');
  });
});
