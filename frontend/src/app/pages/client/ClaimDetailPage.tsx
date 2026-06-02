import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Separator } from '../../components/ui/separator';
import { ArrowLeft, CheckCircle, Clock, Eye, MessageSquare, AlertCircle } from 'lucide-react';
import { getClaim, ClaimDetailResponse } from '../../lib/api';
import { CLAIM_STATUS_LABELS } from '../../types';
import { formatDateTime } from '../../lib/utils';
import ClientLayout from '../../components/ClientLayout';

export default function ClaimDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<ClaimDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    getClaim(id)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar el reclamo.'))
      .finally(() => setIsLoading(false));
  }, [id]);

  if (isLoading) {
    return (
      <ClientLayout>
        <Card>
          <CardContent className="text-center py-12 text-gray-500">Cargando reclamo...</CardContent>
        </Card>
      </ClientLayout>
    );
  }

  if (!detail || error) {
    return (
      <ClientLayout>
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold mb-4">Reclamo no encontrado</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <Link to="/claims">
            <Button>Volver a reclamos</Button>
          </Link>
        </div>
      </ClientLayout>
    );
  }

  const { claim, response, history } = detail;

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

  const getStatusIcon = (action: string) => {
    if (action.includes('Registro')) return <CheckCircle className="size-5 text-green-600" />;
    if (action.includes('IA')) return <Eye className="size-5 text-purple-600" />;
    if (action.includes('respuesta') || action.includes('Respuesta')) return <MessageSquare className="size-5 text-blue-600" />;
    if (action.includes('revisión') || action.includes('revision')) return <Clock className="size-5 text-amber-600" />;
    return <AlertCircle className="size-5 text-gray-600" />;
  };

  return (
    <ClientLayout>
      <div className="space-y-6 max-w-4xl mx-auto">
        <div className="flex items-center gap-4">
          <Link to="/claims">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="size-4 mr-2" />
              Volver
            </Button>
          </Link>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Reclamo {claim.code}</h1>
            <p className="text-gray-600">Pedido: {claim.orderCode}</p>
          </div>
          <Badge className={`${getStatusColor(claim.statusKey)} text-lg px-4 py-2`}>
            {CLAIM_STATUS_LABELS[claim.statusKey as keyof typeof CLAIM_STATUS_LABELS] || claim.status}
          </Badge>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Informacion del reclamo</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-gray-600 mb-1">Categoria detectada</p>
              <p className="font-semibold">{claim.category}</p>
            </div>
            <Separator />
            <div>
              <p className="text-sm text-gray-600 mb-1">Descripcion</p>
              <p className="text-gray-800 whitespace-pre-line">{claim.description}</p>
            </div>
            <Separator />
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600 mb-1">Fecha de creacion</p>
                <p className="font-semibold">{formatDateTime(claim.createdAt)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Canal</p>
                <p className="font-semibold">{claim.channel}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Linea de tiempo</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {history.map((event, index) => (
                <div key={event.id} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="flex items-center justify-center size-10 rounded-full bg-gray-100">
                      {getStatusIcon(event.action)}
                    </div>
                    {index < history.length - 1 && (
                      <div className="w-0.5 h-12 bg-gray-200 mt-2" />
                    )}
                  </div>
                  <div className="flex-1 pt-1">
                    <p className="font-semibold">{event.action}</p>
                    {event.comment && <p className="text-sm text-gray-700">{event.comment}</p>}
                    <p className="text-sm text-gray-500 mt-1">{formatDateTime(event.createdAt)}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {response?.finalResponse ? (
          <Card className="border-green-200 bg-green-50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="size-5" />
                Respuesta de soporte
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-800 whitespace-pre-line">{response.finalResponse}</p>
            </CardContent>
          </Card>
        ) : (
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Clock className="size-8 text-blue-600" />
                <div>
                  <h3 className="font-semibold">Tu reclamo esta en revision</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    SmartClaim AI ya genero una respuesta sugerida. Un agente debe revisarla antes de enviarla.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </ClientLayout>
  );
}
