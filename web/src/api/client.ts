/**
 * Typed REST client for the gateway (docs/ARCHITECTURE.md §4).
 *
 * Base URL: `VITE_GATEWAY_URL`, default `http://localhost:8787`. Set it to the
 * empty string to use same-origin paths and let the Vite dev proxy forward
 * `/api` and `/ws` (no CORS). The client never retries and never caches; the
 * store decides both.
 */

import type { ApiErrorBody, Health } from './types';

const DEFAULT_GATEWAY_URL = 'http://localhost:8787';

export const gatewayUrl: string = (import.meta.env.VITE_GATEWAY_URL ?? DEFAULT_GATEWAY_URL).replace(
  /\/+$/,
  '',
);

export const API_PREFIX = '/api/v1';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

export interface RequestOptions {
  signal?: AbortSignal;
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null) return false;
  const err = (value as { error?: unknown }).error;
  return typeof err === 'object' && err !== null && 'code' in err && 'message' in err;
}

async function request<T>(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  path: string,
  body?: unknown,
  opts: RequestOptions = {},
): Promise<T> {
  const init: RequestInit = {
    method,
    headers: { accept: 'application/json' },
    signal: opts.signal ?? null,
  };
  if (body !== undefined) {
    init.headers = { ...init.headers, 'content-type': 'application/json' };
    init.body = JSON.stringify(body);
  }
  const res = await fetch(`${gatewayUrl}${API_PREFIX}${path}`, init);
  if (!res.ok) {
    let parsed: unknown = null;
    try {
      parsed = await res.json();
    } catch {
      // non-JSON error body; fall through to the generic message
    }
    if (isApiErrorBody(parsed)) {
      throw new ApiError(res.status, parsed.error.code, parsed.error.message);
    }
    throw new ApiError(res.status, 'http_error', `${method} ${path} failed with ${res.status}`);
  }
  return (await res.json()) as T;
}

export const api = {
  /** `GET /health` → `{status, engine, provider}`. */
  health: (opts?: RequestOptions) => request<Health>('GET', '/health', undefined, opts),
};

export type Api = typeof api;
