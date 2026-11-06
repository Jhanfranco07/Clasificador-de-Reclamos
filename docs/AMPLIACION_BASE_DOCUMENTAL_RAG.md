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


## Fase 2. Optimización y validación aislada

Se continuó en el worktree `smartclaim_rag`, rama `feature/ampliacion-base-documental-rag`, desde `2ba33e66764635d351d5e51254252a9ac6226e96`. El worktree de desarrollo mantenía cambios locales. Las pruebas utilizaron SQLite temporal y un PostgreSQL local nuevo, sin datos ni credenciales de producción.

### Recuperación y evaluación

Se reprodujeron las métricas originales antes de modificar el algoritmo. Los fallos incluían variantes morfológicas, errores ortográficos, coincidencias por palabras funcionales y vocabulario ausente del catálogo. Por ejemplo, «Pedí pizza familiar y llegó mediana» carece de términos de tamaño compartidos con el documento esperado. «Programé de doce a una y llegó a las dos» obtuvo una política sobre localizar el destino. La consulta de la capital de Noruega produjo una coincidencia sin evidencia.

La nueva representación combina 60 % de similitud por palabras y 40 % por n-gramas de caracteres de longitud 3–5 dentro de palabras. Normaliza acentos y palabras funcionales, conserva la negación, mantiene el filtro por categoría y devuelve como máximo un fragmento por documento. Usa un umbral de 0,075. El evaluador conserva los modos anteriores, emite las consultas fallidas con los títulos realmente recuperados y mide latencia con caché caliente.

| Variante en las 60 consultas originales | Recall@3 | Precisión@3 | Acierto primero | Sin evidencia |
|---|---:|---:|---:|---:|
| Línea base | 64,29 % | 21,43 % | 46,43 % | 3/4 |
| Solo palabras normalizadas, umbral 0,08 | 53,57 % | 17,86 % | 42,86 % | 4/4 |
| Híbrida conservadora, umbral 0,10 | 62,50 % | 20,83 % | 50,00 % | 4/4 |
| Híbrida seleccionada, umbral 0,075 | 66,07 % | 22,02 % | 50,00 % | 4/4 |

La mediana y el p95 de la línea base reproducida fueron 1,98 y 2,52 ms. En la variante seleccionada fueron 2,83 y 3,49 ms. La medición histórica de fase 1 fue 2,14 ms de mediana.

Las 28 consultas adicionales se redactaron antes de comparar variantes, con tres casos pertinentes y un caso fuera de dominio por categoría. Las etiquetas del conjunto original se conservaron. Se ejecutaron línea base e híbrida después de seleccionar el umbral con el conjunto original. Las consultas adicionales se construyeron con conocimiento del catálogo y no representan tráfico real ni una evaluación ciega externa.

| Métrica en 28 consultas independientes | Línea base | Híbrida |
|---|---:|---:|
| Recall@3 | 57,14 % | 57,14 % |
| Precisión@3 | 19,05 % | 19,05 % |
| Acierto primero | 38,10 % | 42,86 % |
| Sin evidencia | 3/7 | 6/7 |
| Latencia mediana | 2,00 ms | 2,73 ms |
| Latencia p95 | 3,10 ms | 3,52 ms |

| Categoría | Recall@3 original base → híbrida | Recall@3 independiente base → híbrida |
|---|---:|---:|
| Producto incompleto | 62,5 → 62,5 % | 66,7 → 33,3 % |
| Producto incorrecto | 25 → 25 % | 66,7 → 66,7 % |
| Retraso de pedido | 50 → 62,5 % | 0 → 0 % |
| Cobro indebido | 75 → 62,5 % | 66,7 → 66,7 % |
| Fraude o seguridad | 87,5 → 87,5 % | 66,7 → 66,7 % |
| Problema con tarjeta | 87,5 → 100 % | 66,7 → 66,7 % |
| Soporte general | 62,5 → 62,5 % | 66,7 → 100 % |

Se mantuvo la variante híbrida por su mejor abstención y primer resultado con el mismo Recall@3 global independiente. El Recall@3 independiente quedó por debajo de 0,80. Los fallos incluyen retrasos descritos con expresiones de horario o dirección sin vocabulario documental compartido y faltantes descritos solo mediante cantidades. La mejora independiente se concentra en abstención y primer resultado.

