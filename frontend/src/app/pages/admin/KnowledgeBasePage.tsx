import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { FileText, RefreshCw, CheckCircle, Search, Plus, Pencil, Trash2 } from 'lucide-react';
import { createDocument, deleteDocument, getDocuments, reindexDocuments, updateDocument, DocumentsResponse } from '../../lib/api';
import { formatDateTime } from '../../lib/utils';
import AdminLayout from '../../components/AdminLayout';

export default function KnowledgeBasePage() {
  const [data, setData] = useState<DocumentsResponse | null>(null);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [isWorking, setIsWorking] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: '',
    type: 'FAQ',
    category: 'Soporte general',
    content: '',
  });

  const loadDocuments = async () => {
    setError('');
    try {
      setData(await getDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar la base documental.');
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleReindex = async () => {
    setIsWorking(true);
    setError('');
    try {
      await reindexDocuments();
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo reindexar.');
    } finally {
      setIsWorking(false);
    }
  };

  const resetForm = () => {
    setEditingId(null);
    setForm({ title: '', type: 'FAQ', category: 'Soporte general', content: '' });
  };

  const handleSaveDocument = async () => {
    if (form.title.trim().length < 3 || form.content.trim().length < 20) {
      setError('Completa titulo y contenido del documento antes de guardar.');
      return;
    }
    setIsWorking(true);
    setError('');
    try {
      const payload = {
        title: form.title.trim(),
        type: form.type,
        category: form.category.trim(),
        content: form.content.trim(),
      };
      setData(editingId ? await updateDocument(editingId, payload) : await createDocument(payload));
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar el documento.');
    } finally {
      setIsWorking(false);
    }
  };

  const handleEditDocument = (doc: DocumentsResponse['items'][number]) => {
    setEditingId(doc.id);
    setForm({ title: doc.title, type: doc.type, category: doc.category, content: doc.content });
  };

  const handleDeleteDocument = async (id: string) => {
    setIsWorking(true);
    setError('');
    try {
      setData(await deleteDocument(id));
      if (editingId === id) resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo desactivar el documento.');
    } finally {
      setIsWorking(false);
    }
  };

  const docs = data?.items || [];
  const filteredDocs = docs.filter((doc) =>
    `${doc.title} ${doc.category} ${doc.content}`.toLowerCase().includes(query.toLowerCase())
  );
  const indexedDocs = docs.filter((doc) => doc.indexStatus === 'INDEXADO').length;
  const totalDocs = docs.length;

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Base documental</h1>
            <p className="text-gray-600">
              Documentos internos usados para fundamentar respuestas y procedimientos de soporte.
            </p>
          </div>
          <Button variant="outline" onClick={handleReindex} disabled={isWorking}>
            <RefreshCw className="size-4 mr-2" />
            {isWorking ? 'Reindexando...' : 'Reindexar'}
          </Button>
        </div>

        {error && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="py-4 text-red-700">{error}</CardContent>
          </Card>
        )}

        <div className="grid md:grid-cols-3 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total documentos</CardTitle>
              <FileText className="size-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalDocs}</div>
              <p className="text-xs text-gray-500 mt-1">En la base de conocimiento</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Indexados</CardTitle>
              <CheckCircle className="size-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{indexedDocs}</div>
              <p className="text-xs text-gray-500 mt-1">Disponibles para recuperación</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Base vectorial</CardTitle>
              <RefreshCw className="size-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{data?.index.embeddings || data?.index.fragmentos || 0}</div>
              <p className="text-xs text-gray-500 mt-1">
                {data?.index.provider === 'supabase_pgvector' ? 'Supabase pgvector' : 'TF-IDF local'}
              </p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardContent className="pt-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-gray-400" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Buscar en la base documental..."
                className="pl-10"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{editingId ? 'Editar documento' : 'Agregar documento'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-3 gap-4">
              <Input
                value={form.title}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                placeholder="Titulo del documento"
              />
              <Select value={form.type} onValueChange={(value) => setForm((current) => ({ ...current, type: value }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="FAQ">FAQ</SelectItem>
                  <SelectItem value="POLITICA">Politica</SelectItem>
                  <SelectItem value="PROCEDIMIENTO">Procedimiento</SelectItem>
                  <SelectItem value="MANUAL">Manual</SelectItem>
                </SelectContent>
              </Select>
              <Input
                value={form.category}
                onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}
                placeholder="Categoria asociada"
              />
            </div>
            <Textarea
              value={form.content}
              onChange={(event) => setForm((current) => ({ ...current, content: event.target.value }))}
              placeholder="Contenido que alimentara las respuestas del sistema"
              rows={5}
            />
            <div className="flex flex-wrap gap-3">
              <Button onClick={handleSaveDocument} disabled={isWorking}>
                <Plus className="size-4 mr-2" />
                {editingId ? 'Guardar cambios' : 'Agregar documento'}
              </Button>
              {editingId && (
                <Button variant="outline" onClick={resetForm}>
                  Cancelar edicion
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {filteredDocs.map((doc) => (
            <Card key={doc.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4 flex-1">
                    <div className="size-12 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <FileText className="size-6 text-blue-600" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-semibold text-lg">{doc.title}</h3>
                        <Badge variant="secondary">{doc.type}</Badge>
                        {doc.indexStatus === 'INDEXADO' && (
                          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                            <CheckCircle className="size-3 mr-1" />
                            Indexado
                          </Badge>
                        )}
                      </div>
                      <p className="text-gray-700 mb-3">{doc.content}</p>
                      <div className="flex items-center gap-4 text-sm text-gray-500">
                        <span>Categoría: {doc.category}</span>
                        <span>·</span>
                        <span>Actualizado: {formatDateTime(doc.updatedAt)}</span>
                      </div>
                      <div className="flex flex-wrap gap-2 mt-4">
                        <Button size="sm" variant="outline" onClick={() => handleEditDocument(doc)}>
                          <Pencil className="size-4 mr-2" />
                          Editar
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleDeleteDocument(doc.id)}>
                          <Trash2 className="size-4 mr-2" />
                          Desactivar
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-blue-900 mb-2">Sobre el sistema RAG</h3>
            <p className="text-sm text-blue-800">
              La recuperación documental usa Supabase pgvector con embeddings neuronales cuando PostgreSQL está activo.
              En modo local conserva TF-IDF como respaldo para que la demo funcione sin servicios externos.
              Puedes agregar o editar documentos y luego reindexar para que el motor RAG los use en nuevas respuestas.
            </p>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}

