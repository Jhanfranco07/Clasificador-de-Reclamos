import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { ArrowLeft, CheckCircle } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { ClaimCategory, CLAIM_CATEGORY_LABELS } from '../../types';
import { ApiOrder, createClaim, listOrders } from '../../lib/api';
import ClientLayout from '../../components/ClientLayout';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';

export default function NewClaimPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { currentUser } = useAuth();
  const [orders, setOrders] = useState<ApiOrder[]>([]);

  const [orderId, setOrderId] = useState(searchParams.get('orderId') || '');
  const [category, setCategory] = useState<ClaimCategory | ''>('');
  const [description, setDescription] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);
  const [claimCode, setClaimCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const orderIdFromParams = searchParams.get('orderId');
    if (orderIdFromParams) {
      setOrderId(orderIdFromParams);
    }
  }, [searchParams]);

  useEffect(() => {
    listOrders()
      .then((data) => setOrders(data.items))
      .catch(() => setOrders([]));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const order = orders.find((item) => item.id === orderId);
    if (!currentUser || !order) {
      setError('Selecciona un pedido válido para registrar el reclamo.');
      return;
    }

    if (!category) {
      setError('Selecciona el tipo de problema.');
      return;
    }

    if (description.trim().length < 10) {
      setError('Cuéntanos un poco más para poder revisar tu caso.');
      return;
    }

    try {
      setIsSubmitting(true);
      const result = await createClaim({
        customer_name: currentUser.name,
        customer_email: currentUser.email,
        customer_phone: currentUser.phone,
        order_code: order.code,
        channel: 'WEB',
        order_date: order.createdAt,
        description: `${CLAIM_CATEGORY_LABELS[category]}: ${description.trim()}`,
        analyze: true,
      });
      setClaimCode(result.claim.code);
      setShowSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo registrar el reclamo. Inténtalo nuevamente.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCloseSuccess = () => {
    setShowSuccess(false);
    navigate('/claims');
  };

  return (
    <ClientLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center gap-4">
          <Link to="/dashboard">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="size-4 mr-2" />
              Volver
            </Button>
          </Link>
        </div>

        <div>
          <h1 className="text-3xl font-bold mb-2">Reportar problema con un pedido</h1>
          <p className="text-gray-600">
            Selecciona el pedido afectado y cuéntanos qué ocurrió. Usaremos esa información para darte seguimiento desde tu cuenta.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Información del reclamo</CardTitle>
            <CardDescription>
              Selecciona el pedido relacionado y describe el inconveniente con el mayor detalle posible.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="order">Pedido relacionado *</Label>
                <Select value={orderId} onValueChange={setOrderId} required>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecciona un pedido" />
                  </SelectTrigger>
                  <SelectContent>
                    {orders.map((order) => (
                      <SelectItem key={order.id} value={order.id}>
                        {order.code} - {order.storeName}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-sm text-gray-500">
                  Elige el pedido donde ocurrió el problema.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="category">Tipo de problema *</Label>
                <Select value={category} onValueChange={(value) => setCategory(value as ClaimCategory)} required>
                  <SelectTrigger>
                    <SelectValue placeholder="¿Qué tipo de problema tienes?" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(CLAIM_CATEGORY_LABELS).map(([key, label]) => (
                      <SelectItem key={key} value={key}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Descripción del problema *</Label>
                <Textarea
                  id="description"
                  placeholder="Describe qué sucedió, cuándo ocurrió y qué esperas como solución..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                  rows={6}
                  className="resize-none"
                />
                <p className="text-sm text-gray-500">
                  Incluye productos afectados, cobros, tiempos de espera o cualquier detalle útil.
                </p>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="font-semibold text-blue-900 mb-2">Seguimiento del caso</h4>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>Recibirás un código de reclamo para consultar el avance.</li>
                  <li>Soporte revisará el pedido, el tipo de problema y los detalles enviados.</li>
                  <li>Los casos de pago, seguridad o prioridad alta pasan a revisión de un agente.</li>
                  <li>Podrás ver la respuesta desde Mis reclamos cuando el caso sea atendido.</li>
                </ul>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">
                  {error}
                </div>
              )}

              <div className="flex gap-3">
                <Button
                  type="submit"
                  className="flex-1"
                  disabled={!orderId || !category || description.trim().length < 10 || isSubmitting}
                >
                  {isSubmitting ? 'Enviando...' : 'Enviar reclamo'}
                </Button>
                <Link to="/dashboard">
                  <Button type="button" variant="outline">
                    Cancelar
                  </Button>
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>

        <Dialog open={showSuccess} onOpenChange={setShowSuccess}>
          <DialogContent>
            <DialogHeader>
              <div className="flex flex-col items-center text-center">
                <div className="size-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                  <CheckCircle className="size-8 text-green-600" />
                </div>
                <DialogTitle className="text-2xl">Reclamo recibido</DialogTitle>
                <DialogDescription className="mt-2">
                  Tu caso fue registrado correctamente y queda en revisión por soporte.
                </DialogDescription>
              </div>
            </DialogHeader>
            <div className="space-y-4">
              <div className="bg-gray-50 p-4 rounded-lg text-center">
                <p className="text-sm text-gray-600 mb-1">Código de reclamo</p>
                <p className="text-2xl font-bold text-orange-600">{claimCode}</p>
              </div>
              <div className="flex gap-3">
                <Button onClick={handleCloseSuccess} className="flex-1">
                  Ver mis reclamos
                </Button>
                <Link to="/dashboard">
                  <Button variant="outline">Ir al inicio</Button>
                </Link>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </ClientLayout>
  );
}
