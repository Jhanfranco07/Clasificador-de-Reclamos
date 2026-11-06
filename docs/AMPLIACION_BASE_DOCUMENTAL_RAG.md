# Ampliación de la base documental y recuperación RAG

Trabajo aislado en el worktree hermano `smartclaim_rag`, rama `feature/ampliacion-base-documental-rag`, desde `main` en `86691f7da69554ab5173afd5cb0bd5464d5169e4`. El worktree de desarrollo tenía cambios locales. Las verificaciones usaron SQLite desechable y deshabilitaron la configuración de producción y las llamadas a OpenAI.

## Catálogo académico

`data/documentos_academicos.json` contiene 42 procedimientos simulados de SmartClaim AI. Cada registro incluye ID externo, título, tipo, categoría, texto, procedencia, versión, fecha, vigencia y declaraciones estructuradas de revisión humana, compensación y protección de datos. Estas políticas son académicas.

| Categoría | Seed limpio | Nuevos | Total |
|---|---:|---:|---:|
| Producto incompleto | 1 | 6 | 7 |
| Producto incorrecto | 1 | 6 | 7 |
| Retraso de pedido | 3 | 6 | 9 |
| Cobro indebido | 1 | 6 | 7 |
| Fraude o seguridad | 2 | 6 | 8 |
| Problema con tarjeta | 1 | 6 | 7 |
| Soporte general | 9 | 6 | 15 |
| Total | 18 | 42 | 60 |

El archivo SQLite versionado arranca con 6 documentos. Las cifras de evaluación corresponden a una base limpia inicializada con el esquema y seed actuales. En una base preexistente, el simulador muestra los conflictos que requieren revisión. Las reglas de texto del importador detectan expresiones concretas y las declaraciones estructuradas incompatibles. La consistencia semántica de la prosa sigue sujeta a revisión humana.

## Importar y reindexar

Desde la raíz del repositorio, usa una SQLite de pruebas ya inicializada y conserva una copia del archivo antes de probar la importación.

```powershell
$env:DB_PROVIDER = 'sqlite'
$env:APP_ENV = 'test'
$env:DATABASE_URL = ''
$env:OPENAI_API_KEY = ''
$env:PYTHON_DOTENV_DISABLED = '1'
python -m scripts.import_documents --sqlite RUTA_A_SQLITE_DE_PRUEBA --dry-run
python -m scripts.import_documents --sqlite RUTA_A_SQLITE_DE_PRUEBA
python -m scripts.build_rag_index --sqlite RUTA_A_SQLITE_DE_PRUEBA
```

La simulación abre SQLite en modo de solo lectura. La carga registra las filas válidas en `documentos_base` y sus metadatos en `documentos_importados` dentro de la misma transacción. Un ID repetido con el mismo contenido y metadatos se omite. Un ID repetido con cambios se rechaza y requiere revisión, igual que los duplicados por título o contenido. Los documentos nuevos quedan pendientes hasta la sincronización.

`POST /api/documents/reindex` requiere el rol administrador y ejecuta la misma sincronización local. El proceso conserva los fragmentos válidos y sus IDs, elimina filas obsoletas o duplicadas y genera las faltantes. El ajuste TF-IDF se verifica antes de confirmar la transacción. El resultado informa el proveedor y el total de fragmentos. Los archivos históricos de `vector_store` permanecen como artefactos de la versión base. TF-IDF ajusta y reutiliza en memoria un índice ligado al corpus ordenado de la base actual.

## PDF administrativo

Selecciona **Importar PDF para revisión** en **Base documental**. La interfaz envía el binario a `POST /api/documents/pdf-preview`. Revisa el texto editable, completa título, tipo y categoría, y guarda con el flujo normal de `POST /api/documents`. El formulario admite también el registro manual. La vista previa no escribe documentos y el servidor descarta el binario una vez extraído el texto. El registro utiliza los campos y la fecha del documento del sistema.

Se fijó `pypdf==7.0.0` por su extracción local sin OCR y su configuración de presupuestos de análisis y descompresión. Se comprueban el tipo declarado y la cabecera PDF, y se rechazan PDF corruptos, cifrados o sin texto legible. Los límites iniciales son 4 MiB, 25 páginas y 100 000 caracteres extraídos. Los dos primeros se configuran con `DOCUMENT_PDF_MAX_BYTES` y `DOCUMENT_PDF_MAX_PAGES`. El endpoint prescinde del nombre del archivo. El texto se presenta como texto editable y las instrucciones del modelo delimitan su uso como evidencia no confiable. Una extracción exitosa no verifica la autenticidad ni el contenido de una política.

## Diagnóstico reproducido

