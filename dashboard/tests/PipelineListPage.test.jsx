import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/services/api', () => ({
  getPipelines: vi.fn(),
  formatApiError: (err) => err?.message || 'Hata',
  formatDate: (d) => d || '—',
  formatDuration: (s) => (s != null ? `${s}s` : '—'),
}));

import { getPipelines } from '../src/services/api';
import PipelineListPage from '../src/components/PipelineListPage';

const mockPipelines = [
  {
    id: 'abc-1',
    repo_url: 'https://github.com/test/repo',
    branch: 'main',
    commit_hash: 'a1b2c3d4',
    trigger_type: 'webhook',
    status: 'SUCCESS',
    started_at: '2026-04-26T10:00:00Z',
    duration_sec: 120,
  },
  {
    id: 'abc-2',
    repo_url: 'https://github.com/test/repo',
    branch: 'develop',
    commit_hash: 'e5f6g7h8',
    trigger_type: 'manual',
    status: 'RUNNING',
    started_at: '2026-04-26T11:00:00Z',
    duration_sec: null,
  },
];

describe('PipelineListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders pipeline table after loading', async () => {
    getPipelines.mockResolvedValue({
      data: { items: mockPipelines, total: 2, page: 1, page_size: 20 },
    });
    render(<MemoryRouter><PipelineListPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('SUCCESS')).toBeInTheDocument();
      expect(screen.getByText('RUNNING')).toBeInTheDocument();
    });
  });

  it('shows empty state when no pipelines', async () => {
    getPipelines.mockResolvedValue({
      data: { items: [], total: 0, page: 1, page_size: 20 },
    });
    render(<MemoryRouter><PipelineListPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText(/Henüz hiç pipeline yok/)).toBeInTheDocument();
    });
  });

  it('shows error message on API failure', async () => {
    getPipelines.mockRejectedValue({ message: 'Bağlantı hatası' });
    render(<MemoryRouter><PipelineListPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('Bağlantı hatası')).toBeInTheDocument();
    });
  });

  it('shows total pipeline count', async () => {
    getPipelines.mockResolvedValue({
      data: { items: mockPipelines, total: 42, page: 1, page_size: 20 },
    });
    render(<MemoryRouter><PipelineListPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText(/42 pipeline/)).toBeInTheDocument();
    });
  });
});
