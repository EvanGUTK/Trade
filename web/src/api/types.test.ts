import { describe, expect, it } from 'vitest';

import { fmtQty, fmtUsd, micro, toMicro, topics } from './types';

describe('fmtUsd', () => {
  it('formats whole and fractional dollars with grouping', () => {
    expect(fmtUsd(micro(1_234_560_000))).toBe('$1,234.56');
    expect(fmtUsd(micro(100_000_000_000))).toBe('$100,000.00');
    expect(fmtUsd(micro(0))).toBe('$0.00');
  });

  it('keeps the sign in front of the currency symbol', () => {
    expect(fmtUsd(micro(-5_000_000))).toBe('-$5.00');
    expect(fmtUsd(micro(-10_000))).toBe('-$0.01');
  });

  it('rounds half up at the cent using integer math', () => {
    expect(fmtUsd(micro(1_234_565_000))).toBe('$1,234.57');
    expect(fmtUsd(micro(1_234_564_999))).toBe('$1,234.56');
    expect(fmtUsd(micro(4_999))).toBe('$0.00');
    expect(fmtUsd(micro(5_000))).toBe('$0.01');
  });
});

describe('micro', () => {
  it('rejects non-integers and unsafe magnitudes', () => {
    expect(() => micro(1.5)).toThrow(RangeError);
    expect(() => micro(Number.NaN)).toThrow(RangeError);
    expect(() => micro(2 ** 53)).toThrow(RangeError);
  });

  it('converts decimal units to micro, rounding half away from zero', () => {
    expect(toMicro(1.5)).toBe(1_500_000);
    expect(toMicro(-1.5)).toBe(-1_500_000);
    expect(toMicro(0.0000005)).toBe(1);
    expect(toMicro(-0.0000005)).toBe(-1);
  });
});

describe('fmtQty', () => {
  it('trims trailing zeros and groups thousands', () => {
    expect(fmtQty(micro(10_000_000))).toBe('10');
    expect(fmtQty(micro(1_500_000))).toBe('1.5');
    expect(fmtQty(micro(2_000_000_250_000))).toBe('2,000,000.25');
  });
});

describe('topics', () => {
  it('builds §4 topic names', () => {
    expect(topics.quotes('AAPL')).toBe('quotes:AAPL');
    expect(topics.bars('SPY', '5m')).toBe('bars:SPY:5m');
    expect(topics.session('s1')).toBe('session:s1');
    expect(topics.board).toBe('board');
    expect(topics.runs('r9')).toBe('runs:r9');
  });
});
