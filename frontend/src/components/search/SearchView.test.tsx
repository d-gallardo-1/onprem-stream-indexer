import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, EMPTY_QUERY } from '../../lib/api';
import { FakeEventSource } from '../../test/fakeEventSource';
import { DIRECTORY, IND, LAW, makeEstimate, makeHit, makeSearch, makeSnapshot,
  makeSummary } from '../../test/fixtures';
import type { SearchQuery, Tenant } from '../../types/lexstream';
import { SearchView } from './SearchView';

let search: ReturnType<typeof vi.spyOn>;
let estimate: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  FakeEventSource.reset();
  vi.stubGlobal('EventSource', FakeEventSource);
  search = vi.spyOn(api, 'searchSnapshot').mockResolvedValue(makeSearch());
  estimate = vi.spyOn(api, 'estimate').mockResolvedValue(makeEstimate());
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function Harness({ tenant = LAW, rulings = 10, connected = true }: {
  tenant?: Tenant; rulings?: number; connected?: boolean;
}) {
  const [query, setQuery] = useState<SearchQuery>(EMPTY_QUERY);
  return (
    <SearchView snapshot={makeSnapshot(tenant, rulings)} outcomes={DIRECTORY.outcomes}
      matters={DIRECTORY.matters} query={query} onQueryChange={setQuery} connected={connected} />
  );
}

const lastSearch = () => search.mock.calls[search.mock.calls.length - 1];
const streamButton = () => screen.getByRole('button', { name: /Stream Search via SSE|Streaming/ });
const emit = (type: string, data: unknown) => act(() => FakeEventSource.latest.emit(type, data));
const streamed = (position: number, total = 2) => ({
  position, total, elapsed_ms: 120 * position,
  hit: makeHit({ docket_id: `SYN-LAW-2025-000${position}`, title: `Streamed ruling ${position}` }),
});