```powershell
python -m scripts.evaluate_rag --mode baseline
python -m scripts.evaluate_rag --mode words
python -m scripts.evaluate_rag --mode hybrid-strict
python -m scripts.evaluate_rag --mode hybrid
python -m scripts.evaluate_rag --mode baseline --cases data/consultas_rag_independientes.json
python -m scripts.evaluate_rag --mode hybrid --cases data/consultas_rag_independientes.json
```

### Catálogo e integridad

Se cotejaron 60 documentos y 76 fragmentos. El evaluador verifica IDs únicos, pertenencia, orden, texto exacto normalizado, título, categoría y fecha de actualización para todos los fragmentos. Los 42 importados conservan su versión y procedencia en `documentos_importados`. La revisión distinguió guías generales del seed y procedimientos específicos con escenarios relacionados, como doble cobro, retención bancaria y cobro definitivo. Las compensaciones quedan sujetas a revisión y el catálogo académico evita solicitar secretos de pago. La regla del seed distingue mensajes informativos de decisiones finales, y la guía de pedidos fríos reconoce que la categoría depende de la causa. Un cribado léxico de pares encontró 60 títulos únicos y una similitud máxima de 0,238 entre documentos distintos. La similitud léxica se usó como ayuda de revisión, sin inferir equivalencia semántica. El caso histórico de la FAQ se conserva como regresión y también se comprobó la sustitución del fragmento obsoleto en PostgreSQL.

### PostgreSQL y pgvector

Docker Desktop estaba sin motor. Se inició PostgreSQL 18 en un clúster temporal para comprobar la opción nativa. Esa instalación carecía de pgvector. Se instaló PostgreSQL 16.15 y pgvector 0.8.6 en un prefijo local ignorado de conda-forge, y se verificó `CREATE EXTENSION vector` en un clúster separado en loopback. El DSN de prueba requiere `127.0.0.1`, puerto explícito y una base de nombre `smartclaim_test` o con ese prefijo. Cada prueba de integración crea y elimina su propia base temporal. El usuario de pruebas necesita permisos para crear bases y la extensión.

```powershell
$env:SMARTCLAIM_TEST_PG_DSN = 'host=127.0.0.1 port=55479 dbname=smartclaim_test user=smartclaim_test'
python -m pytest -q tests/test_pgvector_integration.py
```

Para reproducir la instalación aislada de Windows se puede crear un prefijo desechable con `micromamba create -p RUTA_TEMPORAL -c conda-forge postgresql=16.15 pgvector=0.8.6`. Inicializa un directorio de datos nuevo con `initdb`, enlaza `pg_ctl` a `127.0.0.1` en un puerto libre y crea la base vacía `smartclaim_test`. Para cargarla manualmente, usa un proceso de shell de pruebas con `APP_ENV=test`, `DB_PROVIDER=postgres` y `DATABASE_URL` igual al DSN local antes de llamar `python -c "from database.db_connection import init_db; init_db()"`.

En una base de pruebas que ya tenga aplicado el esquema y el seed:

```powershell
python -m scripts.import_documents --postgres-test --dry-run
python -m scripts.import_documents --postgres-test
```

La importación simulada dejó el esquema intacto. La carga pasó de 18 a 60 documentos, se repitió sin nuevas filas y un error de restricción revirtió la transacción de prueba completa. El seed avanza la secuencia documental al mayor ID persistido y evita sobrescribir IDs existentes. Se verificaron la columna `vector(1536)`, las relaciones documento–fragmento–embedding y el índice IVFFlat del esquema. Para este catálogo pequeño, la consulta usa distancia coseno exacta sobre los candidatos compatibles, elimina repetidos por documento y coteja IDs, modelo, categoría y metadatos antes de usar el resultado. No se midió el uso de IVFFlat como estrategia de ranking aproximado.

Los vectores sintéticos comprobaron dimensión, similitud, filtros, metadatos, índice vacío, embeddings faltantes, resultados bajo umbral, excepción de búsqueda y eliminación de embeddings obsoletos. El fallback reutiliza la lectura verificada del catálogo y reporta `tfidf` como proveedor. Si el catálogo completo no responde, la recuperación queda sin evidencia. La excepción vectorial se registra sin ocultarla. Las pruebas sintéticas verifican la integración técnica y no miden pertinencia semántica.

