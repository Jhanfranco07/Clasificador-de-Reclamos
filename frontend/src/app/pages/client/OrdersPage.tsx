import { Link } from 'react-router';
import { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { ShoppingBag } from 'lucide-react';
import { ORDER_STATUS_LABELS } from '../../types';
import { formatCurrency, formatDateTime } from '../../lib/utils';
import { ApiOrder, listOrders } from '../../lib/api';
import ClientLayout from '../../components/ClientLayout';

export default function OrdersPage() {
  const [orders, setOrders] = useState<ApiOrder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    listOrders()
      .then((result) => setOrders(result.items))
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los pedidos.'))
      .finally(() => setIsLoading(false));
  }, []);

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

  return (
    <ClientLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Mis pedidos</h1>
          <p className="text-gray-600">Historial completo de tus pedidos</p>
        </div>

        {error && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4 text-red-700">{error}</CardContent>
          </Card>
        )}

        {isLoading ? (
          <Card>
            <CardContent className="text-center py-12 text-gray-500">
              Cargando pedidos...
            </CardContent>
          </Card>
        ) : orders.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <ShoppingBag className="size-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-xl font-semibold mb-2">No tienes pedidos</h3>
              <p className="text-gray-600 mb-6">
                Empieza a explorar restaurantes y haz tu primer pedido
              </p>
              <Link to="/">
                <Button>Explorar restaurantes</Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {orders.map((order) => (
              <Card key={order.id} className="hover:shadow-lg transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 flex-1">
                      {order.storeImage && (
                        <img
                          src={order.storeImage}
                          alt={order.storeName}
                          className="size-16 rounded-lg object-cover"
                        />
                      )}
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="font-semibold text-lg">{order.storeName}</h3>
                          <Badge className={getStatusColor(order.status)}>
                            {ORDER_STATUS_LABELS[order.status]}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-500">{order.code}</p>
                        <p className="text-xs text-gray-400 mt-1">
                          {formatDateTime(new Date(order.createdAt))}
                        </p>
                        <p className="text-sm text-gray-600 mt-2">
                          {order.items.length} productos · {order.paymentMethod}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <p className="text-sm text-gray-500">Total</p>
                        <p className="text-2xl font-bold">{formatCurrency(order.total)}</p>
                      </div>
                      <div className="flex flex-col gap-2">
                        <Link to={`/orders/${order.id}`}>
                          <Button variant="outline" size="sm" className="w-full">
                            Ver detalle
                          </Button>
                        </Link>
                        {(order.status === 'DELIVERED' || order.status === 'DELAYED') && (
                          <Link to={`/claims/new?orderId=${order.id}`}>
                            <Button variant="ghost" size="sm" className="w-full">
                              Reportar problema
                            </Button>
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </ClientLayout>
  );
}