describe('SearchView', () => {
  it('lists the tenant\'s rulings with analytics and marks the matched words', async () => {
    render(<Harness />);

    expect(await screen.findByText('Corvane Freight v Lumestra Packaging')).toBeTruthy();
    expect(lastSearch()[0]).toBe('TNT-LAW-01');
    expect(Array.from(document.querySelectorAll('mark')).map((node) => node.textContent)).toEqual([
      'liquidated', 'damages']);
    expect(screen.getAllByText('£412,000')).toHaveLength(2); // the ruling and the highest exposure
    expect(screen.getByRole('region', { name: 'Outcome analytics' }).textContent).toContain(
      '£253,750.50');
    expect(screen.getByText(/2024: 100.0% of 1\s+→\s+2025: 0.0% of 1/)).toBeTruthy();
  });

  it('offers only the authorities and matters of the selected tenant', async () => {
    render(<Harness tenant={IND} />);
    await screen.findByText('Corvane Freight v Lumestra Packaging');

    const options = (label: string) =>
      Array.from((screen.getByLabelText(label) as HTMLSelectElement).options).map((o) => o.text);
    expect(options('Authority')).toEqual(['Any authority', 'Kestrel Industrial Safety Inspectorate']);
    expect(options('Estimate matter')).toEqual(['Any matter', 'Industrial safety', 'Machinery']);
  });

  it('searches again, debounced, when the text or a filter changes', async () => {
    render(<Harness />);
    await screen.findByText('Corvane Freight v Lumestra Packaging');
    search.mockClear();

    for (const value of ['c', 'co', 'costs']) {
      fireEvent.change(screen.getByRole('searchbox'), { target: { value } });
    }
    fireEvent.change(screen.getByLabelText('Outcome'), { target: { value: 'DISMISSED' } });

    await waitFor(() => expect(search).toHaveBeenCalledTimes(1));
    expect(lastSearch()[1]).toEqual({ q: 'costs', authority: '', outcome: 'DISMISSED' });
  });

  it('searches again when a crawl adds rulings to the partition', async () => {
    const { rerender } = render(<Harness rulings={10} />);
    await screen.findByText('Corvane Freight v Lumestra Packaging');
    const calls = search.mock.calls.length;

    rerender(<Harness rulings={13} />);

    await waitFor(() => expect(search.mock.calls.length).toBe(calls + 1));
  });

  it('runs the search and the estimate again when the stream is back', async () => {
    search.mockRejectedValue(new Error('HTTP 502'));
    estimate.mockRejectedValue(new Error('HTTP 502'));
    const { rerender } = render(<Harness connected={false} />);
    await waitFor(() => expect(screen.getAllByRole('alert')).toHaveLength(2)); // search and estimate
    search.mockResolvedValue(makeSearch());
    estimate.mockResolvedValue(makeEstimate());

    rerender(<Harness connected />);

    expect(await screen.findByText('Corvane Freight v Lumestra Packaging')).toBeTruthy();
    expect((await screen.findByTestId('estimate')).textContent).toBe('47.5%');
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('streams rulings progressively with their arrival time, then the analytics', async () => {
    render(<Harness />);
    await screen.findByText('Corvane Freight v Lumestra Packaging');
    fireEvent.change(screen.getByLabelText('Outcome'), { target: { value: 'UPHELD' } });

    fireEvent.click(streamButton());

    expect(FakeEventSource.latest.url).toBe(
      '/api/v1/search/stream?tenant_id=TNT-LAW-01&outcome=UPHELD');
    expect(streamButton().textContent).toContain('Streaming');
    expect(screen.getByText('Waiting for the first ruling…')).toBeTruthy();
    expect(screen.getByText('Analytics arrive with the final event of the stream.')).toBeTruthy();

    emit('result', streamed(1));
    expect(screen.getByText('Streamed ruling 1')).toBeTruthy();
    expect(screen.queryByText('Streamed ruling 2')).toBeNull();
    expect(screen.getByText('Streaming: 1 of 2 received')).toBeTruthy();
    expect(screen.getAllByText(/^\+\d+ ms$/)).toHaveLength(1);

    emit('result', streamed(2));
    emit('analytics_summary', makeSummary(2));

    expect(screen.getByText(/Stream complete: 2 of 2 ruling\(s\) in \d+ ms/)).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Outcome analytics' })).toBeTruthy();
    expect(FakeEventSource.latest.readyState).toBe(FakeEventSource.CLOSED);
    expect(streamButton().textContent).toContain('Stream Search via SSE');
  });

  it('drops a streamed list when the filters change', async () => {
    render(<Harness />);
    await screen.findByText('Corvane Freight v Lumestra Packaging');
    fireEvent.click(streamButton());
    emit('result', streamed(1));
    const source = FakeEventSource.latest;

    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'costs' } });

    expect(source.readyState).toBe(FakeEventSource.CLOSED);
    expect(screen.queryByText('Streamed ruling 1')).toBeNull();
    expect(await screen.findByText('Corvane Freight v Lumestra Packaging')).toBeTruthy();
  });

  it('reports an interrupted stream', async () => {
    render(<Harness />);
    await screen.findByText('Corvane Freight v Lumestra Packaging');
    fireEvent.click(streamButton());

    act(() => FakeEventSource.latest.fail(false));

    expect(screen.getByRole('alert').textContent).toContain('closed before its summary arrived');
  });

  it('shows the estimate with its sample size, steps and the not-legal-advice label', async () => {
    render(<Harness />);

    expect((await screen.findByTestId('estimate')).textContent).toBe('47.5%');
    const panel = screen.getByRole('region', { name: 'Illustrative outcome estimator' });
    expect(panel.textContent).toContain('it is not legal advice');
    expect(panel.textContent).toContain('Sample: 4 matching ruling(s). Confidence: Moderate');
    expect(screen.getByText('2 of 4 ruling(s) ended this way')).toBeTruthy();
    expect(estimate.mock.calls[0]).toEqual(expect.arrayContaining(['TNT-LAW-01',
      { authority: '', matter: '', outcome: 'UPHELD' }]));

    estimate.mockResolvedValue(makeEstimate(63.4));
    fireEvent.change(screen.getByLabelText('Estimate matter'), { target: { value: 'LABOUR' } });
    fireEvent.change(screen.getByLabelText('Estimate outcome'), { target: { value: 'DISMISSED' } });

    await waitFor(() => expect(screen.getByTestId('estimate').textContent).toBe('63.4%'));
    expect(estimate.mock.calls[estimate.mock.calls.length - 1][1]).toEqual({
      authority: '', matter: 'LABOUR', outcome: 'DISMISSED' });
  });

  it('explains an empty result and shows a failed search', async () => {
    search.mockResolvedValue(makeSearch({ total: 0, results: [] }));
    render(<Harness />);
    expect(await screen.findByText(/No ruling of this tenant matches/)).toBeTruthy();

    search.mockRejectedValue(new Error('backend unavailable'));
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'x' } });

    expect((await screen.findByRole('alert')).textContent).toBe('backend unavailable');
    expect(screen.getByText('Search failed')).toBeTruthy();
  });
});
