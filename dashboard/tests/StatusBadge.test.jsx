import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import StatusBadge from '../src/components/StatusBadge';

describe('StatusBadge', () => {
  const statuses = ['QUEUED', 'RUNNING', 'SUCCESS', 'FAILED', 'STOPPED'];

  it.each(statuses)('renders %s status correctly', (status) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(status)).toBeInTheDocument();
  });

  it('applies RUNNING animation class', () => {
    const { container } = render(<StatusBadge status="RUNNING" />);
    expect(container.firstChild.className).toMatch(/animate-pulse/);
  });

  it('renders unknown status without crashing', () => {
    render(<StatusBadge status="UNKNOWN_STATUS" />);
    expect(screen.getByText('UNKNOWN_STATUS')).toBeInTheDocument();
  });

  it('renders PENDING step status', () => {
    render(<StatusBadge status="PENDING" />);
    expect(screen.getByText('PENDING')).toBeInTheDocument();
  });

  it('renders small size variant', () => {
    const { container } = render(<StatusBadge status="SUCCESS" size="sm" />);
    expect(container.firstChild.className).toMatch(/px-1\.5/);
  });
});
