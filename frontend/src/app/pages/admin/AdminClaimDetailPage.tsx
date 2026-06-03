import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Textarea } from '../../components/ui/textarea';
import { Separator } from '../../components/ui/separator';
import { Alert, AlertDescription } from '../../components/ui/alert';
import {
  ArrowLeft,
  Brain,
  FileText,
  MessageSquare,
  CheckCircle,
  Edit,
  AlertTriangle,
  User,
  Package,
  TrendingUp,
  RefreshCw,
  Lock
} from 'lucide-react';
import {
  analyzeClaim,
  approveResponse,
  getClaim,
  ClaimDetailResponse,
  updateClaimState,
  updateResponse
} from '../../lib/api';
import { CLAIM_STATUS_LABELS } from '../../types';
import { formatDateTime } from '../../lib/utils';
import AdminLayout from '../../components/AdminLayout';

export default function AdminClaimDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<ClaimDetailResponse | null>(null);
  const [editedResponse, setEditedResponse] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState('');

  const loadClaim = async () => {
    if (!id) return;
    setError('');
    try {
      const data = await getClaim(id);
      setDetail(data);
      setEditedResponse(data.response?.finalResponse || data.response?.editedResponse || data.response?.suggestedResponse || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar el reclamo.');
    }
  };

  useEffect(() => {
    loadClaim();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const runAction = async (action: () => Promise<ClaimDetailResponse>) => {
    setError('');
    setIsWorking(true);
    try {
      const data = await action();
      setDetail(data);
      setEditedResponse(data.response?.finalResponse || data.response?.editedResponse || data.response?.suggestedResponse || '');
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo completar la accion.');
    } finally {
      setIsWorking(false);
    }
  };

  if (!detail && !error) {
    return (
      <AdminLayout>
        <Card>
          <CardContent className="text-center py-12 text-gray-500">Cargando reclamo...</CardContent>
        </Card>
      </AdminLayout>
    );
  }

  if (!detail) {
    return (
      <AdminLayout>
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold mb-4">Reclamo no encontrado</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <Link to="/admin/claims">
            <Button>Volver a bandeja</Button>
          </Link>
        </div>
      </AdminLayout>
    );
  }

  const { claim, analysis, response, documents } = detail;

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

  return (
    <AdminLayout>
      <div className="space-y-6 max-w-6xl mx-auto">
        <div className="flex items-center gap-4">
          <Link to="/admin/claims">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="size-4 mr-2" />
              Volver
            </Button>
          </Link>
        </div>

        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">Reclamo {claim.code}</h1>
            <p className="text-gray-600">Revisión de soporte con clasificación, contexto documental y respuesta sugerida.</p>
          </div>
          <Badge className={`${getStatusColor(claim.statusKey)} text-lg px-4 py-2`}>
            {CLAIM_STATUS_LABELS[claim.statusKey as keyof typeof CLAIM_STATUS_LABELS] || claim.status}
          </Badge>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="size-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {claim.requiresHumanReview && (
          <Alert variant="destructive">
            <AlertTriangle className="size-4" />
            <AlertDescription>
              <strong>Revisión humana obligatoria:</strong> valida datos del pedido, pago o seguridad antes de aprobar una respuesta final.
            </AlertDescription>
          </Alert>
        )}

        <div className="grid md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-5">
              <p className="text-xs text-gray-500">Cliente</p>
              <p className="font-semibold truncate">{claim.customerName}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5">
              <p className="text-xs text-gray-500">Pedido</p>
              <p className="font-semibold">{claim.orderCode}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5">
              <p className="text-xs text-gray-500">Prioridad</p>
              <p className="font-semibold">{claim.priority}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5">
              <p className="text-xs text-gray-500">Acción sugerida</p>
              <p className="font-semibold">
                {claim.requiresHumanReview ? 'Revisar antes de responder' : 'Aprobar si el texto es correcto'}
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="size-5" />
                  Mensaje del cliente
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-800 whitespace-pre-line">{claim.description}</p>
                <Separator className="my-4" />
                <div className="grid md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600">Categoria actual</p>
                    <p className="font-semibold">{claim.category}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Canal</p>
                    <p className="font-semibold">{claim.channel}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {analysis ? (
              <Card className="border-purple-200 bg-purple-50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Brain className="size-5 text-purple-600" />
                    Analisis del sistema inteligente
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid md:grid-cols-3 gap-4">
                    <div className="bg-white p-4 rounded-lg">
                      <p className="text-sm text-gray-600 mb-1">Categoria detectada</p>
                      <p className="font-semibold text-purple-900">{analysis.category}</p>
                    </div>
                    <div className="bg-white p-4 rounded-lg">
                      <p className="text-sm text-gray-600 mb-1">Nivel de confianza</p>
                      <p className="text-2xl font-bold text-blue-600">{(analysis.confidence * 100).toFixed(0)}%</p>
                    </div>
                    <div className="bg-white p-4 rounded-lg">
                      <p className="text-sm text-gray-600 mb-1">Prioridad asignada</p>
                      <p className="font-bold text-orange-600">{claim.priority}</p>
                    </div>
                  </div>
                  <div className="bg-white p-4 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Recomendacion</p>
                    <p className="text-gray-800">{analysis.recommendation}</p>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="pt-6 flex items-center justify-between">
                  <p className="text-gray-600">Este reclamo todavia no tiene analisis IA.</p>
                  <Button disabled={isWorking} onClick={() => id && runAction(() => analyzeClaim(id))}>
                    <RefreshCw className="size-4 mr-2" />
                    Analizar ahora
                  </Button>
                </CardContent>
              </Card>
            )}

            <Card className="border-blue-200 bg-blue-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="size-5 text-blue-600" />
                  Documentos recuperados (RAG)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {documents.length > 0 ? (
                  documents.map((doc) => (
                    <div key={`${doc.id}-${doc.fragment}`} className="bg-white p-4 rounded-lg border border-blue-200">
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-semibold text-blue-900">{doc.title}</h4>
                        <Badge variant="outline">{doc.type}</Badge>
                      </div>
                      <p className="text-sm text-gray-700">{doc.fragment}</p>
                      <p className="text-xs text-gray-500 mt-2">
                        Categoria: {doc.category} • Score: {Number(doc.score || 0).toFixed(3)}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-blue-900">
                    No hay documentos consultados. Puede ser un reclamo sin respuesta generada o con RAG desactivado.
                  </p>
                )}
              </CardContent>
            </Card>

            {!response && (
              <Card className="border-orange-200 bg-orange-50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="size-5 text-orange-600" />
                    Respuesta al cliente
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-orange-900">
                    Todavía no hay una respuesta sugerida para este reclamo. Genera una respuesta con el contexto disponible,
                    revísala y luego publícala para que el cliente la vea en Mis reclamos.
                  </p>
                  <Button disabled={isWorking} onClick={() => id && runAction(() => analyzeClaim(id))}>
                    <RefreshCw className="size-4 mr-2" />
                    Generar respuesta sugerida
                  </Button>
                </CardContent>
              </Card>
            )}

            {response && (
              <Card className="border-green-200">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="size-5 text-green-600" />
                    Respuesta al cliente
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {!isEditing ? (
                    <>
                      <div className="bg-green-50 p-4 rounded-lg">
                        <p className="whitespace-pre-line text-gray-800">
                          {response.finalResponse || response.editedResponse || response.suggestedResponse}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-3">
                        <Button
                          disabled={isWorking}
                          onClick={() => runAction(() => approveResponse(response.id, editedResponse || response.suggestedResponse))}
                          className="flex-1"
                        >
                          <CheckCircle className="size-4 mr-2" />
                          Enviar respuesta al cliente
                        </Button>
                        <Button onClick={() => setIsEditing(true)} variant="outline" className="flex-1">
                          <Edit className="size-4 mr-2" />
                          Editar respuesta
                        </Button>
                        <Button
                          disabled={isWorking}
                          onClick={() => id && runAction(() => updateClaimState(id, 'ESCALATED', 'Caso escalado desde panel full stack.'))}
                          variant="destructive"
                        >
                          <AlertTriangle className="size-4 mr-2" />
                          Escalar
                        </Button>
                        <Button
                          disabled={isWorking}
                          onClick={() => id && runAction(() => updateClaimState(id, 'CLOSED', 'Caso cerrado desde panel full stack.'))}
                          variant="outline"
                        >
                          <Lock className="size-4 mr-2" />
                          Cerrar
                        </Button>
                      </div>
                    </>
                  ) : (
                    <>
                      <Textarea
                        value={editedResponse}
                        onChange={(e) => setEditedResponse(e.target.value)}
                        rows={8}
                        className="resize-none"
                      />
                      <div className="flex gap-3">
                        <Button
                          disabled={isWorking || editedResponse.length < 5}
                          onClick={() => runAction(() => updateResponse(response.id, editedResponse))}
                          className="flex-1"
                        >
                          <CheckCircle className="size-4 mr-2" />
                          Guardar edicion
                        </Button>
                        <Button onClick={() => setIsEditing(false)} variant="outline">
                          Cancelar
                        </Button>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="size-5" />
                  Cliente
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-sm text-gray-600">Nombre</p>
                  <p className="font-semibold">{claim.customerName}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Email</p>
                  <p className="text-sm">{claim.customerEmail}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Package className="size-5" />
                  Pedido relacionado
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-sm text-gray-600">Codigo</p>
                  <p className="font-semibold">{claim.orderCode}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Responsable</p>
                  <p className="font-semibold">{claim.responsible || 'Agente de soporte'}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Metadatos</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <p className="text-gray-600">Fecha creacion</p>
                  <p className="font-semibold">{formatDateTime(claim.createdAt)}</p>
                </div>
                <div>
                  <p className="text-gray-600">Ultima actualizacion</p>
                  <p className="font-semibold">{formatDateTime(claim.updatedAt)}</p>
                </div>
                <div>
                  <p className="text-gray-600">Estado</p>
                  <Badge className={getStatusColor(claim.statusKey)}>
                    {CLAIM_STATUS_LABELS[claim.statusKey as keyof typeof CLAIM_STATUS_LABELS] || claim.status}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
