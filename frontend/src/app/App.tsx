import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Toaster } from './components/ui/sonner';

// Public pages
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

// Client pages
import DashboardPage from './pages/client/DashboardPage';
import OrdersPage from './pages/client/OrdersPage';
import OrderDetailPage from './pages/client/OrderDetailPage';
import CheckoutPage from './pages/client/CheckoutPage';
import NewClaimPage from './pages/client/NewClaimPage';
import ClaimsListPage from './pages/client/ClaimsListPage';
import ClaimDetailPage from './pages/client/ClaimDetailPage';
import HelpCenterPage from './pages/client/HelpCenterPage';

// Admin pages
import AdminDashboardPage from './pages/admin/AdminDashboardPage';
import ClaimsBandejaPage from './pages/admin/ClaimsBandejaPage';
import AdminClaimDetailPage from './pages/admin/AdminClaimDetailPage';
import KnowledgeBasePage from './pages/admin/KnowledgeBasePage';
import AIConfigPage from './pages/admin/AIConfigPage';
import ReportsPage from './pages/admin/ReportsPage';

function ProtectedRoute({ children, adminOnly = false }: { children: React.ReactNode; adminOnly?: boolean }) {
  const { isAuthenticated, currentUser, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-600">
        Cargando sesión...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && currentUser?.role !== 'ADMIN' && currentUser?.role !== 'AGENT') {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Client routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/orders"
        element={
          <ProtectedRoute>
            <OrdersPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/orders/:id"
        element={
          <ProtectedRoute>
            <OrderDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/checkout"
        element={
          <ProtectedRoute>
            <CheckoutPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/claims/new"
        element={
          <ProtectedRoute>
            <NewClaimPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/claims"
        element={
          <ProtectedRoute>
            <ClaimsListPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/claims/:id"
        element={
          <ProtectedRoute>
            <ClaimDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/help"
        element={
          <ProtectedRoute>
            <HelpCenterPage />
          </ProtectedRoute>
        }
      />

      {/* Admin routes */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute adminOnly>
            <AdminDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/claims"
        element={
          <ProtectedRoute adminOnly>
            <ClaimsBandejaPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/claims/:id"
        element={
          <ProtectedRoute adminOnly>
            <AdminClaimDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/knowledge"
        element={
          <ProtectedRoute adminOnly>
            <KnowledgeBasePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/ai-config"
        element={
          <ProtectedRoute adminOnly>
            <AIConfigPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/reports"
        element={
          <ProtectedRoute adminOnly>
            <ReportsPage />
          </ProtectedRoute>
        }
      />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="size-full">
          <AppRoutes />
          <Toaster />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}
