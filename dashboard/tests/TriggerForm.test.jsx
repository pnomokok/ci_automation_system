import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../src/services/api', () => ({
  triggerPipeline: vi.fn(),
  formatApiError: (err) => err?.message || 'Hata',
}));

import { triggerPipeline } from '../src/services/api';
import TriggerForm from '../src/components/TriggerForm';

const REPO_URL = 'https://github.com/org/repo';

describe('TriggerForm', () => {
  const onSuccess = vi.fn();
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders_repo_url_as_readonly', () => {
    render(<TriggerForm repoUrl={REPO_URL} onSuccess={onSuccess} onClose={onClose} />);
    expect(screen.getByText(REPO_URL)).toBeInTheDocument();
    expect(screen.queryByDisplayValue(REPO_URL)).toBeNull();
  });

  it('renders_branch_input', () => {
    render(<TriggerForm repoUrl={REPO_URL} onSuccess={onSuccess} onClose={onClose} />);
    expect(screen.getByPlaceholderText('main')).toBeInTheDocument();
  });

  it('submit_without_branch_shows_error', async () => {
    render(<TriggerForm repoUrl={REPO_URL} onSuccess={onSuccess} onClose={onClose} />);
    await userEvent.clear(screen.getByPlaceholderText('main'));
    fireEvent.click(screen.getByText('Pipeline Başlat'));
    await waitFor(() => {
      expect(screen.getByText('Branch adı zorunludur.')).toBeInTheDocument();
    });
  });

  it('submit_calls_triggerPipeline_with_correct_args', async () => {
    triggerPipeline.mockResolvedValue({ data: { id: 'pl-1', status: 'QUEUED' } });
    render(<TriggerForm repoUrl={REPO_URL} onSuccess={onSuccess} onClose={onClose} />);

    await userEvent.clear(screen.getByPlaceholderText('main'));
    await userEvent.type(screen.getByPlaceholderText('main'), 'develop');
    fireEvent.click(screen.getByText('Pipeline Başlat'));

    await waitFor(() => {
      expect(triggerPipeline).toHaveBeenCalledWith(REPO_URL, 'develop', null);
    });
    expect(onSuccess).toHaveBeenCalledWith({ id: 'pl-1', status: 'QUEUED' });
  });

  it('api_error_shows_message', async () => {
    triggerPipeline.mockRejectedValue({ message: 'Sunucu hatası' });
    render(<TriggerForm repoUrl={REPO_URL} onSuccess={onSuccess} onClose={onClose} />);
    fireEvent.click(screen.getByText('Pipeline Başlat'));
    await waitFor(() => {
      expect(screen.getByText('Sunucu hatası')).toBeInTheDocument();
    });
  });

  it('cancel_button_calls_onClose', () => {
    render(<TriggerForm repoUrl={REPO_URL} onSuccess={onSuccess} onClose={onClose} />);
    fireEvent.click(screen.getByText('İptal'));
    expect(onClose).toHaveBeenCalled();
  });
});
