import { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Brain,
  CheckCircle,
  CircleDot,
  Clock,
  Download,
  FolderCheck,
  Lightbulb,
  MessageSquareReply,
  ShieldAlert,
  TrendingUp,
  Users,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import AdminLayout from '../../components/AdminLayout';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { getReports, ReportsResponse } from '../../lib/api';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const CATEGORY_COLORS: Record<string, string> = {
  'Cobro indebido': '#ef4444',
  'Retraso de pedido': '#f97316',
  'Producto incorrecto': '#8b5cf6',
  'Producto incompleto': '#a855f7',
  'Fraude o seguridad': '#b91c1c',
  'Problema con tarjeta': '#ec4899',
  'Soporte general': '#3b82f6',
  'Sin clasificar': '#94a3b8',
};

const STATUS_COLORS: Record<string, string> = {
  Nuevo: '#3b82f6',
  'Analizado por IA': '#8b5cf6',
  'En revisión': '#f59e0b',
  'En revision': '#f59e0b',
  Respondido: '#22c55e',
  Escalado: '#ef4444',
  Cerrado: '#64748b',
};

const PRIORITY_COLORS: Record<string, string> = {
  Crítica: '#b91c1c',
  Critica: '#b91c1c',
  Alta: '#f97316',
  Media: '#eab308',
  Baja: '#22c55e',
  'Sin prioridad': '#94a3b8',
};

const REVIEW_COLORS: Record<string, string> = {
  APROBADA: '#22c55e',
  ENVIADA: '#16a34a',
  PENDIENTE: '#f59e0b',
  EDITADA: '#3b82f6',
  RECHAZADA: '#ef4444',
};

function MetricCard({
  title,
  value,
  description,
  icon: Icon,
  tone,
}: {
  title: string;
  value: string | number;
  description: string;
  icon: typeof TrendingUp;
  tone: string;
}) {
  return (
    <Card className="border-gray-200 shadow-sm">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-gray-700">{title}</p>
            <p className="mt-3 text-3xl font-bold text-gray-950">{value}</p>
          </div>
          <div className={`flex size-10 shrink-0 items-center justify-center rounded-md ${tone}`}>
            <Icon className="size-5" />
          </div>
        </div>
        <p className="mt-3 text-xs leading-5 text-gray-500">{description}</p>
      </CardContent>
    </Card>
  );
}

function SectionHeading({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h2 className="text-xl font-bold text-gray-950">{title}</h2>
      <p className="mt-1 text-sm text-gray-600">{description}</p>
    </div>
  );
}

function ChartCard({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="border-gray-200 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
        <p className="text-xs leading-5 text-gray-500">{description}</p>
      </CardHeader>
      <CardContent className="pt-2">{children}</CardContent>
    </Card>
  );
}

export default function ReportsPage() {
  const [data, setData] = useState<ReportsResponse | null>(null);
  const [error, setError] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [status, setStatus] = useState('ALL');
  const [category, setCategory] = useState('ALL');
  const [priority, setPriority] = useState('ALL');

  useEffect(() => {
    getReports({ dateFrom, dateTo, status, category, priority })
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los reportes.'));
  }, [category, dateFrom, dateTo, priority, status]);

  const metrics = data?.metrics || {};
  const totalClaims = metrics.total || 0;
  const approvedRate = metrics.porcentaje_respuestas_aprobadas || 0;
  const escalated = metrics.casos_escalados || 0;
  const categoryData = data?.byCategory || [];
  const statusData = data?.byStatus || [];
  const priorityData = data?.byPriority || [];
  const resolutionData = data?.attentionTimeByCategory || [];
  const firstResponseData = data?.firstResponseTimeByCategory || [];
  const confidenceData = data?.confidenceByCategory || [];
  const reviewStatusData = data?.responsesByReviewStatus || [];
  const evolutionData = data?.claimsEvolution || [];

  const insights = useMemo(() => {
    const result: string[] = [];
    const topCategory = categoryData[0];
    const topStatus = [...statusData].sort((left, right) => right.total - left.total)[0];
    if (topCategory) result.push(`La categoría con mayor frecuencia es ${topCategory.categoria}, con ${topCategory.total} reclamo(s).`);
    if (approvedRate > 0) result.push(`El ${approvedRate}% de las respuestas sugeridas por IA fueron aprobadas por soporte.`);
    if ((metrics.confianza_promedio || 0) > 0) {
      const level = (metrics.confianza_promedio || 0) >= 85 ? 'alta y estable' : (metrics.confianza_promedio || 0) >= 65 ? 'media' : 'baja';
      result.push(`La confianza promedio del sistema es ${metrics.confianza_promedio}%, considerada ${level}.`);
    }
    result.push(escalated > 0
      ? `${escalated} reclamo(s) fueron escalados a una revisión superior.`
      : 'Actualmente no existen casos escalados a supervisor.');
    if (topStatus) result.push(`El estado más frecuente es ${topStatus.estado}, con ${topStatus.total} caso(s).`);
    return result.slice(0, 4);
  }, [approvedRate, categoryData, escalated, metrics.confianza_promedio, statusData]);

  const handleExport = () => {
    const rows = [
      ['Indicador', 'Valor'],
      ['Total de reclamos registrados', String(totalClaims)],
      ['Tiempo promedio de resolución', `${metrics.tiempo_promedio_atencion || 0} min`],
      ['Tasa de aprobación de respuestas', `${approvedRate}%`],
      ['Casos escalados a supervisor', String(escalated)],
      ['Reclamos abiertos', String(metrics.reclamos_abiertos || 0)],
      ['Reclamos cerrados', String(metrics.reclamos_cerrados || 0)],
      ['Tiempo promedio de primera respuesta', `${metrics.tiempo_promedio_primera_respuesta || 0} min`],
      ['Confianza promedio del sistema IA', `${metrics.confianza_promedio || 0}%`],
      ['Porcentaje de reclamos críticos', `${metrics.porcentaje_criticos || 0}%`],
    ];
    const csv = rows.map((row) => row.map((value) => `"${value}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'smartclaim-reporte-ejecutivo.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  const handlePdfExport = () => {
    const document = new jsPDF();
    document.setFontSize(18);
    document.text('SmartClaim AI - Reporte ejecutivo', 14, 18);
    document.setFontSize(10);
    document.text(`Periodo: ${dateFrom || 'inicio'} a ${dateTo || 'actualidad'}`, 14, 26);
    autoTable(document, {
      startY: 32,
      head: [['Indicador', 'Valor']],
      body: [
        ['Total de reclamos registrados', totalClaims],
        ['Tiempo promedio de resolución', `${metrics.tiempo_promedio_atencion || 0} min`],
        ['Tasa de aprobación de respuestas', `${approvedRate}%`],
        ['Casos escalados a supervisor', escalated],
        ['Reclamos abiertos', metrics.reclamos_abiertos || 0],
        ['Reclamos cerrados', metrics.reclamos_cerrados || 0],
        ['Confianza promedio IA', `${metrics.confianza_promedio || 0}%`],
      ],
    });
    autoTable(document, {
      head: [['Categoría', 'Reclamos']],
      body: categoryData.map((item) => [item.categoria, item.total]),
    });
    document.save('smartclaim-reporte-ejecutivo.pdf');
  };

  return (
    <AdminLayout>
      <div className="space-y-9">
        <div className="flex flex-col gap-4 border-b border-gray-200 pb-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase text-orange-600">Control operativo e inteligencia artificial</p>
            <h1 className="mt-2 text-3xl font-bold text-gray-950">Reportes y Analytics</h1>
            <p className="mt-2 max-w-3xl text-sm text-gray-600">
              Indicadores calculados desde reclamos, conversaciones, análisis de IA y respuestas revisadas por soporte.
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleExport} variant="outline" className="gap-2"><Download className="size-4" />CSV</Button>
            <Button onClick={handlePdfExport} className="gap-2"><Download className="size-4" />PDF</Button>
          </div>
        </div>

        <Card>
          <CardContent className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-5">
            <Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} aria-label="Fecha inicial" />
            <Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} aria-label="Fecha final" />
            <Select value={status} onValueChange={setStatus}><SelectTrigger><SelectValue placeholder="Estado" /></SelectTrigger><SelectContent><SelectItem value="ALL">Todos los estados</SelectItem><SelectItem value="RECEIVED">Nuevo</SelectItem><SelectItem value="IN_REVIEW">En revisión</SelectItem><SelectItem value="RESPONDED">Respondido</SelectItem><SelectItem value="ESCALATED">Escalado</SelectItem><SelectItem value="CLOSED">Cerrado</SelectItem></SelectContent></Select>
            <Select value={priority} onValueChange={setPriority}><SelectTrigger><SelectValue placeholder="Prioridad" /></SelectTrigger><SelectContent><SelectItem value="ALL">Todas las prioridades</SelectItem><SelectItem value="LOW">Baja</SelectItem><SelectItem value="MEDIUM">Media</SelectItem><SelectItem value="HIGH">Alta</SelectItem><SelectItem value="CRITICAL">Crítica</SelectItem></SelectContent></Select>
            <Select value={category} onValueChange={setCategory}><SelectTrigger><SelectValue placeholder="Categoría" /></SelectTrigger><SelectContent><SelectItem value="ALL">Todas las categorías</SelectItem>{categoryData.map((item) => <SelectItem key={item.categoria} value={item.categoria}>{item.categoria}</SelectItem>)}</SelectContent></Select>
          </CardContent>
        </Card>

        {error && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4 text-red-700">{error}</CardContent>
          </Card>
        )}

        <section className="space-y-5">
          <SectionHeading title="Resumen general" description="Lectura ejecutiva del volumen, resolución y desempeño del servicio." />
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Total de reclamos registrados" value={totalClaims} description="Número total de reclamos almacenados en el sistema." icon={TrendingUp} tone="bg-blue-50 text-blue-600" />
            <MetricCard title="Tiempo promedio de resolución" value={`${metrics.tiempo_promedio_atencion || 0} min`} description="Tiempo promedio desde la creación del reclamo hasta su cierre." icon={Clock} tone="bg-cyan-50 text-cyan-700" />
            <MetricCard title="Tasa de aprobación de respuestas" value={`${approvedRate}%`} description="Porcentaje de respuestas sugeridas por IA que fueron aprobadas por soporte." icon={CheckCircle} tone="bg-green-50 text-green-700" />
            <MetricCard title="Casos escalados a supervisor" value={escalated} description="Reclamos derivados a revisión superior por complejidad, criticidad o baja confianza." icon={Users} tone="bg-red-50 text-red-600" />
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Reclamos abiertos" value={metrics.reclamos_abiertos || 0} description="Casos que todavía no han sido cerrados formalmente." icon={CircleDot} tone="bg-orange-50 text-orange-600" />
            <MetricCard title="Reclamos cerrados" value={metrics.reclamos_cerrados || 0} description="Casos finalizados con cierre registrado por soporte." icon={FolderCheck} tone="bg-slate-100 text-slate-700" />
            <MetricCard title="Tiempo promedio de primera respuesta" value={`${metrics.tiempo_promedio_primera_respuesta || 0} min`} description="Tiempo desde la creación hasta el primer mensaje enviado por soporte." icon={MessageSquareReply} tone="bg-purple-50 text-purple-600" />
            <MetricCard title="Confianza promedio del sistema IA" value={`${metrics.confianza_promedio || 0}%`} description="Promedio de probabilidad entregada por el clasificador de IA." icon={Brain} tone="bg-emerald-50 text-emerald-700" />
          </div>
        </section>

        <section className="space-y-5">
          <SectionHeading title="Distribución de reclamos" description="Composición del volumen registrado por categoría, estado y prioridad." />
          <div className="grid gap-5 xl:grid-cols-3">
            <ChartCard title="Reclamos por categoría" description="Permite identificar los motivos de contacto más frecuentes.">
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={categoryData} dataKey="total" nameKey="categoria" innerRadius={55} outerRadius={92} paddingAngle={2}>
                    {categoryData.map((item) => <Cell key={item.categoria} fill={CATEGORY_COLORS[item.categoria] || '#64748b'} />)}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Reclamos por estado" description="Situación actual de los reclamos dentro del flujo de atención.">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={statusData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="estado" tick={{ fontSize: 11 }} interval={0} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="total" name="Reclamos" radius={[4, 4, 0, 0]}>
                    {statusData.map((item) => <Cell key={item.estado} fill={STATUS_COLORS[item.estado] || '#64748b'} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Reclamos por prioridad" description={`${metrics.porcentaje_criticos || 0}% del total corresponde a prioridad crítica.`}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={priorityData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis type="category" dataKey="prioridad" width={90} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="total" name="Reclamos" radius={[0, 4, 4, 0]}>
                    {priorityData.map((item) => <Cell key={item.prioridad} fill={PRIORITY_COLORS[item.prioridad] || '#64748b'} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </section>

        <section className="space-y-5">
          <SectionHeading title="Desempeño del sistema IA" description="Confianza de clasificación y nivel de intervención humana sobre respuestas sugeridas." />
          <div className="grid gap-5 xl:grid-cols-2">
            <ChartCard title="Confianza promedio por categoría" description="Una confianza más alta indica mayor consistencia del clasificador para esa categoría.">
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={confidenceData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="categoria" tick={{ fontSize: 11 }} interval={0} />
                  <YAxis domain={[0, 100]} unit="%" />
                  <Tooltip formatter={(value) => [`${value}%`, 'Confianza']} />
                  <Bar dataKey="confianza_promedio" radius={[4, 4, 0, 0]}>
                    {confidenceData.map((item) => (
                      <Cell key={item.categoria} fill={item.confianza_promedio >= 85 ? '#22c55e' : item.confianza_promedio >= 65 ? '#eab308' : '#ef4444'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Revisión de respuestas sugeridas" description="Estado de las respuestas generadas por IA después de la intervención de soporte.">
              <ResponsiveContainer width="100%" height={320}>
                <PieChart>
                  <Pie data={reviewStatusData} dataKey="total" nameKey="estado_revision" innerRadius={60} outerRadius={100} paddingAngle={3}>
                    {reviewStatusData.map((item) => <Cell key={item.estado_revision} fill={REVIEW_COLORS[item.estado_revision] || '#64748b'} />)}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </section>

        <section className="space-y-5">
          <SectionHeading title="Rendimiento operativo" description="Tiempos de atención y evolución del volumen de reclamos." />
          <div className="grid gap-5 xl:grid-cols-2">
            <ChartCard title="Tiempo promedio de resolución por categoría" description="Minutos transcurridos desde la creación hasta el cierre del reclamo.">
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={resolutionData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" unit=" min" />
                  <YAxis type="category" dataKey="categoria" width={120} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value) => [`${value} min`, 'Resolución']} />
                  <Bar dataKey="tiempo_promedio_min" fill="#2563eb" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Tiempo promedio de primera respuesta" description="Minutos desde el registro hasta el primer mensaje público enviado por soporte.">
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={firstResponseData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" unit=" min" />
                  <YAxis type="category" dataKey="categoria" width={120} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value) => [`${value} min`, 'Primera respuesta']} />
                  <Bar dataKey="tiempo_promedio_min" fill="#7c3aed" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
          <ChartCard title="Evolución de reclamos por fecha" description="Cantidad de reclamos registrados diariamente en el periodo disponible.">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={evolutionData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="fecha" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Area type="monotone" dataKey="total" name="Reclamos" stroke="#ea580c" fill="#ffedd5" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>
        </section>

        <section className="space-y-5">
          <SectionHeading title="Observaciones automáticas" description="Lecturas rápidas generadas a partir de los indicadores disponibles." />
          <div className="grid gap-4 md:grid-cols-2">
            {insights.map((insight, index) => (
              <div key={insight} className="flex gap-3 rounded-md border border-blue-100 bg-blue-50 p-4">
                {index === 3 && escalated > 0
                  ? <ShieldAlert className="mt-0.5 size-5 shrink-0 text-red-600" />
                  : index === 3
                    ? <CheckCircle className="mt-0.5 size-5 shrink-0 text-green-600" />
                    : <Lightbulb className="mt-0.5 size-5 shrink-0 text-blue-600" />}
                <p className="text-sm leading-6 text-blue-950">{insight}</p>
              </div>
            ))}
          </div>
          <div className="flex items-start gap-3 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
            <AlertTriangle className="mt-0.5 size-5 shrink-0 text-amber-600" />
            Los indicadores principales y distribuciones reflejan los filtros seleccionados. Los promedios históricos de IA se mantienen como referencia global.
          </div>
        </section>
      </div>
    </AdminLayout>
  );
}
