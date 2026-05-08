import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/services/api', () => ({
  getTeams: vi.fn(),
  createTeam: vi.fn(),
  formatApiError: (err) => err?.message || 'Hata',
  formatDate: (d) => d || '—',
}));

vi.mock('../src/context/AuthContext', () => ({
  useAuth: () => ({
    user: { username: 'admin' },
    teams: [],
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

import { getTeams } from '../src/services/api';
import TeamsPage from '../src/components/TeamsPage';

const mockTeams = [
  { id: 'team-001', name: 'CI Ekibi',      created_at: '2026-01-01' },
  { id: 'team-002', name: 'Backend Ekibi', created_at: '2026-01-01' },
];

describe('TeamsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders_team_names', async () => {
    getTeams.mockResolvedValue({ data: mockTeams });
    render(<MemoryRouter><TeamsPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('CI Ekibi')).toBeInTheDocument();
      expect(screen.getByText('Backend Ekibi')).toBeInTheDocument();
    });
  });

  it('create_team_button_visible', async () => {
    getTeams.mockResolvedValue({ data: mockTeams });
    render(<MemoryRouter><TeamsPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText(/Yeni Takım/)).toBeInTheDocument();
    });
  });

  it('empty_state_when_no_teams', async () => {
    getTeams.mockResolvedValue({ data: [] });
    render(<MemoryRouter><TeamsPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText(/Henüz bir takıma dahil değilsin/)).toBeInTheDocument();
    });
  });
});
