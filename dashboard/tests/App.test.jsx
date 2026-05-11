import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../src/services/api', () => ({
  loginUser: vi.fn(),
  decodeToken: vi.fn(() => null),
  registerUser: vi.fn(),
  getRepositories: vi.fn().mockResolvedValue({ data: [] }),
  getPipelines: vi.fn().mockResolvedValue({ data: { items: [], total: 0 } }),
  formatApiError: (err) => err?.message || 'Hata',
}));

import App from '../src/App';
import { AuthProvider } from '../src/context/AuthContext';

function AppWithAuth() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}

describe('App', () => {
  it('redirects to login page when not authenticated', () => {
    render(<AppWithAuth />);
    expect(screen.getByText('CI Dashboard')).toBeInTheDocument();
    expect(screen.getAllByText('Giriş Yap').length).toBeGreaterThan(0);
  });

  it('renders without crashing', () => {
    const { container } = render(<AppWithAuth />);
    expect(container).toBeInTheDocument();
  });

  it('shows the app branding in login page', () => {
    render(<AppWithAuth />);
    expect(screen.getByText('Continuous Integration Otomasyon Sistemi')).toBeInTheDocument();
  });
});
