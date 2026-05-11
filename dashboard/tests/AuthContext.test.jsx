import { render, screen, act } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

vi.mock('../src/services/api', () => ({
  loginUser: vi.fn(),
  decodeToken: vi.fn(),
  formatApiError: (err) => err?.message || 'Hata',
}));

import { loginUser, decodeToken } from '../src/services/api';
import { AuthProvider, useAuth } from '../src/context/AuthContext';

function Consumer() {
  const { isAuthenticated, user, isLoading } = useAuth();
  return (
    <div>
      <span data-testid="auth">{isAuthenticated ? 'yes' : 'no'}</span>
      <span data-testid="user">{user?.username || 'none'}</span>
      <span data-testid="loading">{isLoading ? 'loading' : 'idle'}</span>
    </div>
  );
}

function LoginConsumer() {
  const { login, logout, isAuthenticated } = useAuth();
  return (
    <div>
      <span data-testid="auth">{isAuthenticated ? 'yes' : 'no'}</span>
      <button onClick={() => login('alice', 'pass123')}>Login</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    decodeToken.mockReturnValue(null);
  });

  it('provides unauthenticated state by default', () => {
    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );
    expect(screen.getByTestId('auth').textContent).toBe('no');
    expect(screen.getByTestId('user').textContent).toBe('none');
    expect(screen.getByTestId('loading').textContent).toBe('idle');
  });

  it('provides authenticated state when token is in localStorage', () => {
    localStorage.setItem('access_token', 'fake-token');
    decodeToken.mockReturnValue({ username: 'alice', id: 'u1' });

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );
    expect(screen.getByTestId('auth').textContent).toBe('yes');
    expect(screen.getByTestId('user').textContent).toBe('alice');
  });

  it('login sets token and user', async () => {
    loginUser.mockResolvedValue({ data: { access_token: 'new-token' } });
    decodeToken.mockReturnValue({ username: 'alice', id: 'u1' });

    render(
      <AuthProvider>
        <LoginConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth').textContent).toBe('no');
    await act(async () => {
      screen.getByText('Login').click();
    });
    expect(screen.getByTestId('auth').textContent).toBe('yes');
    expect(localStorage.getItem('access_token')).toBe('new-token');
  });

  it('logout clears token and user', async () => {
    localStorage.setItem('access_token', 'existing-token');
    decodeToken.mockReturnValue({ username: 'alice', id: 'u1' });

    render(
      <AuthProvider>
        <LoginConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth').textContent).toBe('yes');
    await act(async () => {
      screen.getByText('Logout').click();
    });
    expect(screen.getByTestId('auth').textContent).toBe('no');
    expect(localStorage.getItem('access_token')).toBeNull();
  });

  it('throws error when useAuth is used outside AuthProvider', () => {
    const originalError = console.error;
    console.error = vi.fn();
    expect(() => render(<Consumer />)).toThrow();
    console.error = originalError;
  });
});
