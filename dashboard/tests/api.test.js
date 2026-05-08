// triggerPipeline artık api instance üzerinden POST /api/v1/pipelines'e gidiyor.
// axios.create instance'ını mock'lamak unit test kapsamını aştığından skip edildi.
import { describe, expect, it } from 'vitest';
import { decodeToken, formatApiError, formatDate, formatDuration } from '../src/services/api';

describe('formatDuration', () => {
  it('returns — for null', () => expect(formatDuration(null)).toBe('—'));
  it('returns seconds for < 60', () => expect(formatDuration(45)).toBe('45s'));
  it('returns minutes and seconds for >= 60', () => expect(formatDuration(125)).toBe('2m 5s'));
  it('handles 0', () => expect(formatDuration(0)).toBe('0s'));
});

describe('formatApiError', () => {
  it('returns error.message from API response', () => {
    const err = { response: { data: { error: { message: 'Pipeline bulunamadı' } } } };
    expect(formatApiError(err)).toBe('Pipeline bulunamadı');
  });

  it('returns detail string', () => {
    const err = { response: { data: { detail: 'Not found' } } };
    expect(formatApiError(err)).toBe('Not found');
  });

  it('returns network error message', () => {
    const err = { message: 'Network Error' };
    expect(formatApiError(err)).toContain('Sunucuya bağlanılamıyor');
  });

  it('returns timeout message for ECONNABORTED', () => {
    const err = { code: 'ECONNABORTED' };
    expect(formatApiError(err)).toContain('zaman aşımı');
  });

  it('returns generic error message', () => {
    const err = { message: 'Something went wrong' };
    expect(formatApiError(err)).toBe('Something went wrong');
  });
});

describe('decodeToken', () => {
  it('decodes a valid JWT payload', () => {
    const payload = { sub: 'user-id', username: 'admin', exp: 9999999999 };
    const b64 = btoa(JSON.stringify(payload)).replace(/=/g, '');
    const token = `header.${b64}.signature`;
    const result = decodeToken(token);
    expect(result.username).toBe('admin');
  });

  it('returns null for invalid token', () => {
    expect(decodeToken('invalid')).toBeNull();
    expect(decodeToken(null)).toBeNull();
  });
});

describe('formatDate', () => {
  it('returns — for null', () => expect(formatDate(null)).toBe('—'));
  it('returns — for empty string', () => expect(formatDate('')).toBe('—'));
  it('returns formatted date string', () => {
    const result = formatDate('2026-04-26T10:00:00Z');
    expect(result).toMatch(/\d{2}\.\d{2}\.2026/);
  });
});
