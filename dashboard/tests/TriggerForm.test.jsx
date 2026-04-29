import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/services/api', () => ({
  createPipeline: vi.fn(),
  formatApiError: (err) => err?.message || 'Hata oluştu',
}));

import { createPipeline } from '../src/services/api';
import TriggerForm from '../src/components/TriggerForm';

describe('TriggerForm', () => {
  const onSuccess = vi.fn();
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders URL and branch inputs', () => {
    render(<TriggerForm onSuccess={onSuccess} onClose={onClose} />);
    expect(screen.getByPlaceholderText('https://github.com/org/repo')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('main')).toBeInTheDocument();
  });

  it('shows validation error for empty URL', async () => {
    render(<TriggerForm onSuccess={onSuccess} onClose={onClose} />);
    fireEvent.click(screen.getByText('Pipeline Başlat'));
    await waitFor(() => {
      expect(screen.getByText('Repository URL zorunludur.')).toBeInTheDocument();
    });
  });

  it('shows validation error for invalid URL', async () => {
    render(<TriggerForm onSuccess={onSuccess} onClose={onClose} />);
    await userEvent.type(screen.getByPlaceholderText('https://github.com/org/repo'), 'not-a-url');
    fireEvent.click(screen.getByText('Pipeline Başlat'));
    await waitFor(() => {
      expect(screen.getByText(/Geçerli bir URL/)).toBeInTheDocument();
    });
  });

  it('calls createPipeline with correct args on valid submit', async () => {
    createPipeline.mockResolvedValue({ data: { id: 'test-id', status: 'QUEUED' } });
    render(<TriggerForm onSuccess={onSuccess} onClose={onClose} />);

    await userEvent.type(screen.getByPlaceholderText('https://github.com/org/repo'), 'https://github.com/test/repo');
    await userEvent.clear(screen.getByPlaceholderText('main'));
    await userEvent.type(screen.getByPlaceholderText('main'), 'develop');

    fireEvent.click(screen.getByText('Pipeline Başlat'));

    await waitFor(() => {
      expect(createPipeline).toHaveBeenCalledWith('https://github.com/test/repo', 'develop');
    });
    expect(onSuccess).toHaveBeenCalledWith({ id: 'test-id', status: 'QUEUED' });
  });

  it('displays API error message', async () => {
    createPipeline.mockRejectedValue({ message: 'Sunucu hatası' });
    render(<TriggerForm onSuccess={onSuccess} onClose={onClose} />);

    await userEvent.type(screen.getByPlaceholderText('https://github.com/org/repo'), 'https://github.com/test/repo');
    fireEvent.click(screen.getByText('Pipeline Başlat'));

    await waitFor(() => {
      expect(screen.getByText('Sunucu hatası')).toBeInTheDocument();
    });
  });

  it('calls onClose when cancel button is clicked', () => {
    render(<TriggerForm onSuccess={onSuccess} onClose={onClose} />);
    fireEvent.click(screen.getByText('İptal'));
    expect(onClose).toHaveBeenCalled();
  });
});
