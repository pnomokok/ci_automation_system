import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
});

// Attach JWT token to every request
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// Token süresi dolunca login'e yönlendir
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ── Auth ─────────────────────────────────────────
export const loginUser = (username, password) =>
  api.post('/auth/login', { username, password });

export const registerUser = (username, password) =>
  api.post('/auth/register', { username, password });

// ── Pipelines ────────────────────────────────────
export const getPipelines = (params = {}) =>
  api.get('/pipelines', { params });

export const getPipeline = (id) =>
  api.get(`/pipelines/${id}`);

export const getPipelinesByRepo = (repoId) =>
  api.get('/pipelines', { params: { repo_id: repoId } });

export const createPipeline = (repoUrl, branch) =>
  api.post('/pipelines', { repo_url: repoUrl, branch });

export const triggerPipeline = (repoUrl, branch, teamId = null) =>
  axios.post('/trigger', { repo_url: repoUrl, branch, team_id: teamId }, { timeout: 60000 });

export const stopPipeline = (id) =>
  api.post(`/pipelines/${id}/stop`);

export const getPipelineLogs = (id, params = {}) =>
  api.get(`/pipelines/${id}/logs`, { params });

export const getPipelineReport = (id) =>
  api.get(`/pipelines/${id}/report`);

// ── Teams ─────────────────────────────────────────
export const getTeams = () =>
  api.get('/teams');

export const createTeam = (name) =>
  api.post('/teams', { name });

export const getTeamDetail = (teamId) =>
  api.get(`/teams/${teamId}`);

export const getTeamMembers = (teamId) =>
  api.get(`/teams/${teamId}/members`);

export const getTeamRepositories = async (teamId) => {
  try {
    return await api.get(`/teams/${teamId}/repositories`);
  } catch {
    return { data: [] };
  }
};

export const addTeamMember = (teamId, username) =>
  api.post(`/teams/${teamId}/members`, { username });

export const removeTeamMember = (teamId, userId) =>
  api.delete(`/teams/${teamId}/members/${userId}`);

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
    if (typeof d === 'string') return d;
    if (typeof d === 'object' && d !== null && d.message) return d.message;
    return JSON.stringify(d);
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
