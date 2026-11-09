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

**Bloqueo de publicación.** RLS estaba desactivado en auth_users, pedidos, reclamos y las tres tablas documentales consultadas. Se observaron permisos SELECT, INSERT, UPDATE y DELETE para anon y authenticated. Falta comprobar la exposición efectiva de Data API y aplicar mínimo privilegio en un cambio autorizado y ensayado. El control del backend no protege el acceso directo por esa API. No se leyeron filas personales ni se probaron escrituras.

La aplicación integrada requiere migraciones aditivas para la operativa y datos semilla controlados en un entorno nuevo. La compatibilidad de PostgreSQL local se limita a la versión ensayada y no sustituye una restauración autorizada de la base destino.


## Validación y límites

- Pytest final: 176 aprobadas con SQLite temporal y PostgreSQL 16.15 local con pgvector 0.8.6. La protección de red registró cero intentos inesperados y bloqueó 14 sondas del propio test. El modo SQLite de prueba no mide durabilidad ante pérdida física. Quedó un aviso de deprecación de Starlette/httpx.
- Chromium final: 64 aprobadas. Incluye compra y seguimiento por cinco roles, carga y vista previa PDF en móvil, exportaciones CSV/PDF, escalamiento con motivo, ocultamiento de borradores y hora de Lima. El servidor de prueba registró cero intentos externos inesperados. La primera ejecución tuvo tres fallos de interacción y expectativas que se ajustaron a los controles integrados.
- El preflight de Reportes aceptó el origen de desarrollo y rechazó un origen ajeno. La API rechazó una sesión CLIENT con HTTP 403 y devolvió cero resultados para un filtro de fecha futura, estado y prioridad. Las métricas históricas de IA siguen siendo globales por diseño. Las fechas de agrupación del reporte siguen el día almacenado.
- TypeScript se comprobó con tsc y Vite generó el build. Las auditorías de dependencias de ejecución con npm audit y pip-audit no reportaron vulnerabilidades conocidas al momento del ensayo.
- La primera suite de Python encontró nueve fallos. Se ajustaron los datos de prueba para respetar pedidos vinculados y esquemas heredados, y se corrigió el fallback semántico fuera de categoría. Las pruebas con vectores sintéticos verificaron reemplazo de fragmentos, dimensionalidad, idempotencia y rollback.
- Quedan por ensayar en staging la migración sobre una restauración autorizada, los orígenes reales de los servicios y la generación LLM con presupuesto aprobado. También queda verificar la exposición efectiva de Data API. No se reentrenó ni se generaron embeddings de pago.

Código integrado en el commit 8287d1db2038f54d77c0a2d5651db67d3003bffc. La rama queda en el worktree local para revisar los bloqueos antes de publicar.
