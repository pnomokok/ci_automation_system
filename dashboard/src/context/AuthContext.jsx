import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { decodeToken, getTeams, loginUser } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('access_token'));
  const [user, setUser] = useState(() => {
    const t = localStorage.getItem('access_token');
    return t ? decodeToken(t) : null;
  });
  const [teams, setTeams] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const isAuthenticated = Boolean(token);

  const login = useCallback(async (username, password) => {
    setIsLoading(true);
    try {
      const res = await loginUser(username, password);
      const { access_token } = res.data;
      localStorage.setItem('access_token', access_token);
      setToken(access_token);
      setUser(decodeToken(access_token));
      try {
        const teamsRes = await getTeams();
        setTeams(teamsRes.data ?? []);
      } catch {
        // teams boş kalır, login akışını bozma
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    setToken(null);
    setUser(null);
    setTeams([]);
  }, []);

  // Proactive expiry check: logout when JWT exp is reached
  useEffect(() => {
    if (!token) return;
    const payload = decodeToken(token);
    if (!payload?.exp) return;
    const msUntilExpiry = payload.exp * 1000 - Date.now();
    if (msUntilExpiry <= 0) { logout(); return; }
    const t = setTimeout(logout, msUntilExpiry);
    return () => clearTimeout(t);
  }, [token, logout]);

  return (
    <AuthContext.Provider value={{ token, user, teams, isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
