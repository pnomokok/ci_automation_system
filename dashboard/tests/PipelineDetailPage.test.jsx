import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/context/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { id: 'u1', username: 'testuser' },
    logout: vi.fn(),
  }),
}));

vi.mock('../src/services/api', () => ({
  getPipeline: vi.fn(),
  getPipelineReport: vi.fn(),
  getPipelineLogs: vi.fn(),
  stopPipeline: vi.fn(),
  triggerPipeline: vi.fn(),
  formatApiError: (err) => err?.message || 'Hata',
  formatDate: (d) => (d ? '2026-01-01' : '—'),
  formatDuration: (d) => (d != null ? `${d}s` : '—'),
}));

import { getPipeline, getPipelineReport, getPipelineLogs } from '../src/services/api';
import PipelineDetailPage from '../src/components/PipelineDetailPage';

const mockPipeline = {
  id: 'pipe-1',
  status: 'SUCCESS',
  branch: 'main',
  repo_url: 'https://github.com/org/repo',
  commit_hash: 'abc123def456789',
  commit_msg: 'Initial commit',
  commit_author: 'Alice',
  trigger_type: 'manual',
  started_at: '2026-01-01T10:00:00Z',
  finished_at: '2026-01-01T10:05:00Z',
  duration_sec: 300,
  steps: [
    { id: 'step-1', name: 'install', order: 1, status: 'SUCCESS', duration_sec: 60, exit_code: 0 },
    { id: 'step-2', name: 'build',   order: 2, status: 'SUCCESS', duration_sec: 120, exit_code: 0 },
    { id: 'step-3', name: 'test',    order: 3, status: 'SUCCESS', duration_sec: 120, exit_code: 0 },
  ],
};

function renderPage(repoId = 'repo-1', pipelineId = 'pipe-1') {
  return render(
    <MemoryRouter initialEntries={[`/repositories/${repoId}/pipelines/${pipelineId}`]}>
      <Routes>
        <Route
          path="/repositories/:repoId/pipelines/:id"
          element={<PipelineDetailPage />}
        />
      </Routes>
    </MemoryRouter>
  );
}

describe('PipelineDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getPipelineLogs.mockResolvedValue({ data: { items: [], total: 0 } });
  });

  it('shows loading spinner while fetching', () => {
    getPipeline.mockImplementation(() => new Promise(() => {}));
    renderPage();
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders pipeline metadata after loading', async () => {
    getPipeline.mockResolvedValue({ data: mockPipeline });
    getPipelineReport.mockResolvedValue({
      data: { total_tests: 5, passed: 5, failed: 0, skipped: 0, no_tests_found: false },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('https://github.com/org/repo')).toBeInTheDocument();
    });
    expect(screen.getByText('main')).toBeInTheDocument();
  });

  it('renders pipeline steps', async () => {
    getPipeline.mockResolvedValue({ data: mockPipeline });
    getPipelineReport.mockResolvedValue({
      data: { total_tests: 0, passed: 0, failed: 0, skipped: 0, no_tests_found: false },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Adımlar')).toBeInTheDocument();
    });
  });

  it('shows test report totals', async () => {
    getPipeline.mockResolvedValue({ data: mockPipeline });
    getPipelineReport.mockResolvedValue({
      data: { total_tests: 42, passed: 40, failed: 2, skipped: 0, no_tests_found: false },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument();
    });
  });

  it('shows error state when API fails', async () => {
    getPipeline.mockRejectedValue(new Error('Pipeline bulunamadı'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Pipeline bulunamadı')).toBeInTheDocument();
    });
  });

  it('shows retrigger button for finished pipeline', async () => {
    getPipeline.mockResolvedValue({ data: mockPipeline });
    getPipelineReport.mockResolvedValue({
      data: { total_tests: 0, passed: 0, failed: 0, skipped: 0, no_tests_found: false },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('↺ Yeniden Tetikle')).toBeInTheDocument();
    });
  });

  it('shows stop button for running pipeline', async () => {
    getPipeline.mockResolvedValue({ data: { ...mockPipeline, status: 'RUNNING' } });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('■ Durdur')).toBeInTheDocument();
    });
  });

  it('shows log viewer section', async () => {
    getPipeline.mockResolvedValue({ data: mockPipeline });
    getPipelineReport.mockResolvedValue({
      data: { total_tests: 0, passed: 0, failed: 0, skipped: 0, no_tests_found: false },
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Loglar')).toBeInTheDocument();
    });
  });
});
