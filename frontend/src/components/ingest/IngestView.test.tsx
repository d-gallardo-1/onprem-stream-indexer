import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../lib/api';
import { DIRECTORY, LAW, makeCrawl, makeRuling, makeSnapshot } from '../../test/fixtures';
import type { CrawlRun } from '../../types/lexstream';
import { IngestView } from './IngestView';

afterEach(cleanup);

function renderView(crawl: CrawlRun | null = null) {
  const snapshot = { ...makeSnapshot(LAW, crawl ? 12 : 10), crawl };
  if (crawl) {
    snapshot.recent = [makeRuling({ docket_id: 'SYN-LAW-CRAWL-0001', title: 'Crawled ruling',
      source: 'SIMULATED_CRAWL', outcome: 'COMPLIANCE_ORDER' })];
    snapshot.events = [{ at: '2026-01-05T09:00:00Z', kind: 'CRAWL_STARTED',
      message: 'RUN-LAW-0001 started on MERIDIAN_DOCKET_GAZETTE' }];
  }
  return render(<IngestView snapshot={snapshot} portals={DIRECTORY.source_portals} />);
}

const runButton = () => screen.getByRole('button', { name: /simulated crawl|Crawl running/ }) as HTMLButtonElement;

describe('IngestView', () => {
  it('shows the corpus counters and an empty state before any crawl', () => {
    renderView();

    expect(screen.getByText('£1,938,300')).toBeTruthy();
    expect(screen.getByText(/No crawl has run for this tenant yet/)).toBeTruthy();
    expect(screen.getByText(/None yet: the index holds the default corpus/)).toBeTruthy();
    expect(screen.getByText(/Nothing is fetched/)).toBeTruthy();
  });

  it('offers only the fixed portal names and starts a crawl for the tenant on screen', async () => {
    const start = vi.spyOn(api, 'startCrawl').mockResolvedValue({ run_id: 'RUN-LAW-0001' });
    renderView();
    const portal = screen.getByLabelText('Source portal') as HTMLSelectElement;

    expect(Array.from(portal.options).map((option) => option.value)).toEqual(DIRECTORY.source_portals);
    expect(document.querySelector('input[type="url"], input[type="text"]')).toBeNull();

    fireEvent.change(portal, { target: { value: 'HALDEN_TRIBUNAL_REGISTER' } });
    fireEvent.change(screen.getByLabelText('New rulings to index'), { target: { value: '2' } });
    fireEvent.click(runButton());

    await waitFor(() =>
      expect(start).toHaveBeenCalledWith('TNT-LAW-01', 'HALDEN_TRIBUNAL_REGISTER', 2));
  });

  it('renders the stages in order while the crawl runs and blocks a second start', () => {
    renderView(makeCrawl());

    const stages = screen.getByRole('region', { name: 'Crawl stages' });
    expect(stages.textContent).toContain('RUN-LAW-0001');
    expect(Array.from(stages.querySelectorAll('ol > li p:first-child')).map((p) => p.textContent)).toEqual([
      'Connecting to portal', 'Parsing dockets']);
    expect(screen.getByRole('status').textContent).toBe('Running');
    expect(runButton().disabled).toBe(true);
    expect(runButton().textContent).toContain('Crawl running');
  });

  it('shows a completed run with its indexed rulings and allows the next one', () => {
    renderView(makeCrawl({
      state: 'COMPLETED',
      finished_at: '2026-01-05T09:00:05Z',
      stages: [...makeCrawl().stages, { stage: 'INDEXED_NEW_RULING', at: '2026-01-05T09:00:04Z',
        detail: 'Crawled ruling', docket_id: 'SYN-LAW-CRAWL-0001' }],
    }));

    expect(screen.getByRole('status').textContent).toBe('Completed');
    expect(screen.getAllByText('SYN-LAW-CRAWL-0001')).toHaveLength(2); // stage and newest list
    expect(screen.getByText('Compliance order')).toBeTruthy();
    expect(screen.getByText('CRAWL_STARTED')).toBeTruthy();
    expect(runButton().disabled).toBe(false);
  });

  it('shows a failed run as failed and allows a new one', () => {
    renderView(makeCrawl({ state: 'FAILED', finished_at: '2026-01-05T09:00:03Z' }));

    expect(screen.getByRole('status').textContent).toBe('Failed');
    expect(runButton().disabled).toBe(false);
  });

  it('shows the refusal when the backend answers that a crawl is already running', async () => {
    vi.spyOn(api, 'startCrawl').mockRejectedValue(
      new Error('Crawl RUN-LAW-0001 is still running for this tenant.'));
    renderView();

    fireEvent.click(runButton());

    expect((await screen.findByRole('alert')).textContent).toContain('is still running');
  });

  it('resets the corpus', async () => {
    const reset = vi.spyOn(api, 'reset').mockResolvedValue({ status: 'reset' });
    renderView(makeCrawl());

    fireEvent.click(screen.getByRole('button', { name: 'Reset corpus' }));

    await waitFor(() => expect(reset).toHaveBeenCalledTimes(1));
  });
});
