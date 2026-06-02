import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import {
  AlertCircle,
  CheckCircle,
  Clock,
  TrendingUp,
  Brain,
  Users,
  AlertTriangle,
} from 'lucide-react';
import { getDashboard, DashboardResponse } from '../../lib/api';
import { CLAIM_STATUS_LABELS } from '../../types';
import AdminLayout from '../../components/AdminLayout';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

export default function AdminDashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar el dashboard.'));
  }, []);

  const metrics = data?.metrics || {};
  const totalClaims = metrics.total || 0;
  const newClaims = data?.byStatus.find((item) => item.estado === 'Nuevo')?.total || 0;
  const inReview = data?.byStatus.find((item) => item.estado === 'En revisión' || item.estado === 'En revision')?.total || 0;
  const responded = metrics.respondidos || 0;
  const critical = metrics.casos_criticos_pendientes || 0;
  const pending = newClaims + inReview + critical;

  const statusData = (data?.byStatus || []).map((item) => ({ name: item.estado, value: item.total }));
  const categoryData = (data?.byCategory || []).map((item) => ({ name: item.categoria, value: item.total }));
  const COLORS = ['#f97316', '#3b82f6', '#10b981', '#8b5cf6', '#ec4899', '#ef4444'];

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
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
    <AdminLayout>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">Centro de soporte operativo</h1>
          <p className="text-gray-600">
            Monitorea reclamos, carga de atención, casos críticos y respuestas pendientes.
          </p>
        </div>

        <Card className="border-orange-200 bg-orange-50">
          <CardContent className="py-5">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-orange-700">Prioridad del turno</p>
                <h2 className="text-2xl font-bold mt-1">
                  {pending > 0 ? `${pending} caso(s) requieren seguimiento` : 'No hay reclamos pendientes'}
                </h2>
                <p className="text-sm text-orange-900/80 mt-1">
                  Revisa primero los reclamos críticos, escalados o marcados para revisión humana.
                </p>
              </div>
              <Badge className={pending > 0 ? 'bg-orange-600' : 'bg-green-600'}>
                {pending > 0 ? 'Atención requerida' : 'Operación estable'}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {error && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4 text-red-700">{error}</CardContent>
          </Card>
        )}

        <div className="grid md:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total de reclamos</CardTitle>
              <AlertCircle className="size-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalClaims}</div>
              <p className="text-xs text-gray-500 mt-1">Registrados en base de datos</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Nuevos</CardTitle>
              <Clock className="size-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{newClaims}</div>
              <p className="text-xs text-gray-500 mt-1">Requieren análisis inicial</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Analizados por IA</CardTitle>
              <Brain className="size-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-600">{metrics.analizados || 0}</div>
              <p className="text-xs text-gray-500 mt-1">Clasificación generada</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Críticos pendientes</CardTitle>
              <AlertTriangle className="size-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{critical}</div>
              <p className="text-xs text-gray-500 mt-1">Prioridad crítica abierta</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">En revisión</CardTitle>
              <Users className="size-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-amber-600">{inReview}</div>
              <p className="text-xs text-gray-500 mt-1">Revisión humana</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Respondidos/Cerrados</CardTitle>
              <CheckCircle className="size-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{responded}</div>
              <p className="text-xs text-gray-500 mt-1">Gestión completada o enviada</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Confianza promedio</CardTitle>
              <TrendingUp className="size-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">
                {metrics.confianza_promedio || 0}%
              </div>
              <p className="text-xs text-gray-500 mt-1">Promedio de clasificación</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Reclamos por categoría</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={categoryData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label>
                    {categoryData.map((entry, index) => (
                      <Cell key={`cell-${entry.name}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Reclamos por estado</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={statusData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#f97316" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Actividad reciente</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {(data?.recentClaims || []).map((claim) => (
                <div key={claim.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <p className="font-semibold">{claim.code}</p>
                    <p className="text-sm text-gray-600">{claim.customerName} · {claim.category}</p>
                    <p className="text-xs text-gray-500 mt-1">Pedido: {claim.orderCode}</p>
                  </div>
                  <Badge className={getStatusColor(claim.statusKey)}>
                    {CLAIM_STATUS_LABELS[claim.statusKey as keyof typeof CLAIM_STATUS_LABELS] || claim.status}
                  </Badge>
                </div>
              ))}
              {!data?.recentClaims.length && (
                <p className="text-sm text-gray-500">Aún no hay actividad registrada.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
