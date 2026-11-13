# Implementación de Fase 1 — SmartClaim AI

Fecha: 30 de octubre de 2026. Rama: `feature/optimizacion-flujo-ia`. Base: `a303961`.

Se utilizan los IDs y criterios originales de [la auditoría](AUDITORIA_FUNCIONAL_INTEGRAL.md) y [el backlog](BACKLOG_MEJORAS_FUNCIONALES.md). Este informe registra la implementación y su validación; no sustituye las decisiones de negocio pendientes ni acredita despliegue. La implementación se completó inicialmente sin commits, pushes o merges y no creó tickets duplicados. La revalidación para el posterior guardado autorizado se registra a continuación.

## Resultado por ticket

| Ticket | Implementación y evidencia | Límite pendiente |
|---|---|---|
| BF-01 | DTO de cliente sin análisis, evidencia, sugerencias ni ediciones internas; borradores fuera del historial público. Publicación con respuesta final, mensaje, notificación, estado e historial en una transacción. Reintentos sobre la misma respuesta son idempotentes, incluso después del cierre. Pruebas de cuatro aprobaciones concurrentes y rollback de notificación fallida. | Integración concurrente en PostgreSQL real pendiente. Identidad canónica y reconciliación completa de revisores históricos corresponden a BF-06/17. |
| BF-02 | Alta API exige pedido existente del titular autenticado; un código ajeno o inexistente devuelve 404. Identidad/fecha del pedido se obtienen del servidor y el cliente no elige responsable. FK nullable `id_pedido`, conservando código y registros heredados. DTO identifica `LEGACY_UNRESOLVED`. Migración y conciliación probadas en copia de la SQLite del workspace, sin perder filas ni huérfanos. | Conciliación de datos reales requiere revisión y ejecución deliberada sobre copias; no se saneó el original ni producción. No se agrega una excepción pública para crear pedidos inexistentes. |
| BF-03 | Cotización de catálogo en backend, productos y establecimientos activos, cantidades enteras positivas, importes válidos, cargos calculados en servidor y hash de cotización. Confirmación revalida catálogo dentro de la transacción. Pedidos/items guardan identificadores y snapshots de nombres, imágenes, precios, cantidades, cargos, dirección y notas. Navegador no envía precios ni comercio. Se retira referencia de pago que antes se descartaba. | **Parcial por decisión de negocio:** no se eligió monocomercio ni partición. Se cotizan todas las líneas de carritos mixtos, pero cargos/total quedan pendientes y su confirmación responde 409 con explicación. No se vacía ni divide el carrito. Precisión monetaria persistida y migración integral siguen en BF-17; idempotencia del alta, BF-09. |
| BF-04 | Se retiran catálogo ficticio de respaldo, ayuda con políticas/contactos aparentes, promoción fija y promesas de correo de las plantillas. Ayuda y pedidos identifican pagos de demostración, ausencia de GPS, devolución bancaria y comunicaciones automáticas. Se conserva el chatbot FAQ existente como fuente de consulta. Catálogo distingue carga, vacío y fallo, y actualiza las tarjetas al recibir datos. | Los documentos/FAQ ya almacenados no se reescribieron. Su audiencia y revisión editorial corresponden a BF-18. Los prompts generativos reforzados solo se inspeccionaron, no se ejecutaron contra proveedores. |
| BF-05 | Servicio central de transiciones y permisos. Respondido exige mensaje público de soporte; cerrado bloquea mensajes, edición, análisis y nuevas publicaciones; reapertura únicamente desde cerrado. Cierre exige motivo administrativo y fecha/tiempo consistentes; reapertura limpia esos campos. Reanálisis conserva publicación y decisiones Respondido/Escalado. Mensajes adicionales conservan respuesta publicada e historial. Matriz de estados/roles, reapertura repetida y carrera cierre/publicación probadas. | Se conserva la posibilidad previa de reapertura propia por CLIENT y de operación por AGENT/ADMIN, con precondiciones. No se inventan plazos, elegibilidad, aceptación de soluciones, transiciones económicas ni resultado de compensación. Esas decisiones siguen en BF-08/11. |

No cambia la arquitectura FAQ → ML → RAG → sugerencia → revisión humana. Los servicios nuevos encapsulan transacciones y reglas del backend existente, sin LangGraph ni nuevas dependencias.

## Contratos y persistencia

