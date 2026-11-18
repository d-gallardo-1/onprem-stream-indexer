import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { useTenantStream } from './hooks/useTenantStream';
import { api } from './lib/api';
import { FakeEventSource } from './test/fakeEventSource';
import { DIRECTORY, IND, makeEstimate, makeSearch, makeSnapshot } from './test/fixtures';
import type { StreamStatus, TenantSnapshot } from './types/lexstream';

vi.mock('./hooks/useTenantStream', async (original) => ({
  ...(await original<typeof import('./hooks/useTenantStream')>()),
  useTenantStream: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

beforeEach(() => {
  vi.stubGlobal('EventSource', FakeEventSource);
  vi.spyOn(api, 'directory').mockResolvedValue(DIRECTORY);
  vi.spyOn(api, 'searchSnapshot').mockResolvedValue(makeSearch());
  vi.spyOn(api, 'estimate').mockResolvedValue(makeEstimate());
});

/** The stream hook answers with the snapshot of whichever tenant it is asked for. */
function streamAnswers(status: StreamStatus, withSnapshot = true) {
  vi.mocked(useTenantStream).mockImplementation((tenantId) => {
    const entry = DIRECTORY.tenants.find((item) => item.tenant.tenant_id === tenantId);
    const snapshot: TenantSnapshot | null = entry && withSnapshot ? makeSnapshot(entry.tenant) : null;
    return { snapshot, status };
  });
}

const tenantSelect = () => screen.getByLabelText('Tenant') as HTMLSelectElement;
const searchBox = () => screen.findByRole('searchbox') as Promise<HTMLInputElement>;
const tab = (name: RegExp) => screen.getByRole('button', { name });

describe('App', () => {
  it('names the platform, selects the first tenant and subscribes to its stream', async () => {
    streamAnswers('CONNECTED');
    render(<App />);
    await searchBox();

    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('LexStream On-Prem');
    expect(screen.getByText('Multi-Tenant Regulatory & Case-Law Intelligence Engine')).toBeTruthy();
    expect(Array.from(tenantSelect().options).map((option) => option.text)).toEqual([
      'TNT-LAW-01 · Vanguard Corporate Litigation LLP',
      'TNT-IND-02 · NorthSea Infrastructure Compliance',
    ]);
    expect(vi.mocked(useTenantStream)).toHaveBeenLastCalledWith('TNT-LAW-01');
    expect(screen.getByText('Synthetic demo data')).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('has the three views of the specification', async () => {
    streamAnswers('CONNECTED');
    render(<App />);
    await searchBox();

    fireEvent.click(tab(/Ingestion Simulator/));
    expect(screen.getByRole('button', { name: 'Run simulated crawl' })).toBeTruthy();

    fireEvent.click(tab(/Tenant Partitioning & Export/));
    expect(screen.getByRole('link', { name: /Download .xlsx report/ })).toBeTruthy();

    fireEvent.click(tab(/Live Search & Outcome Analytics/));
    expect(await screen.findByRole('button', { name: /Stream Search via SSE/ })).toBeTruthy();
  });

  it('switches every view to the newly selected tenant and clears the filters', async () => {
    streamAnswers('CONNECTED');
    render(<App />);
    fireEvent.change(await searchBox(), { target: { value: 'costs' } });
    fireEvent.change(screen.getByLabelText('Authority'), {
      target: { value: 'Halden Labour Review Board' } });

    fireEvent.change(tenantSelect(), { target: { value: 'TNT-IND-02' } });

    expect(vi.mocked(useTenantStream)).toHaveBeenLastCalledWith('TNT-IND-02');
    expect(await screen.findByText(`Rulings of ${IND.name}`)).toBeTruthy();
    expect((await searchBox()).value).toBe('');
    expect((screen.getByLabelText('Authority') as HTMLSelectElement).value).toBe('');
    await waitFor(() => expect(vi.mocked(api.searchSnapshot).mock.lastCall?.slice(0, 2)).toEqual([
      'TNT-IND-02', { q: '', authority: '', outcome: '' }]));

    fireEvent.click(tab(/Tenant Partitioning & Export/));
    expect(screen.getByRole('link', { name: /Download .xlsx report/ }).getAttribute('href')).toBe(
      '/api/v1/export/analytics-xlsx?tenant_id=TNT-IND-02');
  });

  it('exports the query typed in the search view', async () => {
    streamAnswers('CONNECTED');
    render(<App />);
    fireEvent.change(await searchBox(), { target: { value: 'damages' } });

    fireEvent.click(tab(/Tenant Partitioning & Export/));

    expect(screen.getByRole('link', { name: /Download .xlsx report/ }).getAttribute('href')).toBe(
      '/api/v1/export/analytics-xlsx?tenant_id=TNT-LAW-01&q=damages');
  });

  it('warns during a reconnect but keeps controls usable', async () => {
    streamAnswers('RECONNECTING');
    render(<App />);

    expect((await searchBox()).matches(':disabled')).toBe(false);
    expect(screen.getByRole('alert').textContent).toContain('Reconnecting to the live stream');
  });

  it('warns and disables every control once the connection is given up on', async () => {
    streamAnswers('DISCONNECTED');
    render(<App />);

    expect((await searchBox()).matches(':disabled')).toBe(true);
    expect(screen.getByRole('alert').textContent).toContain('controls are disabled');
    // Navigation and the tenant selector live outside the disabled area.
    expect((tab(/Ingestion Simulator/) as HTMLButtonElement).matches(':disabled')).toBe(false);
    expect(tenantSelect().matches(':disabled')).toBe(false);
  });

  it('explains the situation when no snapshot has ever arrived', async () => {
    streamAnswers('DISCONNECTED', false);
    render(<App />);

    expect(await screen.findByText(/Cannot reach the backend/)).toBeTruthy();
    expect(screen.queryByRole('searchbox')).toBeNull();
  });

  it('reports a tenant list that cannot be loaded', async () => {
    vi.mocked(api.directory).mockRejectedValue(new Error('HTTP 502'));
    streamAnswers('RECONNECTING', false);
    render(<App />);

    expect((await screen.findByRole('alert')).textContent).toContain('Cannot load the tenant list: HTTP 502');
    expect(tenantSelect().disabled).toBe(true);
  });

  it('keeps the working screen when a later reload of the tenant list fails', async () => {
    let rulings = 10;
    vi.mocked(useTenantStream).mockImplementation((tenantId) => ({
      snapshot: tenantId ? makeSnapshot(DIRECTORY.tenants[0].tenant, rulings) : null,
      status: 'CONNECTED',
    }));
    const view = render(<App />);
    await searchBox();
    vi.mocked(api.directory).mockRejectedValue(new Error('HTTP 502'));

    rulings = 11; // a crawl indexed a ruling: the directory is reloaded and fails
    view.rerender(<App />);
    await waitFor(() => expect(api.directory).toHaveBeenCalledTimes(2));

    expect(await searchBox()).toBeTruthy();
    expect(tenantSelect().disabled).toBe(false);
    expect(tenantSelect().options).toHaveLength(2);
    expect(screen.queryByText(/Cannot load the tenant list/)).toBeNull();
  });

  it('keeps the results on screen when the stream drops and the backend is down', async () => {
    let status: StreamStatus = 'CONNECTED';
    vi.mocked(useTenantStream).mockImplementation((tenantId) => ({
      snapshot: tenantId ? makeSnapshot(DIRECTORY.tenants[0].tenant) : null,
      status,
    }));
    const view = render(<App />);
    expect(await screen.findByText('Corvane Freight v Lumestra Packaging')).toBeTruthy();
    expect((await screen.findByTestId('estimate')).textContent).toBe('47.5%');
    const calls = vi.mocked(api.searchSnapshot).mock.calls.length;
    for (const call of [api.searchSnapshot, api.estimate, api.directory]) {
      vi.mocked(call).mockRejectedValue(new Error('HTTP 502'));
    }

    status = 'DISCONNECTED';
    view.rerender(<App />);
    await new Promise((resolve) => setTimeout(resolve, 400)); // longer than the search debounce

    expect(screen.getByRole('alert').textContent).toContain('last snapshot received');
    expect(screen.getByText('Corvane Freight v Lumestra Packaging')).toBeTruthy();
    expect(screen.getByTestId('estimate').textContent).toBe('47.5%');
    expect(vi.mocked(api.searchSnapshot).mock.calls.length).toBe(calls);
  });

  it('states in the footer that the data is invented and the selector is not a login', () => {
    streamAnswers('CONNECTED');
    render(<App />);

    expect(screen.getByText(/The tenant selector is not a login, and nothing here is legal advice/)).toBeTruthy();
  });
});
