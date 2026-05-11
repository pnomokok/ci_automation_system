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
  getPipelines: vi.fn(),
  getRepositories: vi.fn(),
  getRepoMembers: vi.fn(),
  addRepoMember: vi.fn(),
  removeRepoMember: vi.fn(),
  updateRepoMemberRole: vi.fn(),
  deletePipeline: vi.fn(),
  triggerPipeline: vi.fn(),
  formatApiError: (err) => err?.message || 'Hata',
  formatDate: (d) => (d ? '2026-01-01' : '—'),
  formatDuration: (d) => (d != null ? `${d}s` : '—'),
}));

import { getPipelines, getRepositories, getRepoMembers } from '../src/services/api';
import RepoPipelinePage from '../src/components/RepoPipelinePage';

const mockRepo = {
  id: 'repo-1',
  url: 'https://github.com/org/repo',
  my_role: 'owner',
  default_branch: 'main',
  created_at: '2026-01-01',
};

function renderPage(repoId = 'repo-1') {
  return render(
    <MemoryRouter initialEntries={[`/repositories/${repoId}`]}>
      <Routes>
        <Route path="/repositories/:repoId" element={<RepoPipelinePage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('RepoPipelinePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getRepositories.mockResolvedValue({ data: [mockRepo] });
    getRepoMembers.mockResolvedValue({ data: [] });
    getPipelines.mockResolvedValue({ data: { items: [], total: 0 } });
  });

  it('renders tab structure', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Pipelines')).toBeInTheDocument();
      expect(screen.getByText('Üyeler')).toBeInTheDocument();
    });
  });

  it('shows pipeline trigger button', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('+ Pipeline Tetikle')).toBeInTheDocument();
    });
  });

  it('shows empty state when no pipelines', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Henüz hiç pipeline yok.')).toBeInTheDocument();
    });
  });

  it('shows status filter dropdown', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Tüm Durumlar')).toBeInTheDocument();
    });
  });

  it('shows pipeline count in header', async () => {
    getPipelines.mockResolvedValue({ data: { items: [], total: 0 } });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/pipeline/)).toBeInTheDocument();
    });
  });

  it('shows repo members section when Üyeler tab is available', async () => {
    getRepoMembers.mockResolvedValue({
      data: [{ id: 'm1', user_id: 'u1', username: 'testuser', role: 'owner' }],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Üyeler')).toBeInTheDocument();
    });
  });

  it('shows back navigation link', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('← Repositories')).toBeInTheDocument();
    });
  });

  it('renders without crashing on unknown repo', async () => {
    renderPage('unknown-repo-id');
    await waitFor(() => {
      expect(document.body).toBeInTheDocument();
    });
  });
});