- `POST /api/orders/quote`: recibe exclusivamente identificadores de producto y cantidades; devuelve líneas canónicas, desglose, `quoteHash`, `canConfirm` y limitación explícita cuando proceda.
- `POST /api/orders`: recibe esas líneas, `quote_hash`, método simulado, dirección y notas. Campos de importe/comercio enviados por un cliente se rechazan. Precio, disponibilidad y contenido cambiante invalidan la cotización. No se impone una caducidad temporal arbitraria.
- `POST /api/claims`: vincula pedido propio por ID y conserva su código/fecha. Varios incidentes sobre el mismo pedido siguen permitidos. El helper interno admite `id_pedido=None` para importaciones históricas y fixtures; la API no utiliza esa excepción.
- `PATCH /api/responses/{id}` guarda solo borrador. `POST /api/responses/{id}/approve` publica una sola vez mediante bloqueo del reclamo y transacción; mensajes contienen el ID del usuario autenticado y el historial su nombre. Reintentar no modifica la publicación existente.
- `POST /api/claims/{id}/close` requiere `{ "comment": "motivo administrativo" }`. El endpoint genérico de estado aplica las mismas precondiciones. El frontend solicita el motivo; cerrado no significa reembolso ejecutado.
- En SQLite se serializan escrituras con `BEGIN IMMEDIATE`; en PostgreSQL se prepara bloqueo de reclamo `FOR UPDATE` y de catálogo `FOR SHARE`. Las comprobaciones de concurrencia realizadas corresponden a SQLite, no certifican PostgreSQL.
- Columnas nuevas nullable: `reclamos.id_pedido`, `pedidos.id_restaurante/notas_entrega/subtotal/costo_delivery/costo_servicio`, `pedido_items.id_producto`. Los snapshots anteriores y filas sin referencias permanecen válidos.

La ampliación SQLite se probó en bases temporales, incluida una copia de la base existente. No se inició la API sobre `data/smartclaim.db`. La migración PostgreSQL aditiva está en `database/migrations/phase1_postgres.sql`; **no se ejecutó**. `CREATE TABLE IF NOT EXISTS` no actualiza tablas PostgreSQL existentes: aplicar y validar la ampliación explícita en un entorno aislado es requisito previo a desplegar esta versión.

### Conciliación no destructiva

`scripts/reconcile_claim_orders.py` usa únicamente la biblioteca estándar y no carga `.env`. Por defecto abre SQLite en modo lectura y produce IDs/estados, sin nombres, correos ni descripciones. Clasifica `MATCH_READY`, `LINKED`, `NO_ORDER`, `OWNER_MISMATCH` y `CONFLICT`.

Ejemplos sobre una **copia preparada por el operador**:

```powershell
.venv/Scripts/python.exe scripts/reconcile_claim_orders.py --sqlite C:/ruta/copia.db
.venv/Scripts/python.exe scripts/reconcile_claim_orders.py --sqlite C:/ruta/copia.db --apply --backup C:/ruta/respaldo-nuevo.db
```

`--apply` exige copia diferente del archivo original del workspace y un backup nuevo. Solo enlaza coincidencias exactas de código/titular con referencia vacía. No borra, reasigna propietarios ni inventa pedidos para huérfanos. Los conflictos requieren revisión humana. La conciliación PostgreSQL operativa permanece pendiente de BF-17.

## Validación y aislamiento

Las suites utilizan `tests/conftest.py`: SQLite y artefactos ML/RAG temporales, `dotenv` deshabilitado solo dentro del proceso de prueba, PostgreSQL bloqueado, constructores OpenAI bloqueados, transportes HTTP y conexiones/DNS externos bloqueados. Se conservan los `.env` del workspace. Las 14 sondas de seguridad son intentos deliberados interceptados antes de efectuar I/O; no son llamadas a proveedores.

Para navegador, `tests/serve_offline.py` aplica las mismas guardas y crea su propia base/índices/modelo temporal. Playwright bloquea solicitudes del navegador fuera de localhost:8000/5173, incluidas imágenes externas, y desactiva service workers. No se apuntó la API a Supabase ni se ejecutaron migraciones, reindexados o escrituras productivas.

Al terminar se detuvieron la API aislada y Vite. El `network.json` final de la API confirmó `unexpected: []`. La comprobación final de hashes confirmó los siete archivos protegidos sin alteraciones y `git diff --check` no detectó errores de whitespace. No hubo llamadas efectivas a OpenAI ni consumo de créditos durante las validaciones.

