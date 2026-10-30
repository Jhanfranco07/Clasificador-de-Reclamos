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
import { ConfigResponse, getConfig, saveConfig } from '../../lib/api';
import AdminLayout from '../../components/AdminLayout';

export default function AIConfigPage() {
  const [ragEnabled, setRagEnabled] = useState(true);
  const [humanReview, setHumanReview] = useState(true);
  const [confidenceThreshold, setConfidenceThreshold] = useState([85]);
  const [maxDocuments, setMaxDocuments] = useState('3');
  const [configuration, setConfiguration] = useState<ConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setMessage('');
    getConfig()
      .then((config) => {
        if (!active) return;
        setRagEnabled(config.useRag);
        setHumanReview(config.humanReviewRequired);
        setConfidenceThreshold([config.confidenceThreshold * 100]);
        setMaxDocuments(String(config.maxDocuments));
        setConfiguration(config);
      })
      .catch((err) => { if (active) { setConfiguration(null); setError(err instanceof Error ? err.message : 'No se pudo cargar la configuración.'); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [reload]);

  const handleSave = async () => {
    if (!configuration || loading || isSaving) return;
    setError('');
    setMessage('');
    setIsSaving(true);
    try {
      const desired = {
        config_id: configuration.id,
        confidence_threshold: confidenceThreshold[0] / 100,
        human_review_required: humanReview,
        use_rag: ragEnabled,
        max_documents: Number(maxDocuments),
      };
      await saveConfig(desired);
      const config = await getConfig();
      if (config.id !== desired.config_id || Math.abs(config.confidenceThreshold - desired.confidence_threshold) > 0.000001
          || config.humanReviewRequired !== desired.human_review_required || config.useRag !== desired.use_rag
          || config.maxDocuments !== desired.max_documents) {
        throw new Error('El guardado no coincide con la configuración consultada. Recarga y verifica los valores.');
      }
      setConfiguration(config);
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
            La clasificación es local y puede combinar ML con reglas. La generación y recuperación ejecutadas se informan según la última traza disponible; disponer de un artefacto o proveedor no acredita su ejecución.
          </AlertDescription>
        </Alert>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertDescription>{error} <Button variant="outline" size="sm" onClick={() => setReload((value) => value + 1)} disabled={isSaving}>Recargar configuración</Button></AlertDescription>
          </Alert>
        )}
        {message && (
          <Alert>
            <Save className="size-4" />
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        )}

        {loading && <p role="status">Cargando configuración...</p>}
        {configuration && <div className="rounded-lg border p-4 space-y-2 break-words">
          <p>Configuración efectiva: #{configuration.id} · se utiliza el mayor ID activo.</p>
          {configuration.activeCount > 1 && <p role="alert">Hay {configuration.activeCount} configuraciones activas heredadas. Se conserva la selección por mayor ID; su conciliación sigue pendiente.</p>}
          <p>Modelo configurado: {configuration.model || 'Sin metadato'}</p>
          <p>Artefacto clasificador local: {configuration.runtime.classifierArtifactPresent ? 'presente (no acredita ejecución)' : 'ausente; el clasificador dispone de respaldo por reglas'}</p>
          {configuration.runtime.lastExecution ? <>
            <p>Última clasificación ejecutada registrada: {configuration.runtime.lastExecution.classifierModel}</p>
            <p>Generación registrada: {configuration.runtime.lastExecution.generationStrategy || 'No consta'} · Recuperación: {configuration.runtime.lastExecution.retrievalStrategy || 'No consta'}</p>
            <p>OpenAI utilizado en esa ejecución: {configuration.runtime.lastExecution.openaiUsed ? 'Sí' : 'No'} · {configuration.runtime.lastExecution.recordedAt} · {configuration.runtime.lastExecution.outcome}</p>
          </> : <p>No hay una ejecución reciente verificable en las trazas consultadas.</p>}
        </div>}

        <fieldset className="space-y-6 min-w-0" disabled={loading || isSaving || !configuration} onChange={() => setMessage('')}>

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
              <Switch id="rag-enabled" checked={ragEnabled} onCheckedChange={(value) => { setRagEnabled(value); setMessage(''); }} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="max-documents">Número de documentos a recuperar</Label>
              <Select value={maxDocuments} onValueChange={(value) => { setMaxDocuments(value); setMessage(''); }} disabled={!ragEnabled || loading || isSaving || !configuration}>
                <SelectTrigger id="max-documents">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => <SelectItem key={n} value={String(n)}>{n} documento(s)</SelectItem>)}
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
              <Label>Modelo de clasificación configurado</Label>
              <p className="break-words">{configuration?.model || 'No disponible'}</p>
              <p className="text-xs text-gray-500">
                Metadato histórico de configuración. Esta pantalla no permite cambiar el motor de clasificación; consulta la ejecución registrada por separado.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Umbral mínimo de confianza</Label>
                <span className="text-sm font-semibold">{confidenceThreshold[0]}%</span>
              </div>
              <Slider aria-label="Umbral mínimo de confianza" value={confidenceThreshold} onValueChange={(value) => { setConfidenceThreshold(value); setMessage(''); }} min={0} max={100} step={1} disabled={loading || isSaving || !configuration} />
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
              <Switch id="human-review" checked={humanReview} onCheckedChange={(value) => { setHumanReview(value); setMessage(''); }} />
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button onClick={handleSave} size="lg" className="gap-2" disabled={isSaving}>
            <Save className="size-4" />
            {isSaving ? 'Guardando...' : 'Guardar configuración'}
          </Button>
        </div>
        </fieldset>
      </div>
    </AdminLayout>
  );
}
