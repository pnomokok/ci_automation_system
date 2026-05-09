import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  addRepoMember,
  deletePipeline,
  formatApiError,
  formatDate,
  formatDuration,
  getPipelines,
  getRepoMembers,
  getRepositories,
  removeRepoMember,
  updateRepoMemberRole,
} from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import StatusBadge from '../StatusBadge';
import TriggerForm from '../TriggerForm';

const PAGE_SIZE = 20;
const STATUSES = ['', 'QUEUED', 'RUNNING', 'SUCCESS', 'FAILED', 'STOPPED'];

function repoShortName(url) {
  return url?.replace(/^https?:\/\/github\.com\//, '') || url || '—';
}

function RoleBadge({ role }) {
  const isOwner = role === 'owner';
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${
      isOwner
        ? 'bg-blue-950 text-blue-300 border-blue-800'
        : 'bg-dark-700 text-gray-400 border-dark-600'
    }`}>
      {isOwner ? 'Owner' : 'Member'}
    </span>
  );
}

function MembersPanel({ repoId, isOwner, currentUserId }) {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [addUsername, setAddUsername] = useState('');
  const [addRole, setAddRole] = useState('member');
  const [adding, setAdding] = useState(false);
  const [busyId, setBusyId] = useState(null);

  const fetchMembers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getRepoMembers(repoId);
      setMembers(res.data);
      setError('');
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [repoId]);

  useEffect(() => { fetchMembers(); }, [fetchMembers]);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!addUsername.trim()) return;
    setAdding(true);
    setError('');
    try {
      await addRepoMember(repoId, addUsername.trim(), addRole);
      setAddUsername('');
      setAddRole('member');
      fetchMembers();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setAdding(false);
    }
  };

  const handleRoleChange = async (member, newRole) => {
    setBusyId(member.user_id);
    setError('');
    try {
      await updateRepoMemberRole(repoId, member.user_id, newRole);
      fetchMembers();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusyId(null);
    }
  };

  const handleRemove = async (member) => {
    if (!window.confirm(`${member.username} bu repodan çıkarılsın mı?`)) return;
    setBusyId(member.user_id);
    setError('');
    try {
      await removeRepoMember(repoId, member.user_id);
      fetchMembers();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      {isOwner && (
        <form onSubmit={handleAdd} className="bg-dark-900 border border-dark-600 rounded-lg p-4 flex gap-3 items-end flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs text-gray-400 mb-1">Kullanıcı adı</label>
            <input
              type="text"
              value={addUsername}
              onChange={(e) => setAddUsername(e.target.value)}
              placeholder="kullanici_adi"
              className="w-full bg-dark-800 border border-dark-600 text-gray-200 text-sm rounded-md px-3 py-2
                         focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Rol</label>
            <select
              value={addRole}
              onChange={(e) => setAddRole(e.target.value)}
              className="bg-dark-800 border border-dark-600 text-gray-200 text-sm rounded-md px-3 py-2
                         focus:outline-none focus:border-blue-500"
            >
              <option value="member">Member</option>
              <option value="owner">Owner</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={adding || !addUsername.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium
                       px-4 py-2 rounded-md transition-colors"
          >
            {adding ? 'Ekleniyor...' : '+ Üye Ekle'}
          </button>
        </form>
      )}

      {error && (
        <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-md px-4 py-3">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="bg-dark-900 border border-dark-600 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-600 text-gray-500 text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3">Kullanıcı</th>
                <th className="text-left px-4 py-3">Rol</th>
                <th className="text-left px-4 py-3">Eklendi</th>
                {isOwner && <th className="px-4 py-3" />}
              </tr>
            </thead>
            <tbody>
              {members.map((m, i) => (
                <tr key={m.id}
                    className={`border-b border-dark-700 ${i === members.length - 1 ? 'border-b-0' : ''}`}>
                  <td className="px-4 py-3 text-gray-200">
                    {m.username}
                    {m.user_id === currentUserId && (
                      <span className="ml-2 text-xs text-gray-500">(siz)</span>
                    )}
                  </td>
                  <td className="px-4 py-3"><RoleBadge role={m.role} /></td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{formatDate(m.created_at)}</td>
                  {isOwner && (
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex gap-2">
                        {m.role === 'member' ? (
                          <button
                            disabled={busyId === m.user_id}
                            onClick={() => handleRoleChange(m, 'owner')}
                            className="text-xs text-blue-400 hover:text-blue-300 transition-colors disabled:opacity-40"
                          >
                            Owner Yap
                          </button>
                        ) : (
                          m.user_id !== currentUserId && (
                            <button
                              disabled={busyId === m.user_id}
                              onClick={() => handleRoleChange(m, 'member')}
                              className="text-xs text-gray-400 hover:text-gray-200 transition-colors disabled:opacity-40"
                            >
                              Member Yap
                            </button>
                          )
                        )}
                        {m.user_id !== currentUserId && (
                          <button
                            disabled={busyId === m.user_id}
                            onClick={() => handleRemove(m)}
                            className="text-xs text-red-500 hover:text-red-400 transition-colors disabled:opacity-40"
                          >
                            Çıkar
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function RepoPipelinePage() {
  const { repoId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [repo, setRepo] = useState(null);
  const [tab, setTab] = useState('pipelines');
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
    if (tab !== 'pipelines') return;
    setLoading(true);
    fetchPipelines();
  }, [fetchPipelines, tab]);

  const hasRunning = pipelines.some(p => p.status === 'RUNNING');
  const pollRef = useRef(null);
  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (hasRunning && tab === 'pipelines') pollRef.current = setInterval(fetchPipelines, 5000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [hasRunning, fetchPipelines, tab]);

  const isOwner = repo?.my_role === 'owner';
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
            {repo?.my_role && (
              <span className="text-xs mt-1 inline-block">
                <RoleBadge role={repo.my_role} />
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

      {/* Tabs */}
      <div className="flex gap-1 border-b border-dark-600">
        <button
          onClick={() => setTab('pipelines')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
            tab === 'pipelines'
              ? 'text-white border-blue-500'
              : 'text-gray-500 hover:text-gray-300 border-transparent'
          }`}
        >
          Pipelines
        </button>
        <button
          onClick={() => setTab('members')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
            tab === 'members'
              ? 'text-white border-blue-500'
              : 'text-gray-500 hover:text-gray-300 border-transparent'
          }`}
        >
          Üyeler
        </button>
      </div>

      {tab === 'pipelines' ? (
        <>
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
                    <th className="text-left px-4 py-3">ID</th>
                    <th className="text-left px-4 py-3">Durum</th>
                    <th className="text-left px-4 py-3">Branch / Commit</th>
                    <th className="text-left px-4 py-3">Tetikleyen</th>
                    <th className="text-left px-4 py-3">Tetikleme</th>
                    <th className="text-left px-4 py-3">Süre</th>
                    <th className="text-left px-4 py-3">Başlangıç</th>
                    <th className="px-4 py-3" />
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
                      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{pipeline.id.slice(0, 8)}</td>
                      <td className="px-4 py-3"><StatusBadge status={pipeline.status} /></td>
                      <td className="px-4 py-3">
                        <div className="text-gray-300 font-mono text-xs">{pipeline.branch}</div>
                        {pipeline.commit_hash && (
                          <div className="text-gray-500 font-mono text-xs mt-0.5">
                            {pipeline.commit_hash.slice(0, 7)}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-300 text-xs font-mono">
                        {pipeline.triggered_by_username ?? <span className="text-gray-600">—</span>}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {pipeline.trigger_type === 'webhook' ? '🔗 Webhook' : 'Manuel'}
                      </td>
                      <td className="px-4 py-3 text-gray-400 font-mono text-xs">
                        {formatDuration(pipeline.duration_sec)}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {formatDate(pipeline.started_at)}
                      </td>
                      <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                        {!['QUEUED', 'RUNNING'].includes(pipeline.status) && (
                          <button
                            onClick={async () => {
                              if (!window.confirm(`Pipeline ${pipeline.id.slice(0, 8)} silinsin mi?`)) return;
                              try {
                                await deletePipeline(pipeline.id);
                                setPipelines(prev => prev.filter(p => p.id !== pipeline.id));
                                setTotal(prev => prev - 1);
                              } catch (err) {
                                setError(formatApiError(err));
                              }
                            }}
                            className="text-xs text-red-500 hover:text-red-400 transition-colors"
                          >
                            Sil
                          </button>
                        )}
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
        </>
      ) : (
        <MembersPanel repoId={repoId} isOwner={isOwner} currentUserId={user?.sub} />
      )}

      {showTrigger && repo && (
        <TriggerForm
          repoUrl={repo.url}
          onSuccess={(pipeline) => {
            setShowTrigger(false);
            if (pipeline?.id) {
              navigate(`/repositories/${repoId}/pipelines/${pipeline.id}`);
            } else {
              setPage(1);
              setStatusFilter('');
              fetchPipelines();
            }
          }}
          onClose={() => setShowTrigger(false)}
        />
      )}
    </div>
  );
}
