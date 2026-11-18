import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, EMPTY_QUERY, tenantParams } from './api';
import { codeLabel, formatTime, gbp, percentText } from './format';
import { splitHighlight } from './highlight';

function stubFetch(body: unknown, ok = true, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({ ok, status, json: async () => body });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe('tenantParams', () => {
  it('always sends the tenant and omits empty filters', () => {
    expect(tenantParams('TNT-LAW-01')).toBe('?tenant_id=TNT-LAW-01');
    expect(tenantParams('TNT-LAW-01', { q: '  costs ', authority: '', outcome: 'UPHELD' })).toBe(
      '?tenant_id=TNT-LAW-01&q=costs&outcome=UPHELD',
    );
  });

  it('encodes values so they cannot add or change a parameter', () => {
    expect(tenantParams('TNT-LAW-01', { q: 'a&tenant_id=TNT-IND-02' })).toBe(
      '?tenant_id=TNT-LAW-01&q=a%26tenant_id%3DTNT-IND-02',
    );
  });
});

describe('api', () => {
  it('names the tenant in every tenant request and URL', async () => {
    const fetchMock = stubFetch({});
    const query = { ...EMPTY_QUERY, q: 'crane' };

    await api.searchSnapshot('TNT-IND-02', query);
    await api.estimate('TNT-IND-02', { authority: '', matter: 'MACHINERY', outcome: 'DISMISSED' });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      '/api/v1/search/snapshot?tenant_id=TNT-IND-02&q=crane',
      '/api/v1/analytics/estimate?tenant_id=TNT-IND-02&matter=MACHINERY&outcome=DISMISSED',
    ]);
    expect(api.searchStreamUrl('TNT-IND-02', query)).toBe(
      '/api/v1/search/stream?tenant_id=TNT-IND-02&q=crane',
    );
    expect(api.stateStreamUrl('TNT-LAW-01')).toBe('/api/v1/ingest/stream?tenant_id=TNT-LAW-01');
    expect(api.exportUrl('TNT-LAW-01', { q: '', authority: 'Halden Labour Review Board', outcome: '' })).toBe(
      '/api/v1/export/analytics-xlsx?tenant_id=TNT-LAW-01&authority=Halden+Labour+Review+Board',
    );
  });

  it('starts a crawl with a portal name from the fixed list, never a URL field', async () => {
    const fetchMock = stubFetch({ run_id: 'RUN-LAW-0001' });

    await api.startCrawl('TNT-LAW-01', 'MERIDIAN_DOCKET_GAZETTE', 2);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/v1/ingest/simulate-crawl');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({
      tenant_id: 'TNT-LAW-01',
      source_portal: 'MERIDIAN_DOCKET_GAZETTE',
      rulings: 2,
    });
  });

  it("surfaces the server's own explanation of a refusal", async () => {
    stubFetch({ detail: 'Crawl RUN-LAW-0001 is still running for this tenant.' }, false, 409);

    await expect(api.startCrawl('TNT-LAW-01', 'X', 1)).rejects.toThrow('is still running');
  });

  it('falls back to the method, path and status when the error has no detail', async () => {
    stubFetch({ detail: [{ msg: 'structured' }] }, false, 500);

    await expect(api.reset()).rejects.toThrow('POST /ingest/reset failed with HTTP 500');
  });
});

describe('formatting helpers', () => {
  it('shows pounds exactly, with pence only when they are not zero', () => {
    expect(gbp(1938300)).toBe('£1,938,300');
    expect(gbp('111750.00')).toBe('£111,750');
    expect(gbp('253750.50')).toBe('£253,750.50');
    expect(gbp('not a number')).toBe('£–');
  });

  it('formats codes, percentages and times', () => {
    expect(codeLabel('MERIDIAN_DOCKET_GAZETTE')).toBe('Meridian docket gazette');
    expect(percentText(47.5)).toBe('47.5%');
    expect(percentText(40)).toBe('40.0%');
    expect(formatTime(null)).toBe('--:--:--');
  });
});

describe('splitHighlight', () => {
  it('marks whole words that the index matched, whatever their case', () => {
    expect(splitHighlight('Liquidated damages clause.', ['liquidated', 'clause'])).toEqual([
      { text: 'Liquidated', hit: true },
      { text: ' damages ', hit: false },
      { text: 'clause', hit: true },
      { text: '.', hit: false },
    ]);
  });

  it('does not mark a word that merely contains a term, and handles no terms', () => {
    expect(splitHighlight('belated', ['late'])).toEqual([{ text: 'belated', hit: false }]);
    expect(splitHighlight('Plain text', [])).toEqual([{ text: 'Plain text', hit: false }]);
    expect(splitHighlight('', [])).toEqual([]);
  });
});