### Evaluación semántica con autorización futura

Usa un clúster local de pruebas y un proyecto de OpenAI separado con presupuesto explícito. Importa el mismo catálogo, sincroniza los fragmentos y configura `OPENAI_EMBEDDING_MODEL=text-embedding-3-small` y `ENABLE_PGVECTOR_RAG=true`. Ejecuta `construir_indice_pgvector(forzar=True)` en ese entorno después de autorizar el consumo. Registra el uso de cada llamada de embeddings mediante `response.usage.total_tokens` en un cliente de evaluación, separando indexación, consultas y reintentos. Calcula la estimación antes de ejecutar como tokens estimados por tarifa vigente por millón, y el consumo real con los tokens devueltos por la API y el cargo del proyecto. Evalúa las mismas consultas con TF-IDF directo, pgvector y pgvector forzado a fallback. Registra el proveedor efectivo y latencia de extremo a extremo. Esta fase no generó embeddings pagados ni registró métricas semánticas.

### PDF, seguridad y regresiones

Se reutilizó el extractor pypdf con presupuestos de bytes, páginas, análisis, descompresión y texto. Las pruebas cubren PDF con texto, multipágina, caracteres acentuados, vacío, imagen sin texto, corrupto, cifrado, contenido ajeno a PDF y límites. El panel muestra la extracción, permite cancelar y editar la vista previa, y ofrece categorías válidas. La interfaz rechaza una extensión distinta de PDF y la API valida la firma binaria. La API rechaza títulos o contenidos repetidos entre documentos activos, con comparación normalizada bajo el mismo bloqueo que la escritura. El backend verificó que un agente no pueda escribir, previsualizar ni reindexar con llamadas directas. El texto de un documento sigue siendo evidencia no confiable y las respuestas requieren revisión humana.

Se aplicaron actualizaciones puntuales a FastAPI, Starlette y pytest tras detectar avisos en Starlette y pytest. La auditoría final de Python con `pip-audit -r requirements.txt` y la auditoría de ejecución de npm con `npm audit --omit=dev` no informaron vulnerabilidades conocidas. La auditoría npm completa mantiene siete avisos de dependencias de desarrollo de la fase anterior. Starlette emite una advertencia de deprecación por el uso de httpx en TestClient.

La verificación final completó 35 pruebas de backend, incluidas tres pruebas de destino local y pgvector, y seis de Playwright contra la compilación de Vite. Pasaron TypeScript y la compilación. La regresión de reclamos verificó análisis, citas, edición, escalamiento, envío e historial. La prueba en navegador incluyó vista móvil, validación de extensión, cancelación, registro, búsqueda y reindexación. El smoke test confirmó el acceso de las tres cuentas ficticias y los 42 documentos añadidos en la demostración local.

### Demostración local y posible entorno remoto

Instala los requisitos del backend en un entorno virtual y ejecuta desde la raíz:

```powershell
python -m scripts.demo_rag
```

El script inicia Uvicorn en `127.0.0.1:18100`, crea una SQLite temporal con 60 documentos, genera credenciales de demostración y las imprime en la consola. El proceso fija el destino SQLite, desactiva OpenAI y genera un secreto local por ejecución. En otra terminal:

```powershell
cd frontend
npm ci
$env:VITE_API_URL = 'http://127.0.0.1:18100'
npm run dev -- --host 127.0.0.1 --port 15173 --strictPort
```

Abre `http://127.0.0.1:15173` e inicia sesión con el administrador ficticio. En **Base documental**, verifica el catálogo, carga un PDF académico, revisa el texto, selecciona la categoría y guarda. Reindexa y verifica el documento mediante la búsqueda. Para mostrar RAG, registra desde la cuenta cliente un pedido y un reclamo por artículos faltantes. Abre el reclamo como agente y verifica el borrador, los documentos citados y el historial.

La opción de despliegue de prueba requiere proyectos de frontend y backend independientes, origen CORS y API exclusivos, una base de pruebas nueva, secretos distintos y OpenAI deshabilitado hasta autorizar su uso. La demostración está preparada para loopback. El despliegue remoto queda pendiente de un entorno aislado verificable y autorización explícita.


