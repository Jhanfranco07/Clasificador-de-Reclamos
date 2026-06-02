import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/label';
import { Switch } from '../../components/ui/switch';
import { Slider } from '../../components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { Brain, Save, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { getConfig, saveConfig } from '../../lib/api';
import AdminLayout from '../../components/AdminLayout';

export default function AIConfigPage() {
  const [ragEnabled, setRagEnabled] = useState(true);
  const [humanReview, setHumanReview] = useState(true);
  const [confidenceThreshold, setConfidenceThreshold] = useState([85]);
  const [maxDocuments, setMaxDocuments] = useState('3');
  const [model, setModel] = useState('modelo_ml_tfidf_logistic_regression');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    getConfig()
      .then((config) => {
        setRagEnabled(config.useRag);
        setHumanReview(config.humanReviewRequired);
        setConfidenceThreshold([Math.round(config.confidenceThreshold * 100)]);
        setMaxDocuments(String(config.maxDocuments));
        setModel(config.model || 'modelo_ml_tfidf_logistic_regression');
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar la configuración.'));
  }, []);

  const handleSave = async () => {
    setError('');
    setMessage('');
    setIsSaving(true);
    try {
      const config = await saveConfig({
        confidence_threshold: confidenceThreshold[0] / 100,
        human_review_required: humanReview,
        use_rag: ragEnabled,
        max_documents: Number(maxDocuments),
      });
      setMessage(`Configuración guardada. RAG: ${config.useRag ? 'activo' : 'inactivo'}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar la configuración.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6 max-w-4xl mx-auto">
        <div>
          <h1 className="text-3xl font-bold mb-2">Configuración del sistema IA</h1>
          <p className="text-gray-600">
            Parámetros de clasificación, recuperación documental y revisión humana.
          </p>
        </div>

        <Alert>
          <Brain className="size-4" />
          <AlertDescription>
            El modelo actual usa TF-IDF, regresión logística y reglas de negocio para apoyar el flujo de soporte.
          </AlertDescription>
        </Alert>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {message && (
          <Alert>
            <Save className="size-4" />
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Sistema RAG</CardTitle>
            <CardDescription>
              Controla si se recuperan documentos antes de generar la respuesta sugerida.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="rag-enabled">Habilitar RAG</Label>
                <p className="text-sm text-gray-500">
                  Si está apagado, la respuesta usa una plantilla básica sin documentos consultados.
                </p>
              </div>
              <Switch id="rag-enabled" checked={ragEnabled} onCheckedChange={setRagEnabled} />
            </div>

            <div className="space-y-2">
              <Label>Número de documentos a recuperar</Label>
              <Select value={maxDocuments} onValueChange={setMaxDocuments} disabled={!ragEnabled}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 documento</SelectItem>
                  <SelectItem value="2">2 documentos</SelectItem>
                  <SelectItem value="3">3 documentos</SelectItem>
                  <SelectItem value="5">5 documentos</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Clasificacion automatica</CardTitle>
            <CardDescription>
              Parámetros del modelo de clasificación de reclamos.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label>Modelo de clasificación</Label>
              <Select value={model} onValueChange={setModel} disabled>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="modelo_ml_tfidf_logistic_regression">Local - TF-IDF + Logistic Regression</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-500">
                El selector queda bloqueado porque no hay proveedor externo configurado.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Umbral mínimo de confianza</Label>
                <span className="text-sm font-semibold">{confidenceThreshold[0]}%</span>
              </div>
              <Slider value={confidenceThreshold} onValueChange={setConfidenceThreshold} min={50} max={95} step={5} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Revisión humana</CardTitle>
            <CardDescription>
              Define si todo reclamo analizado debe pasar por un agente.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="human-review">Revisión humana obligatoria</Label>
                <p className="text-sm text-gray-500">
                  Recomendado cuando un agente debe validar la respuesta antes de enviarla.
                </p>
              </div>
              <Switch id="human-review" checked={humanReview} onCheckedChange={setHumanReview} />
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button onClick={handleSave} size="lg" className="gap-2" disabled={isSaving}>
            <Save className="size-4" />
            {isSaving ? 'Guardando...' : 'Guardar configuración'}
          </Button>
        </div>
      </div>
    </AdminLayout>
  );
}
