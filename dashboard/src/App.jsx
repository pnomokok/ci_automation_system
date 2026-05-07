import { BrowserRouter, Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import PipelineListPage from './components/PipelineListPage';
import PipelineDetailPage from './components/PipelineDetailPage';
import RepositoriesPage from './components/RepositoriesPage';
import TeamsPage from './components/TeamsPage';

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <nav className="bg-dark-900 border-b border-dark-600 h-14 flex items-center px-6 gap-6 sticky top-0 z-40">
      <Link to="/pipelines" className="flex items-center gap-2 text-white font-semibold text-base hover:text-blue-400 transition-colors">
        <span className="text-blue-400">⬡</span>
        <span>CI Dashboard</span>
      </Link>

      <div className="flex-1" />

      <Link
        to="/pipelines"
        className="text-sm text-gray-400 hover:text-gray-100 transition-colors"
      >
        Pipelines
      </Link>
      <Link
        to="/repositories"
        className="text-sm text-gray-400 hover:text-gray-100 transition-colors"
      >
        Repositories
      </Link>
      <Link
        to="/teams"
        className="text-sm text-gray-400 hover:text-gray-100 transition-colors"
      >
        Takımlar
      </Link>

      <div className="flex items-center gap-3 ml-4 border-l border-dark-600 pl-4">
        <span className="text-sm text-gray-500">
          {user?.username || 'Kullanıcı'}
        </span>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-red-400 transition-colors"
        >
          Çıkış
        </button>
      </div>
    </nav>
  );
}

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-dark-950">
      <Navbar />
      <main className="max-w-7xl mx-auto px-6 py-6">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/pipelines"
          element={
            <ProtectedRoute>
              <Layout><PipelineListPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/pipelines/:id"
          element={
            <ProtectedRoute>
              <Layout><PipelineDetailPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/repositories"
          element={
            <ProtectedRoute>
              <Layout><RepositoriesPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/teams"
          element={
            <ProtectedRoute>
              <Layout><TeamsPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/pipelines" replace />} />
        <Route path="*" element={<Navigate to="/pipelines" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
