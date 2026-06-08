import { Link } from 'react-router';
import { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { ArrowRight, AlertCircle, Plus } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { listClaims, ClaimSummary } from '../../lib/api';
import { CLAIM_STATUS_LABELS } from '../../types';
import { formatDateTime } from '../../lib/utils';
import ClientLayout from '../../components/ClientLayout';
import { Input } from '../../components/ui/input';

export default function ClaimsListPage() {
  const { currentUser } = useAuth();
  const [claims, setClaims] = useState<ClaimSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    listClaims({ dateFrom, dateTo, page, pageSize: 6 })
      .then((data) => { setClaims(data.items); setTotalPages(data.pagination.totalPages); })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los reclamos.'))
      .finally(() => setIsLoading(false));
  }, [dateFrom, dateTo, page]);

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

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      LOW: 'text-gray-600',
      MEDIUM: 'text-blue-600',
      HIGH: 'text-orange-600',
      CRITICAL: 'text-red-600',
    };
    return colors[priority] || 'text-gray-600';
  };

  const userClaims = currentUser
    ? claims.filter((claim) => claim.customerEmail?.toLowerCase() === currentUser.email.toLowerCase())
    : [];

  return (
    <ClientLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Mis reclamos</h1>
            <p className="text-gray-600">
              Consulta el estado de tus reclamos y revisa el avance de soporte.
            </p>
          </div>
          <Link to="/claims/new">
            <Button className="gap-2">
              <Plus className="size-4" />
              Nuevo reclamo
            </Button>
          </Link>
        </div>

        {error && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4 text-red-700">{error}</CardContent>
          </Card>
        )}
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card p-4 text-card-foreground">
          <span className="text-sm font-medium">Filtrar por fecha</span>
          <Input type="date" value={dateFrom} onChange={(event) => { setDateFrom(event.target.value); setPage(1); }} className="w-auto" aria-label="Fecha inicial" />
          <Input type="date" value={dateTo} onChange={(event) => { setDateTo(event.target.value); setPage(1); }} className="w-auto" aria-label="Fecha final" />
          {(dateFrom || dateTo) && <Button variant="ghost" onClick={() => { setDateFrom(''); setDateTo(''); setPage(1); }}>Limpiar</Button>}
        </div>

        {isLoading ? (
          <Card>
            <CardContent className="text-center py-12 text-gray-500">
              Cargando reclamos...
            </CardContent>
          </Card>
        ) : userClaims.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <AlertCircle className="size-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-xl font-semibold mb-2">No hay reclamos registrados</h3>
              <p className="text-gray-600 mb-6">
                Si tuviste un problema con un pedido, puedes reportarlo desde aquí.
              </p>
              <Link to="/claims/new">
                <Button>Crear reclamo</Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {userClaims.map((claim) => (
              <Card key={claim.id} className="hover:shadow-lg transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-6">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-semibold text-lg">{claim.code}</h3>
                        <Badge className={getStatusColor(claim.statusKey)}>
                          {CLAIM_STATUS_LABELS[claim.statusKey as keyof typeof CLAIM_STATUS_LABELS] || claim.status}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">
                        <span className="font-semibold">Pedido:</span> {claim.orderCode}
                      </p>
                      <div className="flex flex-wrap items-center gap-3 text-sm">
                        <span className="text-gray-500">{formatDateTime(claim.createdAt)}</span>
                        <span className="text-gray-400">·</span>
                        <span className="text-gray-600">{claim.category}</span>
                        <span className="text-gray-400">·</span>
                        <span className={getPriorityColor(claim.priorityKey)}>
                          Prioridad {claim.priority}
                        </span>
                      </div>
                    </div>
                    <Link to={`/claims/${claim.id}`}>
                      <Button variant="outline" className="gap-2">
                        Ver detalle
                        <ArrowRight className="size-4" />
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
            <div className="flex items-center justify-between pt-3 text-sm">
              <span>Página {page} de {totalPages}</span>
              <div className="flex gap-2"><Button variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</Button><Button variant="outline" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Siguiente</Button></div>
            </div>
          </div>
        )}
      </div>
    </ClientLayout>
  );
}
