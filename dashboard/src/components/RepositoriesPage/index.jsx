import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createRepository, deleteRepository, formatApiError, getRepositories } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

function repoShortName(url) {
  return url?.replace(/^https?:\/\/github\.com\//, '') || url || '—';
}

function AddRepoModal({ teams, onSuccess, onClose }) {
  const [form, setForm] = useState({
    url: '',
    default_branch: 'main',
    webhook_secret: '',
    owner_type: 'user',
    owner_id: 'user-001',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const setOwner = (value) => {
    if (value === 'user') {
      setForm(f => ({ ...f, owner_type: 'user', owner_id: 'user-001' }));
    } else {
      setForm(f => ({ ...f, owner_type: 'team', owner_id: value }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.url.trim()) { setError('Repository URL zorunludur.'); return; }
    if (!form.webhook_secret.trim()) { setError('Webhook secret zorunludur.'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await createRepository({
        url: form.url.trim(),
        default_branch: form.default_branch.trim() || 'main',
        webhook_secret: form.webhook_secret.trim(),
        owner_type: form.owner_type,
        owner_id: form.owner_id,
      });
      onSuccess(res.data);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-dark-900 border border-dark-600 rounded-lg w-full max-w-md p-6 shadow-xl">
        <h2 className="text-base font-semibold text-gray-100 mb-4">Yeni Repository Ekle</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Repository URL</label>
            <input
              type="text"
              placeholder="https://github.com/org/repo"
              value={form.url}
              onChange={(e) => setForm(f => ({ ...f, url: e.target.value }))}
              className="w-full bg-dark-800 border border-dark-600 text-gray-200 text-sm rounded-md px-3 py-2
                         focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Varsayılan Branch</label>
            <input
              type="text"
              placeholder="main"
              value={form.default_branch}
              onChange={(e) => setForm(f => ({ ...f, default_branch: e.target.value }))}
              className="w-full bg-dark-800 border border-dark-600 text-gray-200 text-sm rounded-md px-3 py-2
                         focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Webhook Secret</label>
            <input
              type="password"
              placeholder="gizli_anahtar"
              value={form.webhook_secret}
              onChange={(e) => setForm(f => ({ ...f, webhook_secret: e.target.value }))}
              className="w-full bg-dark-800 border border-dark-600 text-gray-200 text-sm rounded-md px-3 py-2
                         focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-2">Sahip</label>
            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio" name="owner"
                  checked={form.owner_type === 'user'}
                  onChange={() => setOwner('user')}
                  className="accent-blue-500"
                />
                <span className="text-sm text-gray-300">Kişisel</span>
              </label>
              {teams.map((team) => (
                <label key={team.id} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio" name="owner"
                    checked={form.owner_type === 'team' && form.owner_id === team.id}
                    onChange={() => setOwner(team.id)}
                    className="accent-blue-500"
                  />
                  <span className="text-sm text-gray-300">{team.name}</span>
                </label>
              ))}
            </div>
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <div className="flex gap-3 justify-end mt-2">
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

function RepoCard({ repo, teamName, onClick, onDelete }) {
  const ownerLabel = repo.owner_type === 'user' ? 'Kişisel' : teamName;
  return (
    <div
      className="bg-dark-900 border border-dark-600 rounded-lg p-4 hover:border-blue-500/50 hover:bg-dark-800
                 transition-all group relative"
    >
      <div
        onClick={onClick}
        className="cursor-pointer"
      >
        <div className="flex items-start justify-between gap-2">
          <span className="font-mono text-sm text-gray-200 group-hover:text-white transition-colors break-all pr-6">
            {repoShortName(repo.url)}
          </span>
          <span className="text-gray-600 group-hover:text-blue-400 transition-colors text-sm shrink-0">→</span>
        </div>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs px-2 py-0.5 rounded-full bg-dark-700 text-gray-400 border border-dark-600">
            {ownerLabel}
          </span>
          <span className="text-xs text-gray-600 font-mono">{repo.default_branch}</span>
        </div>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(repo); }}
        className="absolute top-3 right-8 opacity-0 group-hover:opacity-100 transition-opacity
                   text-gray-600 hover:text-red-400 text-xs px-1.5 py-0.5 rounded"
        title="Repoyu sil"
      >
        ✕
      </button>
    </div>
  );
}

function DeleteConfirmModal({ repo, onConfirm, onCancel, loading, error }) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-dark-900 border border-dark-600 rounded-lg w-full max-w-sm p-6 shadow-xl">
        <h2 className="text-base font-semibold text-gray-100 mb-2">Repoyu Sil</h2>
        <p className="text-sm text-gray-400 mb-1">
          Aşağıdaki repository silinecek:
        </p>
        <p className="font-mono text-sm text-gray-200 bg-dark-800 rounded px-3 py-2 mb-4 break-all">
          {repoShortName(repo.url)}
        </p>
        <p className="text-xs text-red-400 mb-4">
          Bu işlem geri alınamaz. İlişkili pipeline kayıtları korunur.
        </p>
        {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors disabled:opacity-50"
          >
            İptal
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm font-medium
                       px-4 py-2 rounded-md transition-colors"
          >
            {loading ? 'Siliniyor...' : 'Sil'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function RepositoriesPage() {
  const { teams } = useAuth();
  const navigate = useNavigate();
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const handleDeleteConfirm = async () => {
    setDeleteLoading(true);
    setDeleteError('');
    try {
      await deleteRepository(deleteTarget.id);
      setDeleteTarget(null);
      fetchRepos();
    } catch (err) {
      setDeleteError(formatApiError(err));
    } finally {
      setDeleteLoading(false);
    }
  };

  const fetchRepos = async () => {
    setLoading(true);
    try {
      const res = await getRepositories();
      setRepos(res.data.items ?? res.data);
      setError('');
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRepos(); }, []);

  const userRepos = repos.filter(r => r.owner_type === 'user');

  const teamGroups = teams
    .map(team => ({ team, repos: repos.filter(r => r.owner_type === 'team' && r.owner_id === team.id) }))
    .filter(g => g.repos.length > 0);

  const knownTeamIds = new Set(teams.map(t => t.id));
  const unknownTeamRepos = repos.filter(r => r.owner_type === 'team' && !knownTeamIds.has(r.owner_id));
  const unknownGroups = [...new Set(unknownTeamRepos.map(r => r.owner_id))].map(id => ({
    team: { id, name: 'Takım Repoları' },
    repos: unknownTeamRepos.filter(r => r.owner_id === id),
  }));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-100">Repositories</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {loading ? '...' : `${repos.length} repository`}
          </p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-md transition-colors"
        >
          + Yeni Repo Ekle
        </button>
      </div>

      {error && (
        <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-md px-4 py-3 mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : repos.length === 0 ? (
        <div className="bg-dark-900 border border-dark-600 rounded-lg py-16 text-center text-gray-500">
          Henüz kayıtlı repository yok. Webhook almak için bir repository ekleyin.
        </div>
      ) : (
        <div className="space-y-8">
          {userRepos.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Kişisel Repolarım
              </h2>
              <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                {userRepos.map(repo => (
                  <RepoCard key={repo.id} repo={repo} teamName="Kişisel"
                    onClick={() => navigate(`/repositories/${repo.id}`)}
                    onDelete={setDeleteTarget} />
                ))}
              </div>
            </section>
          )}
          {teamGroups.map(({ team, repos: tRepos }) => (
            <section key={team.id}>
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                {team.name} Repoları
              </h2>
              <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                {tRepos.map(repo => (
                  <RepoCard key={repo.id} repo={repo} teamName={team.name}
                    onClick={() => navigate(`/repositories/${repo.id}`)}
                    onDelete={setDeleteTarget} />
                ))}
              </div>
            </section>
          ))}
          {unknownGroups.map(({ team, repos: uRepos }) => (
            <section key={team.id}>
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                {team.name}
              </h2>
              <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                {uRepos.map(repo => (
                  <RepoCard key={repo.id} repo={repo} teamName="Takım"
                    onClick={() => navigate(`/repositories/${repo.id}`)}
                    onDelete={setDeleteTarget} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      {showAdd && (
        <AddRepoModal
          teams={teams}
          onSuccess={() => { setShowAdd(false); fetchRepos(); }}
          onClose={() => setShowAdd(false)}
        />
      )}

      {deleteTarget && (
        <DeleteConfirmModal
          repo={deleteTarget}
          onConfirm={handleDeleteConfirm}
          onCancel={() => { setDeleteTarget(null); setDeleteError(''); }}
          loading={deleteLoading}
          error={deleteError}
        />
      )}
    </div>
  );
}
