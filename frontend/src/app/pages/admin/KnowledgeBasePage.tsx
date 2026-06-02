import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { FileText, RefreshCw, CheckCircle, Search } from 'lucide-react';
import { getDocuments, reindexDocuments, DocumentsResponse } from '../../lib/api';
import { formatDateTime } from '../../lib/utils';
import AdminLayout from '../../components/AdminLayout';

export default function KnowledgeBasePage() {
  const [data, setData] = useState<DocumentsResponse | null>(null);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [isWorking, setIsWorking] = useState(false);

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
              <CardTitle className="text-sm font-medium">Fragmentos RAG</CardTitle>
              <RefreshCw className="size-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{data?.index.fragmentos || 0}</div>
              <p className="text-xs text-gray-500 mt-1">Vectorizados con TF-IDF</p>
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
              La recuperación documental usa un índice local TF-IDF para encontrar políticas y procedimientos relevantes.
              La carga de nuevos documentos todavía no está implementada desde la interfaz.
            </p>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
