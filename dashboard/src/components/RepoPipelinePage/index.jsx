import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { formatApiError, formatDate, formatDuration, getPipelines, getRepositories } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import StatusBadge from '../StatusBadge';
import TriggerForm from '../TriggerForm';

const PAGE_SIZE = 20;
const STATUSES = ['', 'QUEUED', 'RUNNING', 'SUCCESS', 'FAILED', 'STOPPED'];

function repoShortName(url) {
  return url?.replace(/^https?:\/\/github\.com\//, '') || url || '—';
}

export default function RepoPipelinePage() {
  const { repoId } = useParams();
  const { teams } = useAuth();
  const navigate = useNavigate();

  const [repo, setRepo] = useState(null);
  const [pipelines, setPipelines] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showTrigger, setShowTrigger] = useState(false);

  useEffect(() => {
    getRepositories()
      .then(res => {
        const list = res.data.items ?? res.data;
        setRepo(list.find(r => r.id === repoId) || null);
      })
      .catch(() => {});
  }, [repoId]);

  const fetchPipelines = useCallback(async () => {
    try {
      const params = { page, page_size: PAGE_SIZE, repo_id: repoId };
      if (statusFilter) params.status = statusFilter;
      const res = await getPipelines(params);
      setPipelines(res.data.items);
      setTotal(res.data.total);
      setError('');
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [repoId, page, statusFilter]);

  useEffect(() => {
    setLoading(true);
    fetchPipelines();
  }, [fetchPipelines]);

  const hasRunning = pipelines.some(p => p.status === 'RUNNING');
  const pollRef = useRef(null);
  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (hasRunning) pollRef.current = setInterval(fetchPipelines, 5000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [hasRunning, fetchPipelines]);

  const ownerLabel = repo
    ? repo.owner_type === 'user'
      ? 'Kişisel'
      : teams.find(t => t.id === repo.owner_id)?.name || 'Takım'
    : null;

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <Link to="/repositories" className="text-gray-500 hover:text-gray-200 text-sm transition-colors">
          ← Repositories
        </Link>
        <div className="flex items-start justify-between mt-3 gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-100 font-mono break-all">
              {repo ? repoShortName(repo.url) : repoId}
            </h1>
            {ownerLabel && (
              <span className="text-xs mt-1 inline-block px-2 py-0.5 rounded-full bg-dark-700 text-gray-400 border border-dark-600">
                {ownerLabel}
              </span>
            )}
          </div>
          <button
            onClick={() => setShowTrigger(true)}
            className="shrink-0 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-md transition-colors"
          >
            + Pipeline Tetikle
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="bg-dark-900 border border-dark-600 text-gray-300 text-sm rounded-md px-3 py-1.5
                     focus:outline-none focus:border-blue-500"
        >
          {STATUSES.map(s => (
            <option key={s} value={s}>{s || 'Tüm Durumlar'}</option>
          ))}
        </select>
        <span className="text-sm text-gray-500">
          {total} pipeline
          {hasRunning && (
            <span className="ml-2 text-blue-400 text-xs animate-pulse">● canlı güncelleniyor</span>
          )}
        </span>
      </div>

      {error && (
        <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-md px-4 py-3">
          {error}
          <button onClick={fetchPipelines} className="ml-3 underline hover:no-underline">Tekrar dene</button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : pipelines.length === 0 ? (
        <div className="bg-dark-900 border border-dark-600 rounded-lg py-16 text-center text-gray-500">
          {statusFilter ? 'Bu filtre için pipeline bulunamadı.' : 'Henüz hiç pipeline yok.'}
        </div>
      ) : (
        <div className="bg-dark-900 border border-dark-600 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-600 text-gray-500 text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3">Durum</th>
                <th className="text-left px-4 py-3">Branch / Commit</th>
                <th className="text-left px-4 py-3">Tetikleme</th>
                <th className="text-left px-4 py-3">Süre</th>
                <th className="text-left px-4 py-3">Başlangıç</th>
              </tr>
            </thead>
            <tbody>
              {pipelines.map((pipeline, i) => (
                <tr
                  key={pipeline.id}
                  onClick={() => navigate(`/repositories/${repoId}/pipelines/${pipeline.id}`)}
                  className={`border-b border-dark-700 hover:bg-dark-800 transition-colors cursor-pointer ${
                    i === pipelines.length - 1 ? 'border-b-0' : ''
                  }`}
                >
                  <td className="px-4 py-3"><StatusBadge status={pipeline.status} /></td>
                  <td className="px-4 py-3">
                    <div className="text-gray-300 font-mono text-xs">{pipeline.branch}</div>
                    {pipeline.commit_hash && (
                      <div className="text-gray-500 font-mono text-xs mt-0.5">
                        {pipeline.commit_hash.slice(0, 7)}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {pipeline.trigger_type === 'webhook' ? '🔗 Webhook' : '✋ Manuel'}
                  </td>
                  <td className="px-4 py-3 text-gray-400 font-mono text-xs">
                    {formatDuration(pipeline.duration_sec)}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {formatDate(pipeline.started_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500">Sayfa {page} / {totalPages} ({total} kayıt)</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
              className="px-3 py-1 text-sm bg-dark-800 border border-dark-600 rounded text-gray-300
                         hover:bg-dark-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
              ← Önceki
            </button>
            <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
              className="px-3 py-1 text-sm bg-dark-800 border border-dark-600 rounded text-gray-300
                         hover:bg-dark-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
              Sonraki →
            </button>
          </div>
        </div>
      )}

      {showTrigger && repo && (
        <TriggerForm
          repoUrl={repo.url}
          teamId={repo.team_id ?? null}
          onSuccess={() => { setShowTrigger(false); setPage(1); setStatusFilter(''); fetchPipelines(); }}
          onClose={() => setShowTrigger(false)}
        />
      )}
    </div>
  );
}
