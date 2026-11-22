# Auditoría de integración de SmartClaim AI

Fecha de revisión local: 9 de noviembre de 2026, America/Lima.

## Origen e integración

| Referencia remota verificada | Commit |
|---|---|
| main | 86691f7da69554ab5173afd5cb0bd5464d5169e4 |
| feature/ampliacion-base-documental-rag | a117e4cfff8d50cc091ac5515057faf327c50ce6 |
| codex/respaldo-cinco-roles-2026-11-06 | 92f64b63e4aa079dc13962938bca55c88ac3b9bd |
| feature/optimizacion-flujo-ia | eb8dd2d91b4d5db220554ad065e00bacc07521bd |

Se ejecutó git fetch origin. Los 35 cambios locales de la rama de cinco roles permanecieron en su worktree, con 30 archivos de código ya respaldados en GitHub. La integración partió del main remoto en smartclaim_integrado, avanzó al respaldo y resolvió nueve conflictos al incorporar RAG. El PR #1 seguía abierto y en borrador.

Los conflictos afectaban backend, repositorio y conexión, motor RAG, embeddings JSON, dos pantallas y configuración de pruebas. Se mantuvieron la autorización por rol y titularidad, las transacciones de pedidos y reclamos, la asignación versionada y la aprobación humana. Se incorporaron el ranking híbrido, la verificación de fuentes activas y vigentes, el filtro de modelo en pgvector y la sincronización local de fragmentos. El arranque sigue requiriendo bootstrap explícito en SQLite de desarrollo. Los entornos alojados no ejecutan seeds ni sincronización automática.

## Cobertura por actor

| Actor | Implementado y cubierto en pruebas de backend | Límite o pendiente |
|---|---|---|
| CLIENT | Registro/login, catálogo, cotización, carrito en UI, pedido propio, reclamo vinculado, historial, conversación, avisos y protección entre clientes. | Datos reales, conciliación de reclamos antiguos y validación en entorno alojado. |
| MERCHANT | Asignación por comercio, listado autorizado, preparación, transiciones, historial y rechazo de pedidos ajenos. | Habilitación real de operadores y validación sobre esquema productivo. |
| COURIER | Asignación, retiro y entrega, permisos sobre pedido asignado y conflictos concurrentes. | Validación de cuentas y alcance operativo en staging. |
| AGENT | Bandeja, clasificación, RAG, edición privada, aprobación, toma de caso, escalamiento y trazabilidad. | Calidad semántica real y revisión de casos ambiguos. |
| ADMIN | Gestión operativa de roles y permisos, asignación, reportes, PDF y configuración. | Escritura y reindexación documental alojadas bloqueadas hasta mantenimiento aprobado. |

Las suites cubren operaciones reales contra persistencia temporal, roles no autorizados y reintentos. Los ensayos de navegador y su resultado se registran abajo por separado.

## Fechas, recuperación y ML

La presentación usa America/Lima desde los formateadores compartidos. Los timestamps SQL sin offset se interpretan como UTC, los valores con offset conservan su instante y una fecha de calendario conserva su día. El pedido nuevo escribe la estimación de entrega con offset UTC. Los valores históricos permanecen intactos. La regresión comprueba el caso 7 de noviembre 00:25 UTC → 6 de noviembre 19:25 Lima. Las fechas históricas sin offset generadas por un servidor con zona local distinta de UTC requieren reconciliación antes de tratarlas como instantes inequívocos.

La evaluación reconstruyó 18 documentos del seed y 42 académicos importados idempotentemente. Verificó 60 documentos, 76 fragmentos y sus metadatos. Las pruebas comprueban la FAQ de faltantes, el rechazo de fragmentos cruzados, PDF con vista previa, límites, duplicados y autorización. La recuperación semántica local con pgvector usa vectores sintéticos. Si una categoría reconocida no tiene resultados, el reintento global se limita a TF-IDF y queda trazado. Se corrigió un caso en que el reintento semántico devolvía un vector de fraude para una consulta sin evidencia en la categoría de faltantes.

| TF-IDF híbrido con filtro de categoría de evaluación | Original 60 | Adicional 28 |
|---|---:|---:|
| Recall@3 | 69,64 % | 71,43 % |
| Precisión@3 | 23,21 % | 23,81 % |
| Primer resultado pertinente | 53,57 % | 61,90 % |
| Sin evidencia detectada | 4/4 | 6/7 |

El clasificador se mantuvo sin reentrenar. El reporte histórico registra 105 filas de entrenamiento, siete categorías y accuracy de validación 0,7407 en 27 ejemplos. Esa cifra corresponde al clasificador, y la tabla corresponde al recuperador. El backend conserva plantillas locales, proveedor LLM opcional y aprobación humana. Esta ejecución no midió calidad de generación LLM ni semántica con embeddings reales.

## Base de datos y seguridad

