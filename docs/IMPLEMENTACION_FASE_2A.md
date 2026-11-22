# Implementación de Fase 2A — Configuración administrativa y UX

Base: `4f18a0ad14a00fa1959518b8b84f3aca90f42cee`, rama `feature/optimizacion-flujo-ia`.

Revisión de cierre: 30 de octubre de 2026. Se retomaron los cambios existentes, sin repetir la implementación. La revisión contra BF-14/BF-16 no encontró parches parcialmente aplicados; el cierre documental conservaba marcadores pendientes de resultados y conservación. En esta reanudación se completa el informe y se repiten las validaciones, sin modificar código ni expectativas de pruebas.

Referencia: [auditoría funcional](AUDITORIA_FUNCIONAL_INTEGRAL.md), [criterios BF-14/BF-16 del backlog](BACKLOG_MEJORAS_FUNCIONALES.md) y [Fase 1](IMPLEMENTACION_FASE_1.md). No se crean tickets duplicados. Este documento registra implementación local y pruebas, sin autorizar despliegue.

## Reproducción de los defectos originales

Antes de cambiar código se ejecutaron las tres regresiones mantenidas AF-13, AF-16 y AF-28 con la API aislada: **0 aprobadas y 3 fallidas**.

- **AF-28:** el guardado actualizaba por `Configuración principal`, diferente de la semilla `Configuracion principal`; la respuesta HTTP y la UI no acreditaban persistencia. Había selección por mayor ID activo y posibilidad de múltiples filas activas heredadas.
- **AF-13:** el enlace público «Ver restaurante» llevaba a una ruta protegida; faltaba coherencia con el catálogo y la documentación públicos.
- **AF-16:** `JSON.parse` sin protección en carrito/detalle y lectores inconsistentes en catálogo/checkout permitían que datos locales inválidos dejaran la pantalla vacía o se descartaran silenciosamente.

Se corrigieron las causas sin debilitar las expectativas originales. En `audit-regressions.spec.ts` solo se actualizaron los títulos de esos tres casos de pendiente a corregido.

## BF-14 — Configuración administrativa

1. `GET /api/config` identifica la fila efectiva mediante `id`, `activeCount` y `selectionPolicy`. Se conserva la regla previa **mayor ID activo** en el backend y se informa en pantalla. Si hay varias activas se muestra una advertencia; no se borran ni desactivan filas del usuario.
2. `PUT /api/config` requiere `config_id`, valida límites, actualiza por ID activo en una transacción y comprueba que corresponde a la selección vigente. Un ID inexistente, inactivo u obsoleto devuelve 409 con indicación de recarga.
3. Se verifica que UPDATE afecte exactamente una fila y se consulta nuevamente la fila. Valores distintos de los solicitados abortan la transacción. Los casos de cero filas y de trigger que altera el resultado se ensayaron sobre SQLite temporal, comprobando rollback.
4. Después del PUT, el frontend efectúa **un GET independiente**, compara ID y cada parámetro y muestra éxito únicamente si coinciden. Un PUT 200 simulado que no persiste datos no produce mensaje de éxito. Carga fallida deja la edición bloqueada y ofrece recarga.
5. El umbral cero deja de confundirse con el valor por defecto. Los controles representan el rango permitido por la API, sin redondear silenciosamente el umbral cargado; máximo documental 1–10. Los permisos continúan siendo exclusivamente ADMIN para lectura y modificación de configuración.

### Modelo configurado frente a ejecución observada

El campo `model` conserva el metadato histórico de configuración, mostrado como **modelo configurado** y sin un selector ficticio. No se sustituye automáticamente por el nombre de un modelo deseado.

`runtime.classifierArtifactPresent` informa solamente presencia de archivo, sin cargar, entrenar ni ejecutar el modelo. No se presenta esa presencia como prueba de funcionamiento.

Las nuevas trazas del análisis formal incluyen `classification_model`, obtenido del resultado real del clasificador existente. `runtime.lastExecution` muestra clasificación, estrategia de generación/recuperación, uso de OpenAI, fecha y resultado de una traza registrada. Se consultan como máximo las 100 últimas trazas; se omiten entradas antiguas sin ese dato, JSON inválido y nombres de modelo no reconocidos. Sin evidencia se declara que no consta una ejecución reciente verificable. No se infiere el modelo ejecutado de semillas históricas ni de una clave de proveedor disponible.

No se modifica el clasificador ni el algoritmo FAQ/RAG, no se ejecutan modelos para construir esta vista y no se afirma haber validado un modelo generativo externo.

## BF-16 — Navegación, carrito, errores y adaptación móvil

### Navegación coherente

El detalle de restaurante y el carrito son públicos; el catálogo ya tenía una API pública. Se hace coherente el recorrido anunciado: explorar → añadir → revisar carrito → iniciar sesión al confirmar. Checkout, pedidos, reclamos y pantallas administrativas mantienen protección, al igual que las comprobaciones de titularidad en API.

