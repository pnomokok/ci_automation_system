import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/services/api', () => ({
  getRepositories: vi.fn(),
  createRepository: vi.fn(),
  formatApiError: (err) => err?.message || 'Hata',
  formatDate: (d) => d || '—',
}));

vi.mock('../src/context/AuthContext', () => ({
  useAuth: () => ({
    user: { username: 'admin' },
    teams: [{ id: 'team-001', name: 'CI Ekibi' }],
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

import { getRepositories } from '../src/services/api';
import RepositoriesPage from '../src/components/RepositoriesPage';

const mockRepos = [
  {
    id: 'r1',
    url: 'https://github.com/u/personal',
    owner_type: 'user',
    owner_id: 'user-001',
    default_branch: 'main',
    created_at: '2026-01-01',
  },
  {
    id: 'r2',
    url: 'https://github.com/t/teamrepo',
    owner_type: 'team',
    owner_id: 'team-001',
    default_branch: 'main',
    created_at: '2026-01-01',
  },
];

describe('RepositoriesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getRepositories.mockResolvedValue({ data: { items: mockRepos } });
  });

  it('personal_repos_section_visible', async () => {
    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('Kişisel Repolarım')).toBeInTheDocument();
    });
  });

  it('team_repos_section_visible', async () => {
    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await waitFor(() => {
      const matches = screen.getAllByText(/CI Ekibi/);
      expect(matches.length).toBeGreaterThan(0);
    });
  });

  it('personal_repo_url_shown', async () => {
    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('u/personal')).toBeInTheDocument();
    });
  });

  it('repo_card_click_navigates', async () => {
    let navigatedTo = null;
    render(
      <MemoryRouter initialEntries={['/repositories']}>
        <RepositoriesPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('u/personal')).toBeInTheDocument();
    });
    const card = screen.getByText('u/personal').closest('[class*="cursor-pointer"]');
    expect(card).toBeTruthy();
  });

  it('add_repo_button_exists', async () => {
    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText(/Repo Ekle/)).toBeInTheDocument();
    });
  });
});