## Fase 3. Validación integral y preparación para main

Se continuó en el worktree `smartclaim_rag` desde `14f2a18243ad195d89fc34a8a14047feae5330bc`. El `main` remoto permanecía en `86691f7da69554ab5173afd5cb0bd5464d5169e4`. El worktree de cinco roles se inspeccionó en modo de lectura y conservó sus cambios locales.

### Cobertura y métricas

Se revisaron cinco documentos existentes y se elevó su versión a 2.0. El procedimiento de faltantes distingue cantidades parciales de sustituciones. El de tamaño contrasta presentaciones como familiar y mediana. Los tres de retraso diferencian una entrega agendada fuera de hora, un pedido sin conductor y un repartidor que no localiza el destino. Los fallos investigados se relacionaron principalmente con vocabulario y cobertura del texto. Se conservaron los filtros y el ranking híbrido de la fase 2, los 60 documentos, los 76 fragmentos y las anotaciones de ambos conjuntos. Las versiones anteriores están en el historial Git y una nueva importación guarda los metadatos 2.0. El importador rechaza versiones distintas de un ID existente para evitar sobrescribir ediciones.

| Métrica híbrida | Fase 2, originales | Fase 3, originales | Fase 2, adicionales | Fase 3, adicionales |
|---|---:|---:|---:|---:|
| Recall@3 | 66,07 % | 69,64 % | 57,14 % | 71,43 % |
| Precisión@3 | 22,02 % | 23,21 % | 19,05 % | 23,81 % |
| Primer resultado pertinente | 50,00 % | 53,57 % | 42,86 % | 61,90 % |
| Sin evidencia | 4/4 | 4/4 | 6/7 | 6/7 |
| Mediana local | 2,83 ms | 2,63 ms | 2,73 ms | 2,98 ms |
| p95 local | 3,49 ms | 2,94 ms | 3,52 ms | 3,13 ms |

En el conjunto adicional, retrasos pasó de 0/3 a 3/3, producto incompleto de 1/3 a 2/3, producto incorrecto quedó en 2/3 y soporte general bajó de 3/3 a 2/3. En el original, producto incorrecto pasó de 2/8 a 3/8 y retraso de 5/8 a 6/8. Las consultas adicionales ya eran conocidas al revisar cobertura en esta fase, por lo que esta comparación es retrospectiva. Se mantiene el conjunto sin cambios para trazabilidad.

En pruebas dirigidas, «Programé de doce a una y llegó a las dos» devolvió primero el procedimiento de entrega fuera de la franja. «Me entregaron menos productos de los que pagué» devolvió el procedimiento de cantidad parcial, seguido de la FAQ de faltantes. «Pedí una pizza familiar y llegó mediana» devolvió el procedimiento de tamaño de porción. La consulta de las tres empanadas que llegaron en dos unidades siguió sin evidencia.

### Comparación de recuperadores sobre el mismo catálogo final

| Conjunto y configuración | Recall@3 | Precisión@3 | Primer resultado | Sin evidencia | Mediana | p95 |
|---|---:|---:|---:|---:|---:|---:|
| Original, línea base | 66,07 % | 22,02 % | 48,21 % | 3/4 | 2,55 ms | 3,92 ms |
| Original, híbrido | 69,64 % | 23,21 % | 53,57 % | 4/4 | 2,63 ms | 2,94 ms |
| Adicional, línea base | 76,19 % | 25,40 % | 52,38 % | 3/7 | 2,63 ms | 3,78 ms |
| Adicional, híbrido | 71,43 % | 23,81 % | 61,90 % | 6/7 | 2,98 ms | 3,13 ms |

Se mantuvo el híbrido por su mayor pertinencia inicial y mejor abstención en ambos conjuntos, aceptando menor cobertura a tres resultados frente a la línea base en el adicional. El resultado sigue por debajo de 0,80. Reproduce las cuatro mediciones con el evaluador y los modos `baseline` e `hybrid` sobre los dos archivos de consultas.

### pgvector y presupuesto de evaluación

