import { useEffect, useState } from 'react';
import { createRepository, deleteRepository, formatApiError, getRepositories } from '../../services/api';

function AddRepoModal({ onSuccess, onClose }) {
  const [form, setForm] = useState({ url: '', default_branch: 'main', webhook_secret: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.url.trim()) { setError('Repository URL zorunludur.'); return; }
    try { new URL(form.url); } catch { setError('Geçerli bir URL girin.'); return; }
    if (!form.webhook_secret.trim()) { setError('Webhook secret zorunludur.'); return; }

    setLoading(true);
    setError('');
    try {
      const res = await createRepository({
        url: form.url.trim(),
        default_branch: form.default_branch.trim() || 'main',
        webhook_secret: form.webhook_secret.trim(),
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
              onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
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
              onChange={(e) => setForm((f) => ({ ...f, default_branch: e.target.value }))}
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
              onChange={(e) => setForm((f) => ({ ...f, webhook_secret: e.target.value }))}
              className="w-full bg-dark-800 border border-dark-600 text-gray-200 text-sm rounded-md px-3 py-2
                         focus:outline-none focus:border-blue-500"
            />
          </div>

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          <div className="flex gap-3 justify-end mt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              İptal
            </button>
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium
                         px-4 py-2 rounded-md transition-colors"
            >
              {loading ? 'Ekleniyor...' : 'Ekle'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function RepositoriesPage() {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const fetchRepos = async () => {
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

  const handleDelete = async (id) => {
    if (!window.confirm('Bu repository silinsin mi?')) return;
    setDeletingId(id);
    try {
      await deleteRepository(id);
      setRepos((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-gray-100">Repositories</h1>
          <p className="text-sm text-gray-500 mt-0.5">{repos.length} kayıtlı repository</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-md transition-colors"
        >
          + Repository Ekle
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
        <div className="bg-dark-900 border border-dark-600 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-600 text-gray-500 text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3">URL</th>
                <th className="text-left px-4 py-3">Varsayılan Branch</th>
                <th className="text-left px-4 py-3">Eklenme Tarihi</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {repos.map((repo, i) => (
                <tr
                  key={repo.id}
                  className={`border-b border-dark-700 ${i === repos.length - 1 ? 'border-b-0' : ''}`}
                >
                  <td className="px-4 py-3 font-mono text-xs text-gray-200">{repo.url}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{repo.default_branch}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {repo.created_at ? new Date(repo.created_at).toLocaleString('tr-TR') : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(repo.id)}
                      disabled={deletingId === repo.id}
                      className="text-xs text-red-500 hover:text-red-400 disabled:opacity-40 transition-colors"
                    >
                      {deletingId === repo.id ? 'Siliniyor...' : 'Sil'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAdd && (
        <AddRepoModal
          onSuccess={() => { setShowAdd(false); fetchRepos(); }}
          onClose={() => setShowAdd(false)}
        />
      )}
    </div>
  );
}
