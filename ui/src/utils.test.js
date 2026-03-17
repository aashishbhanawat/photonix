import { formatBytes } from './utils';

describe('formatBytes', () => {
  test('returns "0 Bytes" for 0 bytes', () => {
    expect(formatBytes(0)).toBe('0 Bytes');
  });

  test('formats bytes correctly', () => {
    expect(formatBytes(1)).toBe('1 Bytes');
    expect(formatBytes(1023)).toBe('1023 Bytes');
  });

  test('formats KB correctly', () => {
    expect(formatBytes(1024)).toBe('1 KB');
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(1024 * 1024 - 1)).toBe('1024 KB');
  });

  test('formats MB correctly', () => {
    expect(formatBytes(1024 * 1024)).toBe('1 MB');
    expect(formatBytes(1024 * 1024 * 1.25)).toBe('1.25 MB');
  });

  test('formats GB correctly', () => {
    expect(formatBytes(Math.pow(1024, 3))).toBe('1 GB');
  });

  test('respects decimals parameter', () => {
    const bytes = 1234; // 1.205078125 KB
    expect(formatBytes(bytes, 0)).toBe('1 KB');
    expect(formatBytes(bytes, 1)).toBe('1.2 KB');
    expect(formatBytes(bytes, 2)).toBe('1.21 KB');
    expect(formatBytes(bytes, 3)).toBe('1.205 KB');
  });

  test('handles negative decimals by defaulting to 0', () => {
    const bytes = 1234;
    expect(formatBytes(bytes, -1)).toBe('1 KB');
  });

  test('handles very large units', () => {
    expect(formatBytes(Math.pow(1024, 8))).toBe('1 YB');
  });
});