| Bloque ejecutado | pytest | Playwright específico acumulado |
|---|---:|---:|
| BF-01 | 74 aprobadas | 1 aprobada |
| BF-02 | 77 aprobadas | 2 aprobadas |
| BF-03 | 87 aprobadas | 3 aprobadas |
| BF-04 | 88 aprobadas | 5 aprobadas |
| BF-05 y regresión inicial | 92 aprobadas | suite completa: 14 aprobadas / 4 fallidas |
| Ampliación: copia histórica y matriz | 94 aprobadas | pruebas focalizadas repetidas |
| Validación final | 96 aprobadas / 0 fallidas, 55,12 s | 14 aprobadas / 4 fallidas, 39,8 s |

La compilación Vite se ejecutó después de BF-03 y en la validación final. Resultado final: **correcta, 2601 módulos, 5,46 s**. `npm run build` transpila y empaqueta, pero el proyecto no dispone de una fase separada `tsc`/lint; no se presenta como certificación completa de tipos. La comprobación de navegador detectó y permitió corregir un import de icono retirado durante esta fase, que Vite no había rechazado. pytest conserva una advertencia de deprecación Starlette/AnyIO; no produjo fallos. Las guardas registraron **0 intentos externos inesperados y 14 sondas bloqueadas**.

### Revalidación previa al commit y push autorizados

Se repitieron las suites sobre los mismos cambios de BF-01 a BF-05, sin modificar código ni pruebas para esta publicación:

- `pytest -q`: **96 aprobadas, 0 fallidas**, 72,71 s; una advertencia de deprecación Starlette/AnyIO. Guardas: **0 intentos externos inesperados**, 14 sondas deliberadas bloqueadas.
- `npm run build`: **correcta**, 2601 módulos, 8,83 s.
- Playwright con configuración offline: **14 aprobadas y 4 fallidas**, aproximadamente 1,3 minutos. Se mantienen AF-13 (detalle público, BF-16), AF-16 (carrito corrupto, BF-16), AF-25 (campana desactualizada, BF-12) y AF-28 (configuración persistente, BF-14). No se ocultaron fallos ni se alteraron expectativas.
- La API aislada y Vite se detuvieron. La guarda de red de la API confirmó `unexpected: []` y los hashes de los cinco binarios previos y ambos `.env` se comprobaron nuevamente antes del staging.
- El cierre de la API terminó con código 0 y emitió un aviso de asyncio en Windows (`ConnectionResetError`, WinError 10054). No añadió fallos a las suites ni intentos externos a la guarda.
- Selección explícita de 33 archivos de código, pruebas y documentación, incluido este informe. Los cinco binarios permanecen fuera del staging. No se ejecutaron scripts de migración sobre el workspace ni servicios reales; la suite mantiene sus comprobaciones únicamente en bases temporales/copias aisladas.

El commit autorizado utiliza el mensaje `fix: corregir seguridad e integridad de pedidos y reclamos`. Su guardado no implica aprobación de despliegue ni resolución de las cuatro regresiones pendientes.

### Siete regresiones originalmente fallidas

Se incorporaron las siete expectativas a `frontend/e2e/audit-regressions.spec.ts`, además de seis escenarios de Fase 1 y las cinco pruebas de roles existentes: 18 pruebas de navegador. No son una reproducción byte por byte del arnés temporal de 19 casos de la auditoría (12 aprobados/7 fallidos). No hay `skip`, `fixme` ni expectativas invertidas para aparentar aprobación.

| Caso auditado | Clasificación al finalizar | Evidencia / alcance |
|---|---|---|
| AF-03, borrador visible | Corregido | JSON público, historial y navegador no muestran marcador antes de publicar. |
| AF-12, catálogo vacío ficticio | Corregido | 200 vacío y 503 no muestran comercios de respaldo; catálogo con datos sí muestra sus tarjetas. |
| AF-27, búsqueda/contactos aparentes | Corregido por retiro explícito | Se retira buscador sin efecto y contactos quedan deshabilitados; no se declara una búsqueda nueva implementada. |
| AF-13, detalle público de restaurante | Pendiente de BF-16 y decisión de catálogo público | El router exige sesión pese al enlace público. La prueba exige contenido renderizado y URL final; comprobar solo URL intermedia podía producir un falso aprobado antes de redirigir. |
| AF-16, JSON corrupto en carrito | Pendiente de BF-16 | El lector de carrito sin validación todavía puede romper la página. No se ocultó ni se corrigió fuera de alcance. |
| AF-25, notificaciones desactualizadas | Pendiente de BF-12 | El contador no consulta los mensajes nuevos al abrir la campana. No confundir notificación persistida con UI actualizada. |
| AF-28, configuración no persiste | Pendiente de BF-14 | Guardar/recargar no conserva el valor por la actualización heredada. No se ajustaron semillas para ocultarlo. |

