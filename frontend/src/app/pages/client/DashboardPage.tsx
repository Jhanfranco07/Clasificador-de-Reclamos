import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { ShoppingBag, AlertCircle, Clock, Plus, ArrowRight, HelpCircle } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { getOrdersByUserId } from '../../lib/mockData';
import { listClaims, ClaimSummary } from '../../lib/api';
import { ORDER_STATUS_LABELS, CLAIM_STATUS_LABELS } from '../../types';
import { formatCurrency, formatDateTime } from '../../lib/utils';
import ClientLayout from '../../components/ClientLayout';

export default function DashboardPage() {
  const { currentUser } = useAuth();
  const userOrders = currentUser ? getOrdersByUserId(currentUser.id) : [];
  const recentOrders = userOrders.slice(0, 3);
  const [claims, setClaims] = useState<ClaimSummary[]>([]);

  useEffect(() => {
    listClaims()
      .then((data) => setClaims(data.items))
      .catch(() => setClaims([]));
  }, []);

  const userClaims = currentUser
    ? claims.filter((claim) => claim.customerEmail?.toLowerCase() === currentUser.email.toLowerCase())
    : [];
  const openClaims = userClaims.filter((claim) => claim.statusKey !== 'CLOSED');

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      DELIVERED: 'bg-green-100 text-green-800',
      IN_TRANSIT: 'bg-blue-100 text-blue-800',
      DELAYED: 'bg-amber-100 text-amber-800',
      CANCELLED: 'bg-gray-100 text-gray-800',
      PREPARING: 'bg-purple-100 text-purple-800',
      RECEIVED: 'bg-blue-100 text-blue-800',
      ANALYZING: 'bg-purple-100 text-purple-800',
      IN_REVIEW: 'bg-amber-100 text-amber-800',
      RESPONDED: 'bg-green-100 text-green-800',
      ESCALATED: 'bg-red-100 text-red-800',
      CLOSED: 'bg-gray-100 text-gray-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <ClientLayout>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">
            Hola, {currentUser?.name?.split(' ')[0]}
          </h1>
          <p className="text-gray-600">
            Revisa tus pedidos, consulta reclamos y solicita ayuda cuando tengas un inconveniente.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Pedidos registrados</CardTitle>
              <ShoppingBag className="size-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{userOrders.length}</div>
              <p className="text-xs text-gray-500 mt-1">
                Historial disponible en tu cuenta
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Reclamos abiertos</CardTitle>
              <AlertCircle className="size-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{openClaims.length}</div>
              <p className="text-xs text-gray-500 mt-1">{userClaims.length} reclamos registrados</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Pedidos en camino</CardTitle>
              <Clock className="size-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {userOrders.filter((order) => order.status === 'IN_TRANSIT').length}
              </div>
              <p className="text-xs text-gray-500 mt-1">Seguimiento activo</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <Card className="bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plus className="size-5" />
                Nuevo pedido
              </CardTitle>
              <CardDescription>Explora restaurantes y arma tu carrito.</CardDescription>
            </CardHeader>
            <CardContent>
              <Link to="/">
                <Button className="w-full">Explorar restaurantes</Button>
              </Link>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="size-5" />
                ¿Algún problema?
              </CardTitle>
              <CardDescription>Reporta un inconveniente con tu pedido.</CardDescription>
            </CardHeader>
            <CardContent>
              <Link to="/claims/new">
                <Button variant="secondary" className="w-full">Crear reclamo</Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Pedidos recientes</CardTitle>
              <Link to="/orders">
                <Button variant="ghost" size="sm">
                  Ver todos <ArrowRight className="ml-2 size-4" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentOrders.map((order) => (
                <div key={order.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors">
                  <div className="flex items-center gap-4">
                    <img src={order.storeImage} alt={order.storeName} className="size-12 rounded-lg object-cover" />
                    <div>
                      <p className="font-semibold">{order.storeName}</p>
                      <p className="text-sm text-gray-500">{order.code}</p>
                      <p className="text-xs text-gray-400">{formatDateTime(order.createdAt)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="font-semibold">{formatCurrency(order.total)}</p>
                      <Badge className={getStatusColor(order.status)}>
                        {ORDER_STATUS_LABELS[order.status]}
                      </Badge>
                    </div>
                    <Link to={`/orders/${order.id}`}>
                      <Button variant="ghost" size="sm"><ArrowRight className="size-4" /></Button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {openClaims.length > 0 && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Reclamos en proceso</CardTitle>
                <Link to="/claims">
                  <Button variant="ghost" size="sm">
                    Ver todos <ArrowRight className="ml-2 size-4" />
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {openClaims.slice(0, 4).map((claim) => (
                  <div key={claim.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors">
                    <div>
                      <p className="font-semibold">{claim.code}</p>
                      <p className="text-sm text-gray-600">{claim.category}</p>
                      <p className="text-xs text-gray-400 mt-1">{formatDateTime(claim.createdAt)}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <Badge className={getStatusColor(claim.statusKey)}>
                        {CLAIM_STATUS_LABELS[claim.statusKey as keyof typeof CLAIM_STATUS_LABELS] || claim.status}
                      </Badge>
                      <Link to={`/claims/${claim.id}`}>
                        <Button variant="ghost" size="sm"><ArrowRight className="size-4" /></Button>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <Card className="bg-gradient-to-br from-purple-50 to-pink-50 border-purple-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HelpCircle className="size-5" />
              ¿Necesitas ayuda?
            </CardTitle>
            <CardDescription>Consulta el centro de ayuda o crea un reclamo</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3">
              <Link to="/help">
                <Button variant="outline">Centro de ayuda</Button>
              </Link>
              <Link to="/claims/new">
                <Button variant="outline">Crear reclamo</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </ClientLayout>
  );
}