Se consultó Supabase mediante SELECT de metadatos y conteos. PostgreSQL 17.6, pgvector 0.8.0, vector(1536), 18 documentos, 24 fragmentos, 24 embeddings y 16 reclamos. Faltan documentos_importados, schema_migrations, courier_profiles, comercio_operadores, pedido_asignaciones, pedido_eventos, operaciones_auditoria, claim_commands y las columnas de asignación verificadas. La secuencia de documentos mostraba 6 frente a un ID máximo de 18. Los conteos detectaron cero relaciones cruzadas de embeddings y cero textos desactualizados en la comprobación realizada. Las relaciones documento → fragmento y fragmento → embedding usan borrado en cascada. La sincronización debe inventariar y aprobar qué vectores se perderían antes de aplicar.

**Bloqueo de publicación.** RLS estaba desactivado en auth_users, pedidos, reclamos y las tres tablas documentales consultadas. Se observaron permisos SELECT, INSERT, UPDATE y DELETE para anon y authenticated. La comprobación HTTP posterior y los controles preparados se registran en la sección de cierre de seguridad. El control del backend no protege el acceso directo por esa API. No se leyeron filas personales ni se probaron escrituras.

La aplicación integrada requiere migraciones aditivas para la operativa y datos semilla controlados en un entorno nuevo. La compatibilidad de PostgreSQL local se limita a la versión ensayada y no sustituye una restauración autorizada de la base destino.


## Validación y límites

- Pytest final: 176 aprobadas con SQLite temporal y PostgreSQL 16.15 local con pgvector 0.8.6. La protección de red registró cero intentos inesperados y bloqueó 14 sondas del propio test. El modo SQLite de prueba no mide durabilidad ante pérdida física. Quedó un aviso de deprecación de Starlette/httpx.
- Chromium final: 64 aprobadas. Incluye compra y seguimiento por cinco roles, carga y vista previa PDF en móvil, exportaciones CSV/PDF, escalamiento con motivo, ocultamiento de borradores y hora de Lima. El servidor de prueba registró cero intentos externos inesperados. La primera ejecución tuvo tres fallos de interacción y expectativas que se ajustaron a los controles integrados.
- El preflight de Reportes aceptó el origen de desarrollo y rechazó un origen ajeno. La API rechazó una sesión CLIENT con HTTP 403 y devolvió cero resultados para un filtro de fecha futura, estado y prioridad. Las métricas históricas de IA siguen siendo globales por diseño. Las fechas de agrupación del reporte siguen el día almacenado.
- TypeScript se comprobó con tsc y Vite generó el build. Las auditorías de dependencias de ejecución con npm audit y pip-audit no reportaron vulnerabilidades conocidas al momento del ensayo.
- La primera suite de Python encontró nueve fallos. Se ajustaron los datos de prueba para respetar pedidos vinculados y esquemas heredados, y se corrigió el fallback semántico fuera de categoría. Las pruebas con vectores sintéticos verificaron reemplazo de fragmentos, dimensionalidad, idempotencia y rollback.
- Quedan por ensayar en staging la migración sobre una restauración autorizada, los orígenes reales de los servicios y la generación LLM con presupuesto aprobado. También queda verificar la exposición efectiva de Data API. No se reentrenó ni se generaron embeddings de pago.

Código integrado en el commit 8287d1db2038f54d77c0a2d5651db67d3003bffc. La rama queda en el worktree local para revisar los bloqueos antes de publicar.


## Cierre de seguridad y compatibilidad de PostgreSQL

### Alcance comprobado en Supabase

- Las 25 tablas de aplicación en public tenían RLS desactivado y cero políticas. PostgreSQL confirmó SELECT, INSERT, UPDATE y DELETE efectivos para anon y authenticated, incluidas auth_users, clientes, pedidos, reclamos, respuestas privadas, notificaciones, logs y RAG. La proyección de auth_users incluye password_hash.
- REST devolvió HTTP 200 en las 25 tablas para HEAD con select=* y limit=0, usando la clave pública y sin sesión de usuario. Esto confirma acceso REST anónimo. Los permisos de escritura y los permisos de authenticated se confirmaron en el catálogo. No se descargaron filas ni se enviaron mutaciones productivas.
- Las tablas expuestas fueron analisis_ia, auth_users, categorias_reclamo, claim_messages, clientes, comentarios_agente, configuracion_modelo_ia, dataset_entrenamiento, documentos_base, documentos_consultados, estados_reclamo, evaluacion_respuesta, fragmentos_documento, historial_estados, logs_sistema, notificaciones, pedido_items, pedidos, prioridades, productos, rag_embeddings, reclamos, respuestas_sugeridas, restaurantes y usuarios.
- El catálogo no mostró vistas de aplicación, funciones SECURITY DEFINER de public ejecutables por anon o authenticated ni tablas de public en la publicación supabase_realtime. Una consulta de introspección de solo lectura a GraphQL indicó que pg_graphql está deshabilitado. REST rechazó un perfil inexistente con 406 y no enumeró otros esquemas. Queda verificar la lista completa de esquemas en la configuración administrada.
- FastAPI valida sus propias sesiones y carga el usuario activo desde auth_users. Psycopg usa DATABASE_URL para conectarse a PostgreSQL. La aplicación no propaga sus sesiones como JWT de Supabase. postgres es propietario de las tablas de aplicación y tiene BYPASSRLS, al igual que service_role. No existe smartclaim_backend en el catálogo productivo observado. La identidad exacta de la conexión de Render queda por verificar con current_user y session_user desde ese proceso. pg_stat_activity mostró conexiones de postgres, authenticator, pgbouncer y supabase_admin, sin atribuirlas a Render. authenticator puede asumir anon, authenticated y service_role mediante SET ROLE. No hereda sus permisos.