Las cuatro fallas finales son las pendientes AF-13/16/25/28 de la tabla. Los seis escenarios específicos BF-01 a BF-05 y los cinco casos de roles aprobaron. No se acredita como inestable ningún defecto pendiente solo por fallar con timeout. Se identificó y corrigió la falta de actualización de tarjetas tras cargar catálogo; además se reforzó la comprobación del encabezado de nivel 1 del restaurante para evitar el falso positivo mencionado (el catálogo ya contenía el mismo nombre en un encabezado de tarjeta). Una ejecución intermedia con esa comprobación incompleta dio 15 aprobadas/3 fallidas; **no se utiliza como resultado final**.

### Componentes reales y simulados

**Ejecutados realmente en local:** login y permisos CLIENT/AGENT/ADMIN, endpoints FastAPI, cotización y creación de pedidos, relación y consulta de reclamos, mensajes/publicación/notificaciones SQL, historia/fechas, rollback/concurrencia SQLite, migración/conciliación de copia, clasificador TF-IDF + Logistic Regression, prioridad/NLP local, FAQ directa, filtrado y recuperación RAG TF-IDF, actualización documental e indexación local, plantillas y trazas. La prueba `test_direct_faq_skips_classifier_rag_and_openai` exige explícitamente que FAQ confiable no ejecute clasificador, RAG ni OpenAI.

**Simulados:** Chat/Embeddings y resultados semánticos cuando las pruebas los requieren, pgvector/repositorios PostgreSQL con respuestas deterministas y pruebas SQL/fallback. Imágenes remotas bloqueadas en navegador. Pago siempre demostrativo; no hay banco, GPS, correo ni devolución real.

**Sin comprobar contra servicios reales:** OpenAI, PostgreSQL/Supabase/pgvector, concurrencia e instalación de la ampliación PostgreSQL, migración completa/restore entre motores, compatibilidad con un despliegue existente y canales financieros/de comunicación. No se afirma que Supabase esté pausado; no se consultó su disponibilidad.

## Archivos de esta fase

Código backend y persistencia:

- `backend/main.py`: contratos, DTO público, propiedad de pedidos y endpoints coherentes.
- `database/repositories.py`, `database/transactions.py`: operaciones compuestas y delegación de transiciones/publicación.
- `database/db_connection.py`, `database/schema.sql`, `database/postgres_schema.sql`, `database/migrations/phase1_postgres.sql`: rollback/cierre de conexión y ampliación aditiva.
- `modules/domain_errors.py`, `modules/response_service.py`, `modules/order_service.py`, `modules/claim_workflow.py`: errores de negocio, publicación, cotización y estados centralizados.
- `scripts/reconcile_claim_orders.py`: reporte y conciliación conservadora sobre copia.
- `modules/rag_engine.py`, `modules/chatbot_service.py`: textos/prompt sin promesas de operaciones inexistentes; conserva enrutamiento IA.

Frontend:

- `frontend/src/app/lib/api.ts`, `frontend/src/app/lib/useOrderQuote.ts`: nuevo contrato, cotización ligada al contenido vigente del carrito e ignorado de resultados obsoletos.
- `frontend/src/app/pages/catalog/CatalogPage.tsx`, `CartPage.tsx`, `RestaurantPage.tsx`: catálogo sin fallback y totales canónicos; no se aplica una nueva política multicomercio.
- `frontend/src/app/pages/client/CheckoutPage.tsx`, `OrderDetailPage.tsx`, `HelpCenterPage.tsx`: pedido cotizado, notas conservadas y alcance de simulación explícito.
- `frontend/src/app/pages/admin/AdminClaimDetailPage.tsx`: cierre motivado y bloqueo de acciones incompatibles con cierre/publicación.

