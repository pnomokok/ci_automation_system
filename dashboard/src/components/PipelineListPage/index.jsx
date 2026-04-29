import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { formatApiError, formatDate, formatDuration, getPipelines } from '../../services/api';
import StatusBadge from '../StatusBadge';
import TriggerForm from '../TriggerForm';

const PAGE_SIZE = 20;
const STATUSES = ['', 'QUEUED', 'RUNNING', 'SUCCESS', 'FAILED', 'STOPPED'];

function Spinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

export default function PipelineListPage() {
  const [pipelines, setPipelines] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showTrigger, setShowTrigger] = useState(false);

  const fetchPipelines = useCallback(async () => {
    try {
      const params = { page, page_size: PAGE_SIZE };
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
  }, [page, statusFilter]);

  // Initial + param-change fetch
  useEffect(() => {
    setLoading(true);
    fetchPipelines();
  }, [fetchPipelines]);

  // 5s polling when any pipeline is RUNNING
  const hasRunning = pipelines.some((p) => p.status === 'RUNNING');
  const pollRef = useRef(null);
  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (hasRunning) pollRef.current = setInterval(fetchPipelines, 5000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [hasRunning, fetchPipelines]);

  const handleTriggerSuccess = () => {
    setShowTrigger(false);
    setPage(1);
    setStatusFilter('');
    fetchPipelines();
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      {/* Page header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-gray-100">Pipelines</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {total} pipeline
            {hasRunning && (
              <span className="ml-2 text-blue-400 text-xs animate-pulse-slow">● canlı güncelleniyor</span>
            )}
          </p>
        </div>
        <button
          onClick={() => setShowTrigger(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-md transition-colors"
        >
          + Pipeline Tetikle
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="bg-dark-900 border border-dark-600 text-gray-300 text-sm rounded-md px-3 py-1.5
                     focus:outline-none focus:border-blue-500"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s || 'Tüm Durumlar'}</option>
          ))}
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-md px-4 py-3 mb-4">
          {error}
          <button
            onClick={fetchPipelines}
            className="ml-3 underline hover:no-underline"
          >
            Tekrar dene
          </button>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <Spinner />
      ) : pipelines.length === 0 ? (
        <div className="bg-dark-900 border border-dark-600 rounded-lg py-16 text-center text-gray-500">
          {statusFilter ? 'Bu filtre için pipeline bulunamadı.' : 'Henüz hiç pipeline yok. Yeni bir pipeline tetikleyin.'}
        </div>
      ) : (
        <div className="bg-dark-900 border border-dark-600 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-600 text-gray-500 text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3">Durum</th>
                <th className="text-left px-4 py-3">Repository</th>
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
                  className={`border-b border-dark-700 hover:bg-dark-800 transition-colors cursor-pointer ${
                    i === pipelines.length - 1 ? 'border-b-0' : ''
                  }`}
                  onClick={() => { window.location.href = `/pipelines/${pipeline.id}`; }}
                >
                  <td className="px-4 py-3">
                    <StatusBadge status={pipeline.status} />
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-gray-200 font-mono text-xs">
                      {pipeline.repo_url?.replace('https://github.com/', '') || '—'}
                    </span>
                  </td>
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

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-sm text-gray-500">
            Sayfa {page} / {totalPages} ({total} kayıt)
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1 text-sm bg-dark-800 border border-dark-600 rounded text-gray-300
                         hover:bg-dark-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              ← Önceki
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1 text-sm bg-dark-800 border border-dark-600 rounded text-gray-300
                         hover:bg-dark-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Sonraki →
            </button>
          </div>
        </div>
      )}

      {/* Trigger modal */}
      {showTrigger && (
        <TriggerForm
          onSuccess={handleTriggerSuccess}
          onClose={() => setShowTrigger(false)}
        />
      )}
    </div>
  );
}
