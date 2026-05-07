import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { formatApiError, registerUser } from '../services/api';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState('login'); // 'login' | 'register'
  const [form, setForm] = useState({ username: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const update = (field) => (e) => {
    setForm((p) => ({ ...p, [field]: e.target.value }));
    setError('');
  };

  const switchTab = (next) => {
    setTab(next);
    setForm({ username: '', password: '', confirm: '' });
    setError('');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!form.username.trim() || !form.password) {
      setError('Kullanıcı adı ve şifre zorunludur.');
      return;
    }
    setLoading(true);
    try {
      await login(form.username.trim(), form.password);
      navigate('/pipelines', { replace: true });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!form.username.trim() || !form.password) {
      setError('Kullanıcı adı ve şifre zorunludur.');
      return;
    }
    if (form.password.length < 6) {
      setError('Şifre en az 6 karakter olmalıdır.');
      return;
    }
    if (form.password !== form.confirm) {
      setError('Şifreler eşleşmiyor.');
      return;
    }
    setLoading(true);
    try {
      await registerUser(form.username.trim(), form.password);
      await login(form.username.trim(), form.password);
      navigate('/pipelines', { replace: true });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 text-2xl font-bold text-white">
            <span className="text-blue-400">⬡</span>
            <span>CI Dashboard</span>
          </div>
          <p className="text-gray-500 text-sm mt-1">Continuous Integration Otomasyon Sistemi</p>
        </div>

        <div className="bg-dark-900 border border-dark-600 rounded-lg overflow-hidden">
          {/* Sekmeler */}
          <div className="flex border-b border-dark-600">
            <button
              onClick={() => switchTab('login')}
              className={`flex-1 py-3 text-sm font-medium transition-colors ${
                tab === 'login'
                  ? 'text-white border-b-2 border-blue-500 bg-dark-800'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              Giriş Yap
            </button>
            <button
              onClick={() => switchTab('register')}
              className={`flex-1 py-3 text-sm font-medium transition-colors ${
                tab === 'register'
                  ? 'text-white border-b-2 border-blue-500 bg-dark-800'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              Kayıt Ol
            </button>
          </div>

          {/* Form */}
          <form
            onSubmit={tab === 'login' ? handleLogin : handleRegister}
            className="p-6 space-y-4"
          >
            {error && (
              <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-md px-3 py-2">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Kullanıcı Adı</label>
              <input
                type="text"
                autoComplete="username"
                value={form.username}
                onChange={update('username')}
                className="w-full bg-dark-800 border border-dark-600 text-gray-100 rounded-md px-3 py-2 text-sm
                           focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="kullanici_adi"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Şifre</label>
              <input
                type="password"
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                value={form.password}
                onChange={update('password')}
                className="w-full bg-dark-800 border border-dark-600 text-gray-100 rounded-md px-3 py-2 text-sm
                           focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="••••••••"
              />
            </div>

            {tab === 'register' && (
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Şifre Tekrar</label>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={form.confirm}
                  onChange={update('confirm')}
                  className="w-full bg-dark-800 border border-dark-600 text-gray-100 rounded-md px-3 py-2 text-sm
                             focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  placeholder="••••••••"
                />
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-900 disabled:cursor-not-allowed
                         text-white font-medium rounded-md py-2 text-sm transition-colors"
            >
              {loading
                ? tab === 'login' ? 'Giriş yapılıyor…' : 'Kayıt olunuyor…'
                : tab === 'login' ? 'Giriş Yap' : 'Kayıt Ol'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
