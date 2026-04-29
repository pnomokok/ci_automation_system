import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => (error ? prom.reject(error) : prom.resolve(token)));
  failedQueue = [];
};

// Attach JWT token to every request
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// Auto-refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      });
    }

    original._retry = true;
    isRefreshing = true;

    try {
      const res = await axios.post(
        `${BASE_URL}/api/v1/auth/refresh`,
        {},
        { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } }
      );
      const newToken = res.data.access_token;
      localStorage.setItem('access_token', newToken);
      processQueue(null, newToken);
      original.headers.Authorization = `Bearer ${newToken}`;
      return api(original);
    } catch (err) {
      processQueue(err, null);
      localStorage.removeItem('access_token');
      window.location.href = '/login';
      return Promise.reject(err);
    } finally {
      isRefreshing = false;
    }
  }
);

// ── Auth ─────────────────────────────────────────
export const loginUser = (username, password) =>
  api.post('/auth/login', { username, password });

export const refreshToken = () =>
  api.post('/auth/refresh');

// ── Pipelines ────────────────────────────────────
export const getPipelines = (params = {}) =>
  api.get('/pipelines', { params });

export const getPipeline = (id) =>
  api.get(`/pipelines/${id}`);

export const createPipeline = (repoUrl, branch) =>
  api.post('/pipelines', { repo_url: repoUrl, branch });

export const stopPipeline = (id) =>
  api.post(`/pipelines/${id}/stop`);

export const getPipelineLogs = (id, params = {}) =>
  api.get(`/pipelines/${id}/logs`, { params });

export const getPipelineReport = (id) =>
  api.get(`/pipelines/${id}/report`);

// ── Repositories ─────────────────────────────────
export const getRepositories = (params = {}) =>
  api.get('/repositories', { params });

export const createRepository = (data) =>
  api.post('/repositories', data);

export const deleteRepository = (id) =>
  api.delete(`/repositories/${id}`);

// ── Helpers ──────────────────────────────────────
export const formatApiError = (error) => {
  if (error.response?.data?.error?.message) return error.response.data.error.message;
  if (error.response?.data?.detail) {
    const d = error.response.data.detail;
    return typeof d === 'string' ? d : JSON.stringify(d);
  }
  if (error.message === 'Network Error') return 'Sunucuya bağlanılamıyor. Servisin çalıştığından emin olun.';
  if (error.code === 'ECONNABORTED') return 'İstek zaman aşımına uğradı.';
  return error.message || 'Beklenmedik bir hata oluştu.';
};

export const formatDuration = (seconds) => {
  if (seconds == null) return '—';
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
};

export const formatDate = (dateStr) => {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString('tr-TR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

export const decodeToken = (token) => {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
  } catch {
    return null;
  }
};

export default api;
