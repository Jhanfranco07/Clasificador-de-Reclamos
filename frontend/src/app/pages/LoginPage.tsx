import { useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Package, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Alert, AlertDescription } from '../components/ui/alert';
import { requestPasswordReset } from '../lib/api';

const CART_KEY = 'smartclaim_pending_cart';

export default function LoginPage() {
  const navigate = useNavigate();
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

    const success = await login(email, password);

    if (success) {
      const hasPendingCart = Boolean(window.localStorage.getItem(CART_KEY));
      if (hasPendingCart && !email.includes('@smartclaim.com')) {
        navigate('/checkout');
      } else if (email.includes('@smartclaim.com')) {
        navigate('/admin');
      } else {
        navigate('/dashboard');
      }
    } else {
      setError('Credenciales incorrectas. Usa uno de los accesos de prueba disponibles.');
    }

    setLoading(false);
  };

  const fillAccess = (accessEmail: string) => {
    setEmail(accessEmail);
    setPassword('123456');
    setError('');
    setInfo('');
  };

  const handlePasswordReset = async () => {
    setError('');
    setInfo('');
    if (!email.trim()) {
      setError('Ingresa tu correo para simular la recuperacion.');
      return;
    }
    try {
      const result = await requestPasswordReset(email.trim());
      setInfo(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo solicitar la recuperacion.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-blue-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-4">
            <Package className="size-10 text-orange-500" />
            <span className="font-bold text-3xl">SmartClaim AI</span>
          </Link>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">Iniciar sesiÃ³n</CardTitle>
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
                <Label htmlFor="password">ContraseÃ±a</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Iniciando sesiÃ³n...' : 'Iniciar sesiÃ³n'}
              </Button>

              <div className="text-sm text-center">
                <button type="button" onClick={handlePasswordReset} className="text-orange-600 hover:underline">
                  Â¿Olvidaste tu contraseÃ±a?
                </button>
              </div>

              <div className="text-center text-sm text-gray-600">
                Â¿No tienes cuenta?{' '}
                <Link to="/register" className="text-orange-600 hover:underline font-semibold">
                  RegÃ­strate
                </Link>
              </div>
            </form>

            <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-xs font-semibold text-blue-900 mb-3">Accesos de prueba</p>
              <div className="grid gap-2">
                <Button variant="outline" size="sm" onClick={() => fillAccess('maria.gonzalez@email.com')}>
                  Entrar como cliente
                </Button>
                <Button variant="outline" size="sm" onClick={() => fillAccess('laura.martinez@smartclaim.com')}>
                  Entrar como agente
                </Button>
                <Button variant="outline" size="sm" onClick={() => fillAccess('admin@smartclaim.com')}>
                  Entrar como admin
                </Button>
              </div>
              <p className="text-xs text-blue-700 mt-3">
                En esta versiÃ³n puedes usar cualquier contraseÃ±a.
              </p>
            </div>
          </CardContent>
        </Card>

        <div className="text-center mt-6">
          <Link to="/" className="text-sm text-gray-600 hover:text-gray-900">
            â† Volver al inicio
          </Link>
        </div>
      </div>
    </div>
  );
}