Pruebas y documentación:

- `tests/test_phase1_acceptance.py`: aceptación por BF-01 a BF-05.
- `tests/test_ai_routing.py`, `tests/test_api_auth_orders.py`: fixtures sobre pedidos propios y contratos seguros; sugerencia/análisis inspeccionados con rol staff, sin debilitar privacidad.
- `tests/serve_offline.py`, `frontend/playwright.offline.config.ts`, `frontend/e2e/offline-fixture.ts`: servidor y navegador aislados.
- `frontend/e2e/phase1.spec.ts`, `frontend/e2e/audit-regressions.spec.ts`, `frontend/e2e/roles.spec.ts`: escenarios y siete regresiones documentadas; roles conservan sus expectativas.
- `docs/IMPLEMENTACION_FASE_1.md`: este informe. El backlog y auditoría originales permanecen como referencia histórica, sin reescribir sus criterios.

Los cinco binarios que ya aparecían modificados al comenzar no pertenecen a los cambios de esta fase: `data/smartclaim.db`, `models/claim_classifier.joblib`, `vector_store/rag_metadata.joblib`, `vector_store/rag_tfidf_matrix.joblib`, `vector_store/rag_tfidf_vectorizer.joblib`. **Sus hashes SHA-256 y los de ambos `.env` coinciden con el inventario tomado antes de implementar**. No se agregan dependencias ni artefactos de compilación al seguimiento. Hay 33 archivos de texto nuevos/modificados de esta fase, además de los cinco binarios preexistentes. Al cerrar la implementación, antes del guardado autorizado posterior, HEAD estaba en `a303961`, sin archivos staged.

## Reproducción segura

Desde el directorio raíz, usando el entorno disponible:

```powershell
.venv/Scripts/python.exe -m pytest -q
```

Para navegador, usar terminales separadas. No iniciar `backend.main` directamente con configuración del workspace para esta validación:

```powershell
# Terminal 1, raíz: ruta temporal nueva; el script la crea.
$phaseControl = Join-Path ([IO.Path]::GetTempPath()) ('smartclaim-offline-' + [guid]::NewGuid())
.venv/Scripts/python.exe tests/serve_offline.py --control-dir $phaseControl
# Para detener desde otra terminal: crear el archivo stop dentro de esa ruta.

# Terminal 2, frontend:
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort

# Terminal 3, frontend, con la API aislada ya lista:
npx playwright test --config playwright.offline.config.ts
npm run build
```

Playwright devuelve salida no cero mientras las cuatro regresiones pendientes sigan presentes. Puertos 8000 y 5173 deben estar libres o corresponder a estos procesos aislados. Revisar `network.json` en la ruta de control después de detener el servidor.

## Riesgos antes de continuar o desplegar

1. Acordar la política de carrito multicomercio y cargos; no presentar su confirmación como resuelta. Definir también elegibilidad temporal y resolución/reapertura sin equiparar cierre con pago.
2. Resolver BF-12/14/16 y completar operación real de pedidos BF-07; los recorridos comerciales completos siguen incompletos.
3. Validar ampliación, locks, restricciones, restauración y conciliación en PostgreSQL/pgvector aislado antes de tocar Supabase. El cambio de contrato exige frontend/backend coordinados.
4. El arranque heredado sigue aplicando semillas y ajustes demo. Además, el ajuste heredado de dimensión puede eliminar embeddings si encuentra dimensión incompatible. **No se ejecutó esa ruta en producción ni se corrigió dentro de esta fase**; BF-17 debe separar preparación explícita de inicio normal antes de un despliegue.
5. Decimal calcula importes con dos decimales en servidor, pero almacenamiento REAL y esquema histórico no ofrecen todavía la precisión monetaria final acordada. Los registros previos no se recalcularon.
6. Sigue existiendo reemplazo del análisis IA anterior al reanalizar, referencias de revisor históricas y evidencia documental mutable. Las respuestas publicadas sí permanecen, pero versionado/auditoría integral requieren BF-06/17/18.
7. El documento/FAQ almacenado puede conservar políticas internas de muestra. No reindexar producción automáticamente ni afirmar que las instrucciones del prompt garantizan la conducta de un modelo no ejecutado.

El resultado es apto para continuar desarrollo y revisión local. **No constituye aprobación de despliegue productivo.**