1. Copia el archivo SQLite del commit base a una ruta temporal. El documento `4` y su fragmento contienen el manual de fraude.
2. Aplica `database/schema.sql` y `database/seed_data.sql` **del commit base** a esa copia. Consulta `SELECT d.titulo, f.texto_fragmento FROM documentos_base d JOIN fragmentos_documento f USING (id_documento) WHERE d.id_documento = 4`.
3. El resultado observado fue el título **FAQ sobre pedido incompleto o productos faltantes** con texto que empieza por *Los casos de acceso no reconocido, pedidos no autorizados o sospecha de fraude*. El seed original reemplaza el documento por ID y solo crea fragmentos para IDs sin fragmentos. El reindexado anterior ajustaba TF-IDF sobre esas filas existentes. Además, el índice versionado se generó contra la asignación antigua de IDs.
4. Los seeds actuales conservan documentos existentes y la sincronización reconstruye los fragmentos desde su contenido. El caso de regresión introduce el cruce, comprueba que se rechace, actualiza la FAQ y verifica que el título, ID, categoría, texto y orden permanezcan vinculados tras reindexar. Las citas históricas guardaban texto pero mostraban el título actual por JOIN. El detalle omite una cita cuando su texto ya no se puede vincular con el contenido actual del documento.

La fragmentación usa ventanas de 70 palabras con 15 de solapamiento, numeradas desde 1. Cada resultado nuevo incorpora el ID del documento, el ID y orden del fragmento, el título, el tipo, la categoría y la fecha documental. Los resultados semánticos se cotejan con el fragmento vigente antes de usarse. Los modos se identifican como `openai_json`, `supabase_pgvector` y `tfidf`. TF-IDF usa el texto del reclamo, restringe resultados a la categoría indicada y evita repetir documentos entre los primeros resultados. Un caso sin coincidencias por encima del umbral queda para revisión humana.

## Evaluación reproducible

```powershell
python -m scripts.evaluate_rag
python -m pytest -q
npm --prefix frontend ci
npm --prefix frontend run build
```

El evaluador crea y elimina una base temporal, comprueba la simulación, importa los documentos dos veces y evalúa `data/consultas_rag.json`. Las 60 consultas usan la categoría anotada y cuentan como acierto solo los IDs esperados. Precisión@3 divide por tres incluso cuando se devuelven menos de tres resultados. Los casos sin evidencia se contabilizan por separado. Es una prueba del recuperador y no mide el clasificador. Las consultas y los documentos se prepararon juntos para esta demostración, por lo que las cifras son descriptivas del conjunto.

### Resultados de la evaluación local

| Métrica | Resultado |
|---|---:|
| Recall@3 | 64,29 % |
| Precisión@3 | 21,43 % |
| Primer resultado pertinente | 46,43 % |
| Sin evidencia detectada | 3 de 4 |
| Latencia mediana local | 2,14 ms |
| Fragmentos | 76 |

Recall@3 por categoría, en orden de la tabla del catálogo, fue 62,5 %, 25 %, 50 %, 75 %, 87,5 %, 87,5 % y 62,5 %. El umbral léxico admitió un falso positivo en los cuatro casos sin evidencia.

### Verificación de interfaz y dependencias

Se sirvió la compilación con `vite preview` en `127.0.0.1:15173` y se levantó Uvicorn en `127.0.0.1:18100` con SQLite temporal. Se configuraron `VITE_API_URL`, `CORS_ORIGINS` y `E2E_BASE_URL` con esas direcciones. Los casos Playwright usan cuentas de demostración sembradas en la SQLite temporal. La prueba de documentos usa un ancho de 390 px y comprueba registro manual, rechazo, espera de la vista previa, carga válida, guardado y búsqueda. La prueba de agente verifica la redirección de la ruta administrativa.

```powershell
cd frontend
npx --yes --package typescript@5.8.3 tsc --noEmit --allowImportingTsExtensions --jsx react-jsx --moduleResolution bundler --module esnext --target es2022 --skipLibCheck --types vite/client src/main.tsx
npm run test:e2e -- --workers=1 --timeout=90000 --reporter=line
npm audit --omit=dev
```

La prueba de consola informó 42 creaciones en simulación, 42 inserciones en la primera carga y 42 omisiones en la segunda. El reindexado informó 60 documentos, 76 fragmentos y cero embeddings generados.

El backend completó 29 pruebas y Playwright completó 6 contra la compilación. TypeScript y la compilación de Vite finalizaron correctamente. Una corrida intermedia de Playwright en el servidor de desarrollo registró timeouts al abrir Chromium y al cargar pantallas. La corrida sobre la compilación completó los seis casos.

La auditoría de ejecución quedó en cero después de actualizar en el lockfile React Router a 7.18.5 y DOMPurify a 3.4.17 dentro de los rangos existentes. La auditoría completa mantiene siete avisos de desarrollo presentes en el commit base. El motor de Docker Desktop no estaba disponible para levantar un PostgreSQL local con pgvector.

## Operación posterior

Revisa los conflictos del simulador antes de importar. Sobre una SQLite antigua, inspecciona los documentos conservados por ID antes de incorporar el seed limpio como catálogo base. Para PostgreSQL, verifica primero el DDL, los filtros de recuperación y el rollback en una instancia aislada con pgvector. La generación semántica requiere autorización separada y se ejecuta fuera de la interfaz administrativa. La prueba local no utilizó PostgreSQL, Supabase productivo ni embeddings pagados.

Referencias de implementación

- [Extracción de texto y límites de pypdf](https://pypdf.readthedocs.io/en/latest/user/extract-text.html)
- [Extensión pgvector en Supabase](https://supabase.com/docs/guides/database/extensions/pgvector)
