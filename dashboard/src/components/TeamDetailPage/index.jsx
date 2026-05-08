import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  addTeamMember, formatApiError, formatDate,
  getRepositories, getTeamMembers, removeTeamMember,
} from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const TABS = ['Üyeler', 'Repolar'];

function repoShortName(url) {
  return url?.replace(/^https?:\/\/github\.com\//, '') || url || '—';
}

function AddMemberModal({ teamId, onSuccess, onClose }) {
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim()) { setError('Kullanıcı adı zorunludur.'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await addTeamMember(teamId, username.trim());
      onSuccess(res.data);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-dark-900 border border-dark-600 rounded-lg w-full max-w-sm p-6 shadow-xl">
        <h2 className="text-base font-semibold text-gray-100 mb-4">Üye Ekle</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Kullanıcı Adı</label>
            <input
              type="text"
              autoFocus
              placeholder="kullanici_adi"
              value={username}
              onChange={(e) => { setUsername(e.target.value); setError(''); }}
              className="w-full bg-dark-800 border border-dark-600 text-gray-200 text-sm rounded-md px-3 py-2
                         focus:outline-none focus:border-blue-500"
            />
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <div className="flex gap-3 justify-end">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors">
              İptal
            </button>
            <button type="submit" disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium
                         px-4 py-2 rounded-md transition-colors">
              {loading ? 'Ekleniyor...' : 'Ekle'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function TeamDetailPage() {
  const { teamId } = useParams();
  const { user, teams } = useAuth();
  const navigate = useNavigate();

  const teamName = teams.find(t => t.id === teamId)?.name || 'Takım';

  const [activeTab, setActiveTab] = useState('Üyeler');
  const [members, setMembers] = useState([]);
  const [repos, setRepos] = useState([]);
  const [membersLoading, setMembersLoading] = useState(true);
  const [reposLoading, setReposLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [removingId, setRemovingId] = useState(null);

  const fetchMembers = async () => {
    setMembersLoading(true);
    try {
      const res = await getTeamMembers(teamId);
      setMembers(res.data);
      setError('');
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setMembersLoading(false);
    }
  };

  const fetchRepos = async () => {
    setReposLoading(true);
    try {
      const res = await getRepositories();
      const list = res.data.items ?? res.data;
      setRepos(list.filter(r => r.owner_type === 'team' && r.owner_id === teamId));
    } catch {
      setRepos([]);
    } finally {
      setReposLoading(false);
    }
  };

  useEffect(() => {
    fetchMembers();
    fetchRepos();
  }, [teamId]);

  const handleRemove = async (userId, username) => {
    if (!window.confirm(`"${username}" takımdan çıkarılsın mı?`)) return;
    setRemovingId(userId);
    try {
      await removeTeamMember(teamId, userId);
      setMembers(prev => prev.filter(m => m.user_id !== userId));
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <Link to="/teams" className="text-gray-500 hover:text-gray-200 text-sm transition-colors">
          ← Takımlar
        </Link>
        <h1 className="text-xl font-semibold text-gray-100 mt-3">{teamName}</h1>
      </div>

      {error && (
        <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-md px-4 py-3">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-dark-600">
        <div className="flex gap-0">
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === tab
                  ? 'text-white border-blue-500'
                  : 'text-gray-500 border-transparent hover:text-gray-300'
              }`}
            >
              {tab}
              {tab === 'Üyeler' && !membersLoading && (
                <span className="ml-1.5 text-xs text-gray-600">({members.length})</span>
              )}
              {tab === 'Repolar' && !reposLoading && (
                <span className="ml-1.5 text-xs text-gray-600">({repos.length})</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Üyeler */}
      {activeTab === 'Üyeler' && (
        <div>
          <div className="flex justify-end mb-3">
            <button
              onClick={() => setShowAdd(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-md transition-colors"
            >
              + Üye Ekle
            </button>
          </div>
          {membersLoading ? (
            <div className="flex justify-center py-10">
              <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : members.length === 0 ? (
            <div className="bg-dark-900 border border-dark-600 rounded-lg py-12 text-center text-gray-500">
              Henüz üye yok.
            </div>
          ) : (
            <div className="bg-dark-900 border border-dark-600 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-dark-600 text-gray-500 text-xs uppercase tracking-wider">
                    <th className="text-left px-4 py-3">Kullanıcı Adı</th>
                    <th className="text-left px-4 py-3">Katılma Tarihi</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {members.map((m, i) => (
                    <tr key={m.user_id}
                      className={`border-b border-dark-700 ${i === members.length - 1 ? 'border-b-0' : ''}`}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-dark-700 flex items-center justify-center text-xs font-medium text-gray-300">
                            {m.username[0].toUpperCase()}
                          </div>
                          <span className="text-gray-200 text-sm">{m.username}</span>
                          {m.username === user?.username && (
                            <span className="text-xs text-blue-400">Sen</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {m.joined_at ? new Date(m.joined_at).toLocaleString('tr-TR') : '—'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {m.username !== user?.username && (
                          <button
                            onClick={() => handleRemove(m.user_id, m.username)}
                            disabled={removingId === m.user_id}
                            className="text-xs text-red-500 hover:text-red-400 disabled:opacity-40 transition-colors"
                          >
                            {removingId === m.user_id ? 'Çıkarılıyor...' : 'Çıkar'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Repolar */}
      {activeTab === 'Repolar' && (
        <div>
          {reposLoading ? (
            <div className="flex justify-center py-10">
              <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : repos.length === 0 ? (
            <div className="bg-dark-900 border border-dark-600 rounded-lg py-12 text-center text-gray-500">
              Bu takıma ait repository yok.
            </div>
          ) : (
            <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
              {repos.map(repo => (
                <div
                  key={repo.id}
                  onClick={() => navigate(`/repositories/${repo.id}`)}
                  className="bg-dark-900 border border-dark-600 rounded-lg p-4 hover:border-blue-500/50 hover:bg-dark-800
                             transition-all cursor-pointer group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-mono text-sm text-gray-200 group-hover:text-white transition-colors break-all">
                      {repoShortName(repo.url)}
                    </span>
                    <span className="text-gray-600 group-hover:text-blue-400 transition-colors text-sm shrink-0">→</span>
                  </div>
                  <div className="mt-2">
                    <span className="text-xs text-gray-600 font-mono">{repo.default_branch}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {showAdd && (
        <AddMemberModal
          teamId={teamId}
          onSuccess={() => { setShowAdd(false); fetchMembers(); }}
          onClose={() => setShowAdd(false)}
        />
      )}
    </div>
  );
}
