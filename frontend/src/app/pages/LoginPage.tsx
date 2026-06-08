import { useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Package, AlertCircle, ShieldCheck, Sparkles } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Alert, AlertDescription } from '../components/ui/alert';
import { requestPasswordReset } from '../lib/api';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setInfo('');
    setLoading(true);

    const user = await login(email, password);

    if (user) {
      const requestedPath = (location.state as { from?: string } | null)?.from;
      const destination = user.role === 'CLIENT'
        ? requestedPath && !requestedPath.startsWith('/admin') ? requestedPath : '/dashboard'
        : requestedPath?.startsWith('/admin') ? requestedPath : '/admin';
      navigate(destination, { replace: true });
    } else {
      setError('Correo o contraseña incorrectos. Verifica tus datos e inténtalo nuevamente.');
    }

    setLoading(false);
  };

  const handlePasswordReset = async () => {
    setError('');
    setInfo('');
    if (!email.trim()) {
      setError('Ingresa tu correo para simular la recuperación.');
      return;
    }
    try {
      const result = await requestPasswordReset(email.trim());
      setInfo(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo solicitar la recuperación.');
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,#fff7ed,transparent_32%),linear-gradient(135deg,#ffffff_0%,#f8fafc_45%,#eff6ff_100%)] dark:bg-[radial-gradient(circle_at_top_left,rgba(249,115,22,0.12),transparent_32%),linear-gradient(135deg,#0f172a_0%,#111827_55%,#0f172a_100%)] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-4">
            <span className="flex size-12 items-center justify-center rounded-2xl bg-orange-500 text-white shadow-lg shadow-orange-500/20">
              <Package className="size-7" />
            </span>
            <span className="font-bold text-3xl">SmartClaim AI</span>
          </Link>
          <div className="mx-auto flex w-fit items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground shadow-sm">
            <ShieldCheck className="size-3.5 text-green-600" />
            Acceso seguro por rol
          </div>
        </div>

        <Card className="border-white/80 shadow-2xl shadow-slate-200/70">
          <CardHeader>
            <div className="mb-2 flex size-10 items-center justify-center rounded-xl bg-slate-900 text-white">
              <Sparkles className="size-5" />
            </div>
            <CardTitle className="text-2xl">Iniciar sesión</CardTitle>
            <CardDescription>
              Accede a tu cuenta para gestionar pedidos y reclamos
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="size-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              {info && (
                <Alert>
                  <AlertCircle className="size-4" />
                  <AlertDescription>{info}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="tu@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Contraseña</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Iniciando sesión...' : 'Iniciar sesión'}
              </Button>

              <div className="text-sm text-center">
                <button type="button" onClick={handlePasswordReset} className="text-orange-600 hover:underline">
                  ¿Olvidaste tu contraseña?
                </button>
              </div>

              <div className="text-center text-sm text-gray-600">
                ¿No tienes cuenta?{' '}
                <Link to="/register" className="text-orange-600 hover:underline font-semibold">
                  Regístrate
                </Link>
              </div>
            </form>

          </CardContent>
        </Card>

        <div className="text-center mt-6">
          <Link to="/" className="text-sm text-gray-600 hover:text-gray-900">
            ← Volver al inicio
          </Link>
        </div>
      </div>
    </div>
  );
}
