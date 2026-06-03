import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Download, TrendingUp, Clock, CheckCircle, Users } from 'lucide-react';
import { getReports, ReportsResponse } from '../../lib/api';
import AdminLayout from '../../components/AdminLayout';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

export default function ReportsPage() {
  const [data, setData] = useState<ReportsResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getReports()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los reportes.'));
  }, []);

  const metrics = data?.metrics || {};
  const totalClaims = metrics.total || 0;
  const approvedRate = metrics.porcentaje_respuestas_aprobadas || 0;
  const escalated = data?.byStatus.find((item) => item.estado === 'Escalado')?.total || 0;
  const categoryData = (data?.byCategory || []).map((item, index) => ({
    name: item.categoria,
    value: item.total,
    color: ['#f97316', '#3b82f6', '#10b981', '#8b5cf6', '#ec4899', '#ef4444'][index % 6],
  }));
  const statusData = data?.byStatus || [];
  const responseTimeData = data?.attentionTimeByCategory || [];
  const confidenceData = data?.confidenceByCategory || [];
  const reviewStatusData = data?.responsesByReviewStatus || [];

  const handleExport = () => {
    const rows = [
      ['indicador', 'valor'],
      ['Total reclamos', String(totalClaims)],
      ['Confianza promedio', `${metrics.confianza_promedio || 0}%`],
      ['Respuestas aprobadas', `${approvedRate}%`],
      ['Casos escalados', String(escalated)],
    ];
    const csv = rows.map((row) => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'smartclaim_report.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Reportes y Analytics</h1>
            <p className="text-gray-600">
              Métricas calculadas desde reclamos, análisis y respuestas registradas.
            </p>
          </div>
          <Button onClick={handleExport} className="gap-2">
            <Download className="size-4" />
            Exportar CSV
          </Button>
        </div>

        {error && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4 text-red-700">{error}</CardContent>
          </Card>
        )}

        <div className="grid md:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total reclamos</CardTitle>
              <TrendingUp className="size-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalClaims}</div>
              <p className="text-xs text-gray-500 mt-1">Base transaccional</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Tiempo promedio</CardTitle>
              <Clock className="size-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{metrics.tiempo_promedio_atencion || 0} min</div>
              <p className="text-xs text-gray-500 mt-1">Creación a cierre</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Tasa de aprobacion</CardTitle>
              <CheckCircle className="size-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{approvedRate}%</div>
              <p className="text-xs text-gray-500 mt-1">Respuestas aprobadas</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Casos escalados</CardTitle>
              <Users className="size-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{escalated}</div>
              <p className="text-xs text-gray-500 mt-1">Requieren supervisor</p>
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
                  <Pie data={categoryData} cx="50%" cy="50%" outerRadius={80} fill="#8884d8" dataKey="value" label>
                    {categoryData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
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
                  <XAxis dataKey="estado" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="total" fill="#f97316" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Tiempo promedio por categoría</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={responseTimeData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="categoria" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="tiempo_promedio_min" fill="#3b82f6" name="Minutos" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Nivel de confianza del sistema IA</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center h-[300px]">
                <div className="text-center">
                  <div className="text-6xl font-bold text-green-600 mb-4">
                    {metrics.confianza_promedio || 0}%
                  </div>
                  <p className="text-gray-600 mb-2">Confianza promedio de clasificación</p>
                  <div className="w-64 bg-gray-200 rounded-full h-4 overflow-hidden">
                    <div
                      className="bg-green-500 h-full rounded-full"
                      style={{ width: `${metrics.confianza_promedio || 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Confianza promedio por categoria</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={confidenceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="categoria" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="confianza_promedio" fill="#10b981" name="Confianza %" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Revision de respuestas</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={reviewStatusData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="estado_revision" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="total" fill="#8b5cf6" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        <Card className="bg-purple-50 border-purple-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <h3 className="font-semibold text-purple-900 mb-2">Observación de despliegue</h3>
              <p className="text-sm text-purple-800">
                Los reportes consumen datos registrados por la aplicación. Para producción conviene reforzar
                autenticación, permisos por rol y trazabilidad del envío al cliente.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