El login conserva `/checkout` como destino y mantiene el carrito. El detalle muestra confirmación de artículo agregado, enlace al carrito y regreso al catálogo adecuado a la sesión. Las pruebas recorren compra de demostración, pedidos, reporte de un pedido propio y consulta de reclamos. No se añaden operaciones de preparación, entrega, cancelación o pago.

### Recuperación del carrito

`lib/cart.ts` centraliza el esquema y la lectura; `useCart` centraliza escritura/errores y `CartNotice` la explicación y acción de recuperación. Catálogo, restaurante, carrito y checkout usan el mismo mecanismo.

- Se validan JSON, array, IDs de producto, nombres, comercio, cantidades enteras positivas, rango técnico, importes finitos y tipos de imágenes. Duplicados o artículos incompletos no se utilizan para confirmar compras.
- Ante datos inválidos, no se sobrescribe el valor original de localStorage: se bloquean las acciones y se informa. Solo «Restablecer carrito» realiza la recuperación explícita.
- Errores de acceso o cuota de almacenamiento se capturan y explican; no se anuncia un artículo agregado si la escritura falló.
- Los precios locales siguen sin autorizar la compra: la cotización del backend de Fase 1 es la autoridad. Artículo retirado produce error visible, confirmación deshabilitada y conserva el carrito para revisión. La restricción provisional de confirmación multicomercio permanece intacta.
- El destacado sin productos permanece deshabilitado, sin artículos fantasma.

### Carga, error y vacío

Se distinguen carga, error y vacío en los recorridos cliente y administrativos modificados. Un 503 no se convierte en «no tienes pedidos», «no hay reclamos», cero métricas o conversación sin mensajes. Los detalles dejan de titular un fallo de conexión como recurso inexistente.

En formulario de reclamo, conversación y configuración hay reintentos explícitos; se bloquean acciones dependientes de datos no cargados. Bandeja, reportes y listados descartan respuestas antiguas de solicitudes anteriores cuando cambian sus parámetros. Los ajustes de reportes afectan presentación de carga/error, **no corrigen la definición de métricas o filtros de BF-15**.

### Escritorio y móvil

Se mantienen componentes, colores y diseño. Los cambios se limitan a distribución responsive, límites de ancho, saltos de texto, etiquetas accesibles de botones y estados de interacción. Se comprueban **320, 360, 768 y 1280 px** en catálogo, pedidos, reclamos, formulario, restaurante, carrito, documentos y configuración.

Durante las pruebas se corrigieron un badge del catálogo que forzaba ancho mínimo a 320 px y un título documental largo dentro de flex. Se ensayan nombres/códigos sin cortes naturales, importes largos y edición documental en 320 px; no se oculta el desbordamiento global con `overflow-x:hidden`.

## Validación

| Ejecución | Resultado |
|---|---|
| Reproducción inicial AF-13/16/28 | 3 fallidas, confirmando defectos |
| Repetición tras las correcciones | 3 aprobadas, 0 fallidas |
| Primera ampliación pytest | 115 aprobadas, 0 fallidas |
| pytest final de cierre | 116 aprobadas, 0 fallidas; 313,27 s |
| Primera repetición completa de cierre de Playwright | 45 aprobadas, 2 fallidas: AF-25 y timeout de preparación/login de AF-03; 2,9 min |
| Playwright completo tras finalizar pytest | 46 aprobadas, 1 fallida (AF-25 / BF-12); 1,7 min |
| Build frontend final de cierre | Correcto: 2604 módulos, 33,93 s |

Las suites conservan las guardas de Fase 1: PostgreSQL y constructores OpenAI bloqueados, transporte/red exterior bloqueados, dotenv deshabilitado únicamente en proceso de pruebas, SQLite/modelo/índices temporales. El navegador permite solo localhost:8000/5173 y bloquea imágenes remotas y service workers.

La repetición final de pytest confirmó **0 intentos externos inesperados y 14 sondas deliberadas bloqueadas**; conserva una advertencia de deprecación Starlette/AnyIO. No hubo fallos pytest. La primera ejecución de navegador de la reanudación coincidió con pytest y build; AF-03 agotó 30 s al rellenar la contraseña, antes de la comprobación de privacidad. Sus seis escenarios específicos de Fase 1 y los 29 de Fase 2A sí aprobaron. Se conserva ese resultado y se repite la suite sin pytest/build simultáneos, manteniendo `retries: 0`, el límite de tiempo y las expectativas originales.

