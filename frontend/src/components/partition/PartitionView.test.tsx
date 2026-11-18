import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { EMPTY_QUERY } from '../../lib/api';
import { DIRECTORY, IND, LAW } from '../../test/fixtures';
import { PARTITION_NOTICE, PartitionView } from './PartitionView';

afterEach(cleanup);

describe('PartitionView', () => {
  it('describes partitioning without claiming access control', () => {
    render(<PartitionView tenant={LAW} directory={DIRECTORY} query={EMPTY_QUERY} />);

    expect(screen.getByText(PARTITION_NOTICE)).toBeTruthy();
    expect(PARTITION_NOTICE).toContain('not access control');
    expect(document.body.textContent?.toLowerCase()).not.toContain('strict isolation');
    expect(document.body.textContent).toContain('verified identity');
  });

  it('draws the request path down to one partition per tenant', () => {
    render(<PartitionView tenant={IND} directory={DIRECTORY} query={EMPTY_QUERY} />);
    const path = screen.getByRole('group', { name: 'Request path' });

    expect(path.textContent).toContain('TenantStore.partition(tenant_id)');
    expect(path.textContent).toContain('an unknown tenant is a 404');
    const partitions = Array.from(path.querySelectorAll('ul > li'));
    expect(partitions.map((item) => item.querySelector('p')?.textContent)).toEqual([
      'TNT-LAW-01', 'TNT-IND-02']);
    expect(partitions.map((item) => item.getAttribute('aria-current'))).toEqual([null, 'true']);
    expect(partitions[1].textContent).toContain('Selected');
    expect(partitions[0].textContent).toContain('Not reachable from the selected tenant');
  });

  it('builds the report link from the tenant and the current query', () => {
    const query = { q: 'costs', authority: 'Halden Labour Review Board', outcome: 'UPHELD' };
    render(<PartitionView tenant={LAW} directory={DIRECTORY} query={query} />);
    const link = screen.getByRole('link', { name: /Download .xlsx report/ });

    expect(link.getAttribute('href')).toBe(
      '/api/v1/export/analytics-xlsx?tenant_id=TNT-LAW-01&q=costs&authority=Halden+Labour+Review+Board&outcome=UPHELD');
    expect(link.hasAttribute('download')).toBe(true);
    expect(screen.getByText('Text: costs')).toBeTruthy();
    expect(screen.getByText('Outcome: Upheld')).toBeTruthy();
  });

  it('says what an unfiltered report covers and that formulas are neutralised', () => {
    render(<PartitionView tenant={LAW} directory={DIRECTORY} query={EMPTY_QUERY} />);

    expect(screen.getByText('Text: all rulings')).toBeTruthy();
    expect(screen.getByText('Authority: any')).toBeTruthy();
    expect(screen.getByText(/written as plain text/)).toBeTruthy();
    expect(screen.getAllByRole('row')).toHaveLength(7); // header + six scoped routes
  });
});