Se reabrió el clúster local PostgreSQL 16.15 con pgvector 0.8.6. El catálogo aislado de la fase anterior contenía 60 documentos y 76 fragmentos. Las verificaciones de la fase 3 usaron bases nuevas del mismo clúster. Se conservaron las pruebas de dimensión 1536, ranking, filtrado, rollback, idempotencia y fallback con vectores sintéticos. Se agregó una prueba de incompatibilidad de dimensión que confirma que el inicio falla sin borrar vectores existentes.

Estimación calculada localmente con tiktoken 0.14.0 y `cl100k_base`. Para indexar se cuenta la concatenación de título, categoría, tipo y fragmento que usa `construir_indice_pgvector`. Para consultar se cuenta el texto exacto de cada consulta.

| Concepto | Entradas | Tokens estimados |
|---|---:|---:|
| Indexación | 76 | 5 757 |
| Consultas originales | 60 | 644 |
| Consultas adicionales | 28 | 392 |
| Total | 164 | 6 793 |

Con la tarifa estándar consultada de USD 0,02 por millón de tokens de `text-embedding-3-small`, una pasada se estima en **USD 0,00013586**. La cifra excluye reintentos y generación de respuestas. El costo y los tokens reales quedan pendientes de autorización. La evaluación sintética sigue siendo una prueba técnica. [OpenAI Docs, text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small)

### Revisión humana, PDF y seguridad

Se detectó que guardar una edición rellenaba `respuesta_final` y exponía el texto en la API de cliente. La edición solo actualiza el borrador. La vista de cliente excluye borradores, análisis, fuentes internas y comentarios internos, y solo expone una respuesta aprobada. El historial público omite ediciones internas y agrupa el par consecutivo de publicación y marcado como respondido. Las acciones se conservan en el historial del agente. La operación de publicar mantiene la revisión humana. El recorrido desde el navegador también reprodujo un formulario de reclamo que no enviaba el pedido preseleccionado: la validación nativa del selector se quedaba desincronizada tras cargar las opciones. Se conservó la validación explícita contra la lista real de pedidos y se verificó el envío desde el detalle de un pedido.

El arranque en `APP_ENV=production` deja de crear las cuentas y pedidos de demostración. Las cuentas demo ya presentes en una base requieren inventario y tratamiento previo al despliegue. La extracción PDF sigue aplicando sus límites y conserva el texto como dato no confiable. Las instrucciones de generación delimitan esa evidencia y la publicación permanece reservada al personal. El comportamiento de un modelo real ante instrucciones maliciosas en PDF queda pendiente de la evaluación autorizada.

Las pruebas ejercen edición del documento importado, dos reindexaciones consecutivas y recuperación del nuevo texto por su ID. Las pruebas de navegador verifican la respuesta CORS de reportes a través del origen local, la firma del PDF descargado y que el CSV contenga filas. Esto verifica el flujo local. La configuración CORS de un entorno remoto se comprobará en su propio origen.

La demostración se inicia con `python -m scripts.demo_rag`. El [plan de integración](PLAN_INTEGRACION_MAIN_RAG.md) detalla el ensayo de Git, las comprobaciones y el rollback.

### Evidencia de validación

- Backend: 42 pruebas aprobadas, con flujos de pedidos, reclamos, conversación, PDF y reportes parametrizados para PostgreSQL. Las pruebas pgvector verifican el fallback y preservación de datos al detectar una dimensión incompatible.
- Navegador contra PostgreSQL: 7 pruebas aprobadas, incluido el flujo de pedido, clasificación, FAQ recuperada, edición privada, escalamiento y publicación visible para el cliente. La primera corrida detectó un predicado de espera de reportes que omitía el query string y un formulario con pedido precargado que no enviaba. Se verificaron ambos en la corrida final.
- TypeScript y compilación Vite: aprobados. Auditoría de Python y auditoría npm de ejecución sin hallazgos conocidos. La auditoría completa de npm conserva siete avisos de desarrollo y TestClient conserva su advertencia de deprecación.
- Demostración: instalación nueva de los requisitos, pip check, arranque, login de tres cuentas ficticias y conteos de 60 documentos y 76 fragmentos. Las capturas de fallo y descargas de Playwright son salidas de prueba y permanecen fuera de Git.