La repetición completa posterior terminó con **46 aprobadas / 1 fallida**. AF-03 aprobó en 1,9 s, sin modificar código ni pruebas: el fallo adicional se clasifica como **timeout intermitente de preparación/login**, no como una exposición de borrador reproducida. La causa exacta de su demora no queda demostrada. AF-13, AF-16 y AF-28 aprobaron de nuevo; las seis pruebas de navegador de Fase 1, los 29 casos nuevos y las cinco pruebas de roles también aprobaron. **AF-25 es el único defecto funcional fallido al cierre**, documentado como pendiente de BF-12. No se modificaron BF-12 ni BF-07.

Comparación con los cuatro fallos funcionales pendientes al cerrar Fase 1:

| Caso | Cierre de Fase 1 | Fase 2A |
|---|---|---|
| AF-13: detalle público | Fallido | Corregido y comprobado sin sesión |
| AF-16: carrito corrupto | Fallido | Corregido; conserva valor inválido y ofrece recuperación explícita |
| AF-28: configuración | Fallido | Corregido; guardado por ID y nueva consulta de confirmación |
| AF-25: campana | Fallido | Permanece pendiente de BF-12; sin cambio de expectativas |

Se ejercitan realmente FastAPI, autenticación y permisos, transacciones SQLite, copia de configuración histórica, frontend React, clasificación local, FAQ, RAG TF-IDF, plantillas y trazas. Las pruebas existentes de FAQ siguen exigiendo que una coincidencia confiable no ejecute ML, RAG ni OpenAI. La Fase 1 conserva sus pruebas de propiedad, precios canónicos, borradores privados, publicación idempotente, rollback y máquina de estados.

Los 29 casos nuevos de Playwright incluyen **una prueba unitaria del parser** sin navegador y 28 escenarios de interfaz. La suite completa contiene los 18 casos anteriores más esos 29. Se agregan pruebas pytest de límites, permisos, selección por ID, múltiples activas, cambio de nombre, cero filas, readback incorrecto, metadato frente a ejecución y preservación de filas sobre una copia de SQLite original.

PostgreSQL solo tiene una prueba de contrato de bloqueo con stub SQLite, además de los mocks previos de pgvector; **no es integración PostgreSQL real**. Docker está instalado pero su motor local no está disponible; no se inició, instaló ni conectó un servidor PostgreSQL/Supabase para esta fase. No se presume pausa de Supabase.

La compilación Vite no incluye un proceso independiente `tsc`/lint en este repositorio. Las capturas generadas por Playwright se mantienen dentro de `frontend/test-results/offline`, ignorado por Git; no se agregan artefactos binarios al seguimiento.

## Archivos modificados o nuevos

Backend:

- `backend/main.py`: contrato estable de configuración, DTO y evidencia de clasificador en trazas.
- `database/repositories.py`: delegación de guardado por ID.
- `modules/config_service.py`: actualización transaccional y verificación.
- `modules/ai_status.py`: estado basado en evidencia, sin invocar modelos.

Frontend común:

- `frontend/src/app/App.tsx`: detalle de restaurante y carrito públicos; confirmación protegida.
- `frontend/src/app/lib/api.ts`: ID, estado de ejecución y contrato de configuración.
- `frontend/src/app/lib/cart.ts`, `frontend/src/app/lib/useCart.ts`, `frontend/src/app/components/CartNotice.tsx`: carrito validado y recuperación explícita.
- `frontend/src/app/components/ClaimConversation.tsx`: carga, error y reintento del historial.
- `frontend/src/app/components/ClientLayout.tsx`, `frontend/src/app/components/AdminLayout.tsx`: ajuste de cabecera móvil; no cambia notificaciones ni permisos.

Pantallas:

- `frontend/src/app/pages/admin/AIConfigPage.tsx`: confirmación posterior al guardado y ejecución registrada.
- `frontend/src/app/pages/admin/KnowledgeBasePage.tsx`: carga/error y adaptación de documentos largos.
- `frontend/src/app/pages/admin/AdminDashboardPage.tsx`, `ReportsPage.tsx`, `ClaimsBandejaPage.tsx`: error visible y carga sin ceros aparentes.
- `frontend/src/app/pages/catalog/CatalogPage.tsx`, `RestaurantPage.tsx`, `CartPage.tsx`: navegación, carrito, acciones y móvil.
- `frontend/src/app/pages/client/CheckoutPage.tsx`: mismo lector de carrito y confirmación existente.
- `frontend/src/app/pages/client/DashboardPage.tsx`, `OrdersPage.tsx`, `ClaimsListPage.tsx`: errores diferenciados y reflujo.
- `frontend/src/app/pages/client/NewClaimPage.tsx`: pedidos cargados/erróneos/vacíos, reintento y selección válida.
- `frontend/src/app/pages/client/OrderDetailPage.tsx`, `ClaimDetailPage.tsx`: consulta sin respuestas obsoletas y fallos de API explícitos.

Pruebas e informe:

