import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  addTeamMember, createTeam, formatApiError,
  getTeamMembers, getTeams, removeTeamMember,
} from '../../services/api';
import { useAuth } from '../../context/AuthContext';

// ── Takım oluşturma modal'ı ──────────────────────────────────────────────────

function CreateTeamModal({ onSuccess, onClose }) {
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) { setError('Takım adı zorunludur.'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await createTeam(name.trim());
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
        <h2 className="text-base font-semibold text-gray-100 mb-4">Yeni Takım Oluştur</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Takım Adı</label>
            <input
              type="text"
              autoFocus
              placeholder="orn. alpha-team"
              value={name}
              onChange={(e) => { setName(e.target.value); setError(''); }}
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
              {loading ? 'Oluşturuluyor...' : 'Oluştur'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Ana sayfa ────────────────────────────────────────────────────────────────

export default function TeamsPage() {
  const navigate = useNavigate();
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);

  const fetchTeams = async () => {
    setLoading(true);
    try {
      const res = await getTeams();
      setTeams(res.data);
      setError('');
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTeams(); }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-gray-100">Takımlar</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {loading ? '...' : `${teams.length} takım`}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-md transition-colors"
        >
          + Yeni Takım
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
      ) : teams.length === 0 ? (
        <div className="bg-dark-900 border border-dark-600 rounded-lg py-16 text-center text-gray-500">
          Henüz bir takıma dahil değilsin. Yeni bir takım oluşturabilirsin.
        </div>
      ) : (
        <div className="bg-dark-900 border border-dark-600 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-600 text-gray-500 text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3">Takım Adı</th>
                <th className="text-left px-4 py-3">Oluşturulma</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {teams.map((team, i) => (
                <tr
                  key={team.id}
                  onClick={() => navigate(`/teams/${team.id}`)}
                  className={`border-b border-dark-700 hover:bg-dark-800 transition-colors cursor-pointer ${
                    i === teams.length - 1 ? 'border-b-0' : ''
                  }`}
                >
                  <td className="px-4 py-3 font-medium text-gray-200">{team.name}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {team.created_at ? new Date(team.created_at).toLocaleString('tr-TR') : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-xs text-blue-400 hover:text-blue-300">Detay →</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateTeamModal
          onSuccess={() => { setShowCreate(false); fetchTeams(); }}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  );
}
