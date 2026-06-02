import { Link } from 'react-router';
import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { AlertTriangle, Eye, Filter, Search } from 'lucide-react';
import { listClaims, ClaimSummary } from '../../lib/api';
import { CLAIM_STATUS_LABELS, ClaimStatus } from '../../types';
import { formatDateTime } from '../../lib/utils';
import AdminLayout from '../../components/AdminLayout';

export default function ClaimsBandejaPage() {
  const [claims, setClaims] = useState<ClaimSummary[]>([]);
  const [statusFilter, setStatusFilter] = useState<ClaimStatus | 'ALL'>('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    listClaims()
      .then((data) => setClaims(data.items))
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los reclamos.'));
  }, []);

  const filteredClaims = claims.filter((claim) => {
    const matchesStatus = statusFilter === 'ALL' || claim.statusKey === statusFilter;
    const query = searchTerm.trim().toLowerCase();
    const matchesSearch = !query || [
      claim.code,
      claim.customerName,
      claim.customerEmail,
      claim.orderCode,
      claim.category,
      claim.priority,
    ].some((value) => value?.toLowerCase().includes(query));
    return matchesStatus && matchesSearch;
  });

  const urgentClaims = claims.filter((claim) => claim.priorityKey === 'CRITICAL' || claim.statusKey === 'ESCALATED');
  const activeClaims = claims.filter((claim) => !['RESPONDED', 'CLOSED'].includes(claim.statusKey));

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      RECEIVED: 'bg-blue-100 text-blue-800',
      ANALYZING: 'bg-purple-100 text-purple-800',
      IN_REVIEW: 'bg-amber-100 text-amber-800',
      RESPONDED: 'bg-green-100 text-green-800',
      ESCALATED: 'bg-red-100 text-red-800',
      CLOSED: 'bg-gray-100 text-gray-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      LOW: 'text-gray-600',
      MEDIUM: 'text-blue-600',
      HIGH: 'text-orange-600',
      CRITICAL: 'text-red-600 font-bold'
    };
    return colors[priority] || 'text-gray-600';
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">Bandeja de reclamos</h1>
            <p className="text-gray-600">
              Prioriza casos sensibles, revisa respuestas sugeridas y cierra la atención del cliente.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative">
              <Search className="size-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <Input
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Buscar código, cliente o pedido"
                className="pl-9 sm:w-72"
              />
            </div>
            <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as ClaimStatus | 'ALL')}>
              <SelectTrigger className="w-48">
                <Filter className="size-4 text-gray-500 mr-2" />
                <SelectValue placeholder="Filtrar por estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Todos los estados</SelectItem>
                <SelectItem value="RECEIVED">Recibidos</SelectItem>
                <SelectItem value="ANALYZING">Analizados por IA</SelectItem>
                <SelectItem value="IN_REVIEW">En revisión</SelectItem>
                <SelectItem value="RESPONDED">Respondidos</SelectItem>
                <SelectItem value="ESCALATED">Escalados</SelectItem>
                <SelectItem value="CLOSED">Cerrados</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {error && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4 text-red-700">{error}</CardContent>
          </Card>
        )}

        <div className="grid md:grid-cols-4 gap-4">
          {[
            ['Activos', 'ACTIVE', 'text-slate-900'],
            ['Urgentes', 'URGENT', 'text-red-600'],
            ['En revisión', 'IN_REVIEW', 'text-amber-600'],
            ['Requieren agente', 'REVIEW', 'text-purple-600'],
          ].map(([label, key, color]) => (
            <Card key={key}>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className={`text-2xl font-bold ${color}`}>
                    {key === 'REVIEW'
                      ? claims.filter(c => c.requiresHumanReview).length
                      : key === 'URGENT'
                        ? urgentClaims.length
                      : key === 'ACTIVE'
                        ? activeClaims.length
                      : claims.filter(c => c.statusKey === key).length}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">{label}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle>Reclamos ({filteredClaims.length})</CardTitle>
              {urgentClaims.length > 0 && (
                <Badge className="bg-red-100 text-red-700 hover:bg-red-100">
                  <AlertTriangle className="size-3 mr-1" />
                  {urgentClaims.length} urgente(s)
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código</TableHead>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Pedido</TableHead>
                    <TableHead>Categoría</TableHead>
                    <TableHead>Prioridad</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead className="text-right">Acción</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredClaims.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8 text-gray-500">
                        No hay reclamos con este filtro
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredClaims.map((claim) => (
                      <TableRow key={claim.id}>
                        <TableCell className="font-medium">{claim.code}</TableCell>
                        <TableCell>{claim.customerName}</TableCell>
                        <TableCell>{claim.orderCode}</TableCell>
                        <TableCell>{claim.category}</TableCell>
                        <TableCell>
                          <span className={getPriorityColor(claim.priorityKey)}>
                            {claim.priority}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(claim.statusKey)}>
                            {CLAIM_STATUS_LABELS[claim.statusKey as keyof typeof CLAIM_STATUS_LABELS] || claim.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {formatDateTime(claim.createdAt)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Link to={`/admin/claims/${claim.id}`}>
                            <Button variant="ghost" size="sm">
                              <Eye className="size-4 mr-1" />
                              Revisar
                            </Button>
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
