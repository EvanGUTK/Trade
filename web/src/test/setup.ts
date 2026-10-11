import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// vitest runs with `globals: false`, so Testing Library cannot auto-register
// its cleanup. Unmount every tree after each test to keep tests independent.
afterEach(() => {
  cleanup();
});
