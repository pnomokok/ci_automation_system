import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createRepository, deleteRepository, formatApiError, getPipelines, getRepositories, updateRepository } from '../../services/api';

function repoShortName(url) {
  return url?.replace(/^https?:\/\/github\.com\//, '') || url || '—';
}

const CI_CONFIG_TEMPLATE = `runtime: python
image: python:3.11-slim
steps:
  install:
    command: pip install -r requirements.txt
    timeout: 120
    network: bridge
  build:
    command: echo "build ok"
    timeout: 60
    network: none
  test:
    command: pytest tests/ -v
    timeout: 300
    network: none
branches:
  - main
  - develop
`;

const TEST_TEMPLATE = `def test_example():
    # Bu testi kendi test senaryolarınla değiştir
    assert True
`;

function extractGithubPath(url) {
  const match = url.trim().replace(/\.git$/, '').match(/github\.com\/([^/]+)\/([^/]+)/);
  return match ? { owner: match[1], repo: match[2] } : null;
}

async function hasCiConfig(url, branch) {
  const parts = extractGithubPath(url);
  if (!parts) return true;
  try {
    const res = await fetch(
      `https://api.github.com/repos/${parts.owner}/${parts.repo}/contents/ci-config.yaml?ref=${branch}`,
      { headers: { Accept: 'application/vnd.github.v3+json' } }
    );
    return res.ok;
  } catch {
    return true;
  }
}

async function hasTestFiles(url, branch) {
  const parts = extractGithubPath(url);
  if (!parts) return true;
  try {
    const check = (path) => fetch(
      `https://api.github.com/repos/${parts.owner}/${parts.repo}/contents/${path}?ref=${branch}`,
      { headers: { Accept: 'application/vnd.github.v3+json' } }
    ).then(r => r.ok).catch(() => false);
    const [hasTests, hasTest] = await Promise.all([check('tests'), check('test')]);
    return hasTests || hasTest;
  } catch {
    return true;
  }
}

function CopyableTemplate({ content }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="relative">
      <pre className="bg-dark-800 border border-dark-600 rounded-md px-4 py-3 text-xs text-gray-300 font-mono overflow-x-auto whitespace-pre">
        {content}
      </pre>
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 bg-dark-700 hover:bg-dark-600 border border-dark-500
                   text-gray-400 hover:text-gray-200 text-xs px-2 py-1 rounded transition-colors"
      >
        {copied ? 'Kopyalandı!' : 'Kopyala'}
      </button>
    </div>
  );
}

