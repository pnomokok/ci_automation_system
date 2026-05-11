import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/services/api', () => ({
  getPipelineLogs: vi.fn(),
  formatApiError: (err) => err?.message || 'Hata',
}));

import { getPipelineLogs } from '../src/services/api';
import LogViewer from '../src/components/LogViewer';

describe('LogViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders step tabs on mount', () => {
    getPipelineLogs.mockImplementation(() => new Promise(() => {}));
    render(<LogViewer pipelineId="pipe-1" />);
    expect(screen.getByText('install')).toBeInTheDocument();
    expect(screen.getByText('build')).toBeInTheDocument();
    expect(screen.getByText('test')).toBeInTheDocument();
  });

  it('shows loading indicator while fetching', () => {
    getPipelineLogs.mockImplementation(() => new Promise(() => {}));
    render(<LogViewer pipelineId="pipe-1" />);
    expect(screen.getByText('Yükleniyor…')).toBeInTheDocument();
  });

  it('shows empty state when no logs exist', async () => {
    getPipelineLogs.mockResolvedValue({ data: { items: [], total: 0 } });
    render(<LogViewer pipelineId="pipe-1" />);
    await waitFor(() => {
      expect(screen.getByText(/"install" adımı için log yok\./)).toBeInTheDocument();
    });
  });

  it('renders log lines from API response', async () => {
    getPipelineLogs.mockResolvedValue({
      data: {
        items: [
          { step_id: 's1', line_number: 1, stream: 'stdout', content: 'Installing packages...' },
          { step_id: 's1', line_number: 2, stream: 'stderr', content: 'Warning: deprecated' },
        ],
        total: 2,
      },
    });
    render(<LogViewer pipelineId="pipe-1" />);
    await waitFor(() => {
      expect(screen.getByText('Installing packages...')).toBeInTheDocument();
      expect(screen.getByText('Warning: deprecated')).toBeInTheDocument();
    });
  });

  it('shows error message when API call fails', async () => {
    getPipelineLogs.mockRejectedValue(new Error('Bağlantı hatası'));
    render(<LogViewer pipelineId="pipe-1" />);
    await waitFor(() => {
      expect(screen.getByText('Bağlantı hatası')).toBeInTheDocument();
    });
  });

  it('does not call API when pipelineId is null', () => {
    render(<LogViewer pipelineId={null} />);
    expect(getPipelineLogs).not.toHaveBeenCalled();
  });

  it('shows copy and export buttons', () => {
    getPipelineLogs.mockImplementation(() => new Promise(() => {}));
    render(<LogViewer pipelineId="pipe-1" />);
    expect(screen.getByText('Kopyala')).toBeInTheDocument();
    expect(screen.getByText('↓ Dışa Aktar')).toBeInTheDocument();
  });

  it('shows stream filter dropdown', () => {
    getPipelineLogs.mockImplementation(() => new Promise(() => {}));
    render(<LogViewer pipelineId="pipe-1" />);
    expect(screen.getByText('stdout + stderr')).toBeInTheDocument();
  });
});