- `tests/test_phase2a_acceptance.py`: aceptación BF-14 sobre persistencia aislada y evidencia de ejecución.
- `frontend/e2e/phase2a.spec.ts`: unidad de parser y aceptación UI/errores/móvil.
- `frontend/e2e/audit-regressions.spec.ts`: títulos actualizados, expectativas originales conservadas.
- `docs/IMPLEMENTACION_FASE_2A.md`: este documento; auditoría/backlog/informe de Fase 1 permanecen históricos.

## Pendientes y riesgos de integración

1. **BF-12 / AF-25 sigue pendiente:** la campana no consulta automáticamente avisos nuevos al abrir. No se modificó ese comportamiento para obtener una suite completamente verde.
2. La configuración efectiva es única por la regla de selección, no por una restricción física de unicidad de `activo`. Las filas activas heredadas permanecen. BF-17 debe acordar su conciliación sin pérdida de datos.
3. El contrato PUT ahora exige `config_id`: frontend y backend deben desplegarse coordinadamente. Ediciones concurrentes sobre el mismo ID todavía siguen la última escritura; no se incorporó control de versiones optimista. El GET posterior detecta discrepancias, pero no sustituye ese control.
4. Validar transacción/rowcount/locks y tipos REAL en PostgreSQL aislado antes de desplegar. No se ejecutó ninguna ampliación de esquema en bases reales ni se requiere una migración nueva para Fase 2A.
5. El arranque heredado con semillas y ajuste potencialmente destructivo de dimensión vectorial sigue siendo riesgo de BF-17. Solo se arrancó sobre bases temporales. No iniciar esta validación apuntando a producción.
6. La vista de ejecución depende de trazas recientes persistidas. Artefacto presente no acredita validez; trazas antiguas sin modelo explícito no se reinterpretan. La calidad de generación externa no se verificó.
7. Elegibilidad de incidentes, precisión monetaria persistida, administración comercial, métricas completas y operación manual de pedidos no quedan resueltas por estos ajustes de UX. El enlace directo para reclamar algunos estados de pedido continúa dependiendo del alcance de BF-08; no se inventan reglas de elegibilidad.
8. La comprobación móvil corresponde a Chromium con viewport emulado y los escenarios descritos; no certifica todos los dispositivos, motores o combinaciones de accesibilidad.

## Recomendaciones para BF-12 y BF-07

**BF-12:** refrescar al abrir campana y tras acciones relevantes; distinguir carga/error/no leídos; mantener navegación aunque falle el marcado. Definir lectura individual frente a todas, asignación a usuarios activos, receptor explícito del escalado y notificaciones de entrada. Aprovechar la prueba AF-25 que continúa fallando como aceptación. No prometer tiempo real ni introducir polling sin necesidad acordada.

**BF-07:** acordar permisos del operador y política de cancelación/DELAYED antes de implementar. Añadir transiciones autorizadas con timestamps, actor, motivo e historial del pedido; conservar snapshots de Fase 1 y no confundir simulación con entrega/pago real. Probar PREPARING → IN_TRANSIT → DELIVERED, cancelación y carreras en bases aisladas. Preparar BF-06/17 para identidad y arranque seguro; no utilizar Supabase productivo como banco de pruebas.

## Conservación y cierre

La comparación final SHA-256 contra el inventario original de Fase 2A confirmó **7/7 archivos sin alteraciones**: los cinco binarios protegidos y ambos `.env`. Los binarios siguen mostrando los cambios locales que ya tenían antes de esta fase; no se restauraron, eliminaron ni agregaron al staging. No se publican credenciales.

La API temporal terminó correctamente y su `network.json` confirmó `unexpected: []`. Vite también fue detenido; no quedaron servidores de validación escuchando en 8000/5173. No hubo llamadas efectivas a OpenAI ni acceso a Supabase de producción. Las comprobaciones de esquema y configuración se ejecutaron exclusivamente en bases temporales/copias aisladas; no se ejecutaron migraciones sobre el archivo SQLite real.

Hay **31 archivos de texto modificados o nuevos de Fase 2A**, enumerados por responsabilidad arriba, además de los cinco binarios preexistentes. En la reanudación de cierre solo se actualizó este informe: no fue necesario corregir nuevamente la implementación. La revisión de patrones de credenciales no encontró coincidencias en esos archivos; `git diff --check` y la revisión de whitespace de archivos nuevos pasaron.

Estado final: rama `feature/optimizacion-flujo-ia`, HEAD `4f18a0ad14a00fa1959518b8b84f3aca90f42cee`, staging vacío y cambios locales conservados. No se realizaron commits, pushes, merges o despliegues, ni se cambió a `main`. Los resultados cierran el alcance local de Fase 2A y permiten continuar el desarrollo; no constituyen aprobación de producción. Permanecen los riesgos de PostgreSQL real, conciliación de configuraciones y arranque seguro descritos anteriormente.