function PostAddWarningStep({ missingCiConfig, missingTests, onClose }) {
  const both = missingCiConfig && missingTests;
  const [activeTab, setActiveTab] = useState(missingCiConfig ? 'ci-config' : 'tests');

  return (
    <div className="flex flex-col gap-4">
      {both && (
        <div className="flex gap-1 border-b border-dark-600">
          {[{ id: 'ci-config', label: 'ci-config.yaml' }, { id: 'tests', label: 'tests/' }].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === tab.id
                  ? 'text-white border-yellow-500'
                  : 'text-gray-500 hover:text-gray-300 border-transparent'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {(!both || activeTab === 'ci-config') && missingCiConfig && (
        <div className="flex flex-col gap-3">
          <div className="flex items-start gap-3 bg-yellow-950/50 border border-yellow-800/60 rounded-md px-4 py-3">
            <span className="text-yellow-400 text-base mt-0.5">⚠</span>
            <div>
              <p className="text-yellow-300 text-sm font-medium">ci-config.yaml bulunamadı</p>
              <p className="text-yellow-500 text-xs mt-0.5">
                Pipeline'ların çalışabilmesi için bu dosyanın repoya eklenmesi gerekiyor.
              </p>
            </div>
          </div>
          <CopyableTemplate content={CI_CONFIG_TEMPLATE} />
        </div>
      )}

      {(!both || activeTab === 'tests') && missingTests && (
        <div className="flex flex-col gap-3">
          <div className="flex items-start gap-3 bg-yellow-950/50 border border-yellow-800/60 rounded-md px-4 py-3">
            <span className="text-yellow-400 text-base mt-0.5">⚠</span>
            <div>
              <p className="text-yellow-300 text-sm font-medium">Test dosyaları bulunamadı</p>
              <p className="text-yellow-500 text-xs mt-0.5">
                <code className="font-mono bg-dark-800 px-1 rounded">tests/</code> klasörü
                bulunamadı. Test adımı çalışır ancak sonuçlar raporlanamaz. Aşağıdaki örneği{' '}
                <code className="font-mono bg-dark-800 px-1 rounded">tests/test_example.py</code>{' '}
                olarak ekle.
              </p>
            </div>
          </div>
          <CopyableTemplate content={TEST_TEMPLATE} />
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={onClose}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-md transition-colors"
        >
          Tamam
        </button>
      </div>
    </div>
  );
}

function AddRepoModal({ onSuccess, onClose }) {
  const [form, setForm] = useState({ url: '', default_branch: 'main', webhook_secret: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showWarningStep, setShowWarningStep] = useState(false);
  const [missingCiConfig, setMissingCiConfig] = useState(false);
  const [missingTests, setMissingTests] = useState(false);
  const [addedRepo, setAddedRepo] = useState(null);

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
      });
      setAddedRepo(res.data);
      const branch = form.default_branch.trim() || 'main';
      const url = form.url.trim();
      const [ciExists, testsExist] = await Promise.all([
        hasCiConfig(url, branch),
        hasTestFiles(url, branch),
      ]);
      if (!ciExists || !testsExist) {
        setMissingCiConfig(!ciExists);
        setMissingTests(!testsExist);
        setShowWarningStep(true);
      } else {
        onSuccess(res.data);
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleWarningClose = () => {
    setShowWarningStep(false);
    onSuccess(addedRepo);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-dark-900 border border-dark-600 rounded-lg w-full max-w-lg p-6 shadow-xl">
        {showWarningStep ? (
          <>
            <h2 className="text-base font-semibold text-gray-100 mb-4">Repository Eklendi</h2>
            <PostAddWarningStep
              missingCiConfig={missingCiConfig}
              missingTests={missingTests}
              onClose={handleWarningClose}
            />
          </>
        ) : (
          <>
            <h2 className="text-base font-semibold text-gray-100 mb-1">Yeni Repository Ekle</h2>
            <p className="text-xs text-gray-500 mb-4">Bu repoyu ekleyen kişi otomatik olarak owner olur.</p>
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

              {error && <p className="text-red-400 text-sm">{error}</p>}

              <div className="flex gap-3 justify-end mt-2">
                <button type="button" onClick={onClose}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors">
                  İptal
                </button>
                <button type="submit" disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium
                             px-4 py-2 rounded-md transition-colors">
                  {loading ? 'Kontrol ediliyor...' : 'Ekle'}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
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

function RepoCard({ repo, pipelineCount, onClick, onEdit, onDelete }) {
  const isOwner = repo.my_role === 'owner';
  return (
    <div
      className="bg-dark-900 border border-dark-600 rounded-lg p-4 hover:border-blue-500/50 hover:bg-dark-800
                 transition-all group relative"
    >
      <div onClick={onClick} className="cursor-pointer">
        <div className="flex items-start justify-between gap-2">
          <span className="font-mono text-sm text-gray-200 group-hover:text-white transition-colors break-all pr-6">
            {repoShortName(repo.url)}
          </span>
          {/* Owner: ok hover'da kaybolur, butonlar onun yerine gelir */}
          <span className={`transition-opacity text-sm shrink-0 ${
            isOwner
              ? 'text-gray-600 group-hover:opacity-0'
              : 'text-gray-600 group-hover:text-blue-400'
          }`}>→</span>
        </div>
        <div className="mt-2 flex items-center gap-2 flex-wrap">
          <RoleBadge role={repo.my_role} />
          <span className="text-xs text-gray-600 font-mono">{repo.default_branch}</span>
          {pipelineCount !== undefined && (
            <span className="text-xs text-gray-600 font-mono">{pipelineCount} pipeline</span>
          )}
        </div>
      </div>
      {isOwner && (
        <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => { e.stopPropagation(); onEdit(repo); }}
            className="text-gray-500 hover:text-blue-400 text-sm px-1 py-0.5 rounded transition-colors"
            title="Repoyu düzenle"
          >
            ✎
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(repo); }}
            className="text-gray-500 hover:text-red-400 text-sm px-1 py-0.5 rounded transition-colors"
            title="Repoyu sil"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}

function EditRepoModal({ repo, onSuccess, onClose }) {
  const [form, setForm] = useState({ default_branch: repo.default_branch, webhook_secret: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const patch = {};
    if (form.default_branch.trim() && form.default_branch.trim() !== repo.default_branch) {
      patch.default_branch = form.default_branch.trim();
    }
    if (form.webhook_secret.trim()) {
      patch.webhook_secret = form.webhook_secret.trim();
    }
    if (Object.keys(patch).length === 0) { onClose(); return; }
    setLoading(true);
    setError('');
    try {
      const res = await updateRepository(repo.id, patch);
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
        <h2 className="text-base font-semibold text-gray-100 mb-1">Repoyu Düzenle</h2>
        <p className="text-xs text-gray-500 mb-4 font-mono break-all">{repoShortName(repo.url)}</p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Varsayılan Branch</label>
            <input
              type="text"
              value={form.default_branch}
              onChange={(e) => setForm(f => ({ ...f, default_branch: e.target.value }))}
              className="w-full bg-dark-800 border border-dark-600 text-gray-200 text-sm rounded-md px-3 py-2
                         focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              Yeni Webhook Secret{' '}
              <span className="text-gray-600">(boş bırakılırsa değişmez)</span>
            </label>
            <input
              type="password"
              placeholder="Yeni gizli anahtar"
              value={form.webhook_secret}
              onChange={(e) => setForm(f => ({ ...f, webhook_secret: e.target.value }))}
              className="w-full bg-dark-800 border border-dark-600 text-gray-200 text-sm rounded-md px-3 py-2
                         focus:outline-none focus:border-blue-500"
            />
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
              {loading ? 'Kaydediliyor...' : 'Kaydet'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DeleteConfirmModal({ repo, onConfirm, onCancel, loading, error }) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-dark-900 border border-dark-600 rounded-lg w-full max-w-sm p-6 shadow-xl">
        <h2 className="text-base font-semibold text-gray-100 mb-2">Repoyu Sil</h2>
        <p className="text-sm text-gray-400 mb-1">Aşağıdaki repository silinecek:</p>
        <p className="font-mono text-sm text-gray-200 bg-dark-800 rounded px-3 py-2 mb-4 break-all">
          {repoShortName(repo.url)}
        </p>
        <p className="text-xs text-red-400 mb-4">
          Bu işlem geri alınamaz. Pipeline'lar ve tüm üyelikler de silinir.
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
  const navigate = useNavigate();
  const [repos, setRepos] = useState([]);
  const [pipelineCounts, setPipelineCounts] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
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
      const list = res.data.items ?? res.data;
      setRepos(list);
      setError('');
      const counts = await Promise.all(
        list.map(r => getPipelines({ repo_id: r.id, page_size: 1 }).then(r2 => [r.id, r2.data.total]).catch(() => [r.id, 0]))
      );
      setPipelineCounts(Object.fromEntries(counts));
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRepos(); }, []);

  const ownedRepos = repos.filter(r => r.my_role === 'owner');
  const memberRepos = repos.filter(r => r.my_role === 'member');

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
          Henüz hiçbir reponun üyesi değilsiniz. Yeni bir repo ekleyin veya bir owner sizi kendi reposuna eklesin.
        </div>
      ) : (
        <div className="space-y-8">
          {ownedRepos.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Sahip Olduğum Repolar
              </h2>
              <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                {ownedRepos.map(repo => (
                  <RepoCard key={repo.id} repo={repo}
                    pipelineCount={pipelineCounts[repo.id]}
                    onClick={() => navigate(`/repositories/${repo.id}`)}
                    onEdit={setEditTarget}
                    onDelete={setDeleteTarget} />
                ))}
              </div>
            </section>
          )}
          {memberRepos.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Üye Olduğum Repolar
              </h2>
              <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                {memberRepos.map(repo => (
                  <RepoCard key={repo.id} repo={repo}
                    pipelineCount={pipelineCounts[repo.id]}
                    onClick={() => navigate(`/repositories/${repo.id}`)}
                    onEdit={setEditTarget}
                    onDelete={setDeleteTarget} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {showAdd && (
        <AddRepoModal
          onSuccess={() => { setShowAdd(false); fetchRepos(); }}
          onClose={() => setShowAdd(false)}
        />
      )}

      {editTarget && (
        <EditRepoModal
          repo={editTarget}
          onSuccess={(updatedRepo) => {
            setRepos(rs => rs.map(r => r.id === updatedRepo.id ? { ...r, ...updatedRepo } : r));
            setEditTarget(null);
          }}
          onClose={() => setEditTarget(null)}
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
