import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/context/AuthContext', () => ({
  useAuth: () => ({
    login: vi.fn().mockResolvedValue(undefined),
    isAuthenticated: false,
  }),
}));

vi.mock('../src/services/api', () => ({
  formatApiError: (err) => err?.message || 'Hata',
  registerUser: vi.fn(),
}));

import LoginPage from '../src/pages/LoginPage';

function renderLoginPage() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows CI Dashboard branding', () => {
    renderLoginPage();
    expect(screen.getByText('CI Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Continuous Integration Otomasyon Sistemi')).toBeInTheDocument();
  });

  it('shows login tab by default', () => {
    renderLoginPage();
    expect(screen.getByPlaceholderText('kullanici_adi')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
  });

  it('shows validation error for empty username', async () => {
    renderLoginPage();
    const submitBtn = screen.getAllByRole('button', { name: 'Giriş Yap' })[1];
    await userEvent.click(submitBtn);
    expect(screen.getByText('Kullanıcı adı ve şifre zorunludur.')).toBeInTheDocument();
  });

  it('switches to register tab and shows extra fields', async () => {
    renderLoginPage();
    await userEvent.click(screen.getByRole('button', { name: 'Kayıt Ol' }));
    expect(screen.getByPlaceholderText('ornek@email.com')).toBeInTheDocument();
  });

  it('shows password mismatch error on register', async () => {
    renderLoginPage();
    await userEvent.click(screen.getAllByRole('button', { name: 'Kayıt Ol' })[0]);

    await userEvent.type(screen.getByPlaceholderText('kullanici_adi'), 'testuser');
    const passwords = screen.getAllByPlaceholderText('••••••••');
    await userEvent.type(passwords[0], 'password123');
    await userEvent.type(passwords[1], 'different456');

    await userEvent.click(screen.getAllByRole('button', { name: 'Kayıt Ol' })[1]);
    expect(screen.getByText('Şifreler eşleşmiyor.')).toBeInTheDocument();
  });

  it('shows short password error on register', async () => {
    renderLoginPage();
    await userEvent.click(screen.getAllByRole('button', { name: 'Kayıt Ol' })[0]);

    await userEvent.type(screen.getByPlaceholderText('kullanici_adi'), 'testuser');
    const passwords = screen.getAllByPlaceholderText('••••••••');
    await userEvent.type(passwords[0], 'abc');
    await userEvent.type(passwords[1], 'abc');

    await userEvent.click(screen.getAllByRole('button', { name: 'Kayıt Ol' })[1]);
    expect(screen.getByText('Şifre en az 6 karakter olmalıdır.')).toBeInTheDocument();
  });
});