### Controles preparados

La migración retira acceso directo al esquema public para anon y authenticated y revoca privilegios de tablas, columnas y secuencias de aplicación para esos roles, PUBLIC y service_role. Habilita y fuerza RLS en las tablas del manifiesto. Concede a smartclaim_backend solo las operaciones SQL por tabla que necesita FastAPI. El rol puede leer documentos, fragmentos y vectores, y carece de privilegios para reindexarlos o eliminarlos. En producción FastAPI exige PostgreSQL con el login limitado y comprueba la identidad de la sesión, atributos, membresías, propiedad de relaciones en public y capacidad de crear objetos allí.

Las políticas SQL se limitan al login de servicio. FastAPI aplica el alcance de los cinco roles. Una conexión comprometida de smartclaim_backend podría leer las filas que el servicio necesita y ejecutar sus operaciones permitidas. Cualquier futuro acceso directo de usuarios necesita políticas por propietario y otro contrato de acceso. [Seguridad de la Data API](https://supabase.com/docs/guides/api/securing-your-api) · [RLS en Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security)

### Diferencias de esquema y preservación

Producción mantiene los CHECK anteriores de roles y estados. Faltan los siete campos aditivos de Fase 1 y la infraestructura de 2B y 2C. Se observaron 50 índices, todos válidos, y cero FKs sin validar. La FK de reclamos a pedidos aún no existe. Las FKs de RAG vigentes incluyen cascadas. La secuencia documental tiene cache 1, valor 6 e is_called=true para un máximo de 18. pgvector está instalado en public. La nueva FK compuesta protege el vínculo de pedido y titular. Los reclamos históricos sin vínculo confirmado conservan NULL. La importación de altas conserva IDs, texto y vectores existentes.

### Límites para autorizar producción

No hubo respaldo autorizado ni acceso a la credencial activa de Render. Los datos y tokens del ensayo son sintéticos. Hace falta una restauración autorizada, validar el propietario de migración en Supabase 17.6 y repetir las comprobaciones HTTP en la configuración administrada. Los permisos expuestos justifican revisar logs e impacto, incluidas sesiones y contraseñas. La comprobación de alcance no establece si terceros accedieron o modificaron datos. El despliegue y la publicación de esta rama siguen pendientes de esas verificaciones.


### Resultados del ensayo aislado

| Control | Resultado |
|---|---|
| Origen del laboratorio | Esquema PostgreSQL legado de main, roles y grants sintéticos. Red Docker interna y ninguna conexión PostgreSQL publicada. |
| Diferencias de datos | Laboratorio Docker con 18 documentos, 18 fragmentos, 18 vectores sintéticos y cero reclamos. Producción tenía 18, 24, 24 y 16, respectivamente. Las pruebas de integridad crearon pedidos y reclamos sintéticos por separado. |
| Versiones | PostgreSQL 16.15, pgvector 0.8.7 y PostgREST 13.0.8 en Docker. Pytest usó PostgreSQL 16.15 y pgvector 0.8.6 en loopback. Producción se observó con PostgreSQL 17.6 y pgvector 0.8.0. |
| Aplicación repetida | Se ejecutaron dos veces las seis migraciones. Se conservaron las huellas de documentos, fragmentos y vectores. La secuencia pasó de 6/llamada a 19/sin llamada. Se aplicó RLS forzado a 33 tablas. |
| REST aislado | Antes, HEAD devolvió 200 para anon y el JWT autenticado en auth_users. Después, HEAD devolvió 401 para anon y 403 para authenticated en cada una de las 33 tablas. PATCH sobre auth_users recibió las mismas denegaciones. |
| Restauración | pg_dump y pg_restore sobre otra base del laboratorio reprodujeron huellas, conteo y secuencia 6/llamada. El respaldo anterior restauró también el grant y RLS desactivado de auth_users. La base de destino compartía los roles del clúster del laboratorio. |
| Catálogo | Las pruebas aplicaron 42 altas y sus fragmentos, verificaron el rechazo del lote mixto y la omisión idempotente. Compararon las filas previas completas y confirmaron que los vectores conservaron su conteo e identidad. |
| Pytest | 191 aprobadas. Se repitió el flujo con cinco roles desde el login limitado y se comprobó la denegación horizontal y administrativa, la integridad y el rollback de secuencia ante un fallo inducido. La primera corrida completa tuvo un fallo en la ruta utilizada por la prueba de escalamiento, corregido en el ensayo final. Cero intentos de red inesperados. |
| Navegador y compilación | Chromium aprobó 64 pruebas con backend local y SQLite sintética. tsc y Vite completaron la verificación. |
