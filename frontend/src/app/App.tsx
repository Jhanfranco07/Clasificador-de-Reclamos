import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation } from 'react-router';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Toaster } from './components/ui/sonner';
import ChatbotWidget from './components/ChatbotWidget';
import ClientLayout from './components/ClientLayout';
import { ThemeProvider } from 'next-themes';

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
const RestaurantPage = lazy(() => import('./pages/catalog/RestaurantPage'));
const CartPage = lazy(() => import('./pages/catalog/CartPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));

function ProtectedRoute({
  children,
  allowedRoles,
}: {
  children?: React.ReactNode;
  allowedRoles?: Array<'CLIENT' | 'AGENT' | 'ADMIN'>;
}) {
  const { isAuthenticated, currentUser, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-600">
        Cargando sesión...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }

  if (allowedRoles && currentUser && !allowedRoles.includes(currentUser.role)) {
    return <Navigate to={currentUser.role === 'CLIENT' ? '/dashboard' : '/admin'} replace />;
  }

  return <>{children ?? <Outlet />}</>;
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
      <Route element={<ProtectedRoute />}>
        <Route element={<ClientLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/restaurants" element={<LandingPage internal />} />
          <Route path="/restaurants/:id" element={<RestaurantPage />} />
          <Route path="/products" element={<LandingPage internal />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/orders/:id" element={<OrderDetailPage />} />
          <Route path="/claims" element={<ClaimsListPage />} />
          <Route path="/claims/new" element={<NewClaimPage />} />
          <Route path="/claims/:id" element={<ClaimDetailPage />} />
          <Route path="/help" element={<HelpCenterPage />} />
          <Route path="/notifications" element={<Navigate to="/claims" replace />} />
        </Route>
      </Route>

      {/* Admin routes */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={['AGENT', 'ADMIN']}>
            <AdminDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route path="/admin/dashboard" element={<Navigate to="/admin" replace />} />
      <Route path="/admin/documents" element={<Navigate to="/admin/knowledge" replace />} />
      <Route path="/admin/settings" element={<Navigate to="/admin/ai-config" replace />} />
      <Route
        path="/admin/claims"
        element={
          <ProtectedRoute allowedRoles={['AGENT', 'ADMIN']}>
            <ClaimsBandejaPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/claims/:id"
        element={
          <ProtectedRoute allowedRoles={['AGENT', 'ADMIN']}>
            <AdminClaimDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/knowledge"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <KnowledgeBasePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/ai-config"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <AIConfigPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/reports"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <ReportsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/profile"
        element={
          <ProtectedRoute allowedRoles={['AGENT', 'ADMIN']}>
            <ProfilePage />
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
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      <AuthProvider>
        <BrowserRouter>
          <div className="size-full">
            <AppRoutes />
            <Toaster />
            <ChatbotWidget />
          </div>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
