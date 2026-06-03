import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Toaster } from './components/ui/sonner';

const LandingPage = lazy(() => import('./pages/LandingPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const DashboardPage = lazy(() => import('./pages/client/DashboardPage'));
const OrdersPage = lazy(() => import('./pages/client/OrdersPage'));
const OrderDetailPage = lazy(() => import('./pages/client/OrderDetailPage'));
const CheckoutPage = lazy(() => import('./pages/client/CheckoutPage'));
const NewClaimPage = lazy(() => import('./pages/client/NewClaimPage'));
const ClaimsListPage = lazy(() => import('./pages/client/ClaimsListPage'));
const ClaimDetailPage = lazy(() => import('./pages/client/ClaimDetailPage'));
const HelpCenterPage = lazy(() => import('./pages/client/HelpCenterPage'));
const AdminDashboardPage = lazy(() => import('./pages/admin/AdminDashboardPage'));
const ClaimsBandejaPage = lazy(() => import('./pages/admin/ClaimsBandejaPage'));
const AdminClaimDetailPage = lazy(() => import('./pages/admin/AdminClaimDetailPage'));
const KnowledgeBasePage = lazy(() => import('./pages/admin/KnowledgeBasePage'));
const AIConfigPage = lazy(() => import('./pages/admin/AIConfigPage'));
const ReportsPage = lazy(() => import('./pages/admin/ReportsPage'));

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
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-gray-600">Cargando modulo...</div>}>
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
    </Suspense>
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
