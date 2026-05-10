import { useState } from 'react';
import { triggerPipeline, formatApiError } from '../../services/api';

export default function TriggerForm({ repoUrl, defaultBranch = 'main', onSuccess, onClose }) {
  const [form, setForm] = useState({ branch: defaultBranch });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState('');

  const validate = () => {
    const e = {};
    if (!form.branch.trim()) e.branch = 'Branch adı zorunludur.';
    return e;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError('');
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setLoading(true);
    try {
      const res = await triggerPipeline(repoUrl, form.branch.trim());
      onSuccess?.(res.data);
    } catch (err) {
      setApiError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      onClick={(e) => { if (e.target === e.currentTarget) onClose?.(); }}
    >
      <div className="bg-dark-900 border border-dark-600 rounded-lg w-full max-w-md mx-4 shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-dark-600">
          <h2 className="text-base font-semibold text-gray-100">Pipeline Tetikle</h2>
          <button onClick={onClose}
            className="text-gray-500 hover:text-gray-200 transition-colors text-lg leading-none">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {apiError && (
            <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-md px-3 py-2">
              {apiError}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Repository</label>
            <span className="block w-full bg-dark-800/50 border border-dark-600 text-gray-400 rounded-md px-3 py-2 text-sm font-mono break-all">
              {repoUrl}
            </span>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Branch <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={form.branch}
              onChange={(e) => setForm(p => ({ ...p, branch: e.target.value }))}
              placeholder="main"
              className={`w-full bg-dark-800 border text-gray-100 rounded-md px-3 py-2 text-sm font-mono
                         focus:outline-none focus:ring-1 focus:ring-blue-500
                         ${errors.branch ? 'border-red-600' : 'border-dark-600 focus:border-blue-500'}`}
            />
            {errors.branch && <p className="text-red-400 text-xs mt-1">{errors.branch}</p>}
          </div>

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="flex-1 bg-dark-800 hover:bg-dark-700 border border-dark-600 text-gray-300
                         rounded-md py-2 text-sm transition-colors">
              İptal
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-900 disabled:cursor-not-allowed
                         text-white font-medium rounded-md py-2 text-sm transition-colors">
              {loading ? 'Tetikleniyor…' : 'Pipeline Başlat'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
