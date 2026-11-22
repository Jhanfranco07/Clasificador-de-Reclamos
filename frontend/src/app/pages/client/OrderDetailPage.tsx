import { useEffect, useState } from 'react';
import OrderHistory from '../../components/OrderHistory';
import { useParams, Link } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Separator } from '../../components/ui/separator';
import { ArrowLeft, MapPin, CreditCard, User, AlertCircle } from 'lucide-react';
import { ORDER_STATUS_LABELS } from '../../types';
import { formatCurrency, formatDateTime } from '../../lib/utils';
import { ApiOrder, getOrder } from '../../lib/api';
import ClientLayout from '../../components/ClientLayout';

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [order, setOrder] = useState<ApiOrder | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    let active = true;
    setIsLoading(true);
    setError('');
    getOrder(id)
      .then((result) => { if (active) setOrder(result.order); })
      .catch((err) => { if (active) setError(err instanceof Error ? err.message : 'No se pudo cargar el pedido.'); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [id]);

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      DELIVERED: 'bg-green-100 text-green-800',
      IN_TRANSIT: 'bg-blue-100 text-blue-800',
      DELAYED: 'bg-amber-100 text-amber-800',
      CANCELLED: 'bg-gray-100 text-gray-800',
      PREPARING: 'bg-purple-100 text-purple-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (isLoading) {
    return (
      <ClientLayout>
        <Card>
          <CardContent className="text-center py-12 text-gray-500">Cargando pedido...</CardContent>
        </Card>
      </ClientLayout>
    );
  }

  if (!order || error) {
    return (
      <ClientLayout>
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold mb-4">{error ? 'No se pudo cargar el pedido' : 'Pedido no encontrado'}</h2>
          <p role={error ? 'alert' : undefined} className="text-gray-600 mb-6">{error}</p>
          <Link to="/orders">
            <Button>Volver a pedidos</Button>
          </Link>
        </div>
      </ClientLayout>
    );
  }

  return (
    <ClientLayout>
      <div className="space-y-6 max-w-4xl mx-auto">
        <div className="flex items-center gap-4">
          <Link to="/orders">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="size-4 mr-2" />
              Volver
            </Button>
          </Link>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">{order.storeName}</h1>
            <p className="text-gray-600">Pedido {order.code}</p>
            <p className="text-sm text-amber-800">Operación de demostración: pago no verificado. No acredita un cobro ni una entrega real.</p>
          </div>
          <Badge className={`${getStatusColor(order.status)} text-lg px-4 py-2`}>
            {ORDER_STATUS_LABELS[order.status]}
          </Badge>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Información del pedido</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-600">Fecha de pedido</span>
              <span className="font-semibold">{formatDateTime(order.createdAt)}</span>
            </div>
            {order.estimatedDelivery && (
              <div className="flex justify-between">
                <span className="text-gray-600">Entrega estimada</span>
                <span className="font-semibold">{formatDateTime(order.estimatedDelivery)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-600">Estado</span>
              <Badge className={getStatusColor(order.status)}>
                {ORDER_STATUS_LABELS[order.status]}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Productos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {order.items.map((item) => (
                <div key={item.id} className="flex justify-between items-center">
                  <div>
                    <p className="font-semibold">{item.name}</p>
                    <p className="text-sm text-gray-500">Cantidad: {item.quantity}</p>
                  </div>
                  <p className="font-semibold">{formatCurrency(item.price * item.quantity)}</p>
                </div>
              ))}
              <Separator />
              <div className="flex justify-between items-center text-lg font-bold">
                <span>Total</span>
                <span>{formatCurrency(order.total)}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="size-5" />
                Dirección de entrega
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p>{order.deliveryAddress}</p>
              {order.deliveryNotes && <p className="mt-2 text-sm">Referencia de entrega: {order.deliveryNotes}</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="size-5" />
                Método de pago
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p>{order.paymentMethod}</p>
              <p className="text-sm text-gray-500 mt-1">
                Importe del pedido: {formatCurrency(order.total)}
              </p>
            </CardContent>
          </Card>
        </div>

        {order.deliveryDriver && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="size-5" />
                Repartidor
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="font-semibold">{order.deliveryDriver}</p>
              <p className="text-sm text-gray-500">{order.driverVerified ? 'Asignación registrada, sin seguimiento de ubicación' : 'Texto histórico sin asignación de repartidor verificada'}</p>
            </CardContent>
          </Card>
        )}

        <OrderHistory order={order} />
        {order.deliveredAt && <p>Entrega registrada · {formatDateTime(order.deliveredAt)}</p>}
        {(
          <Card className="bg-orange-50 border-orange-200">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <AlertCircle className="size-8 text-orange-600" />
                  <div>
                    <h3 className="font-semibold">¿Tuviste algún problema con este pedido?</h3>
                    <p className="text-sm text-gray-600">
                      Crea un reclamo y te ayudaremos a resolverlo.
                    </p>
                  </div>
                </div>
                <Link to={`/claims/new?orderId=${order.id}`}>
                  <Button>Crear reclamo</Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </ClientLayout>
  );
}
