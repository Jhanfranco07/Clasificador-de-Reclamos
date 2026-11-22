# Auditoría funcional integral de SmartClaim AI

Fecha: 30 de octubre de 2026. Rama: `feature/optimizacion-flujo-ia`.

## Dictamen

Existe un prototipo integrado de compra simulada y gestión de reclamos con IA local. Se completó en navegador compra → registro de pedido → reclamo → sugerencia local → envío por agente → cierre → consulta del cliente. Eso **no acredita el ciclo comercial completo**: no hay operación para entregar o cancelar pedidos, pago conciliado, resolución económica registrada ni administración comercial.

La optimización FAQ/ML/RAG funciona en las pruebas locales. Los riesgos principales están en los contratos y reglas de negocio: pedidos construidos con datos arbitrarios del navegador, reclamos sin relación validada con un pedido, publicación prematura de borradores, estados inconsistentes y configuración que anuncia guardado sin persistirlo.

Esta es una auditoría, no una implementación. Los fallos encontrados permanecen sin corregir. No se proponen cambios a FastAPI, React, al clasificador ni a la arquitectura de IA optimizada.

## Método, límites y evidencia

- Lectura de frontend, 35 operaciones HTTP, modelos Pydantic, repositorios, esquemas, semillas, scripts y documentación.
- SQLite original abierta exclusivamente en modo de lectura para conteos y relaciones. Pruebas de escritura solo en bases temporales creadas para esta auditoría.
- FastAPI mediante TestClient y una segunda instancia local temporal para Chromium. Configuración y barreras de `tests/conftest.py`: sin cargar secretos del `.env`, clientes OpenAI/psycopg y transporte externo bloqueados; rutas de base/modelo/índices redirigidas.
- Chromium abortó solicitudes fuera de localhost/127.0.0.1, puertos 8000/5173. Las imágenes externas se bloquearon: su ausencia visual en las capturas no prueba que las URLs reales estén rotas.
- 32 combinaciones ruta/rol/viewport observadas después de cargar las pantallas, con anchos 1365 y 360 px. No equivale a cobertura de todos los dispositivos.
- Las comprobaciones PostgreSQL fueron de código/esquema y mocks de la suite existente. No se contactó Supabase. No se acredita integración PostgreSQL/pgvector real.
- Ninguna llamada real a modelos o embeddings externos. En las sondas de API, `openai_used=false`; los stubs de pytest no consumen tokens.

Evidencia de esta ejecución, conservada localmente:

- Directorio temporal: `C:/Users/PC/AppData/Local/Temp/smartclaim-functional-audit-jdizqk3g`.
- `api-results.json`: resultados agrupados de API; `browser-observations.jsonl`: observaciones de las iteraciones; `playwright-results.json`: última ejecución completa.
- Lanzadores/sondas: `audit_api.py`, `browser_backend.py`; datos: `api-audit.db`, `browser.db`, `extra.db`, exclusivamente temporales.
- Pruebas de navegador y capturas de fallos: `frontend/node_modules/.cache/smartclaim-functional-jdizqk3g/`, ignorado por Git. Se ejecutaron copias de las cinco pruebas originales y escenarios adicionales; las pruebas fuente no se modificaron.
- Las observaciones JSONL contienen iteraciones preliminares; utilizar la última observación de cada nombre. Se ajustaron esperas de carga y selectores del arnés antes de emitir este dictamen. No se atribuyen esos ajustes al producto.

No se deben ejecutar estos recorridos contra una API compartida. Los pasos de reproducción de los hallazgos presuponen usuarios ficticios y una base aislada.

## Resultados de ejecución

| Grupo | Resultado final | Interpretación |
|---|---|---|
| Suite pytest existente | **70 aprobadas, 0 fallidas**, 33,90 s | Verifica los contratos ya cubiertos; no certifica coherencia comercial. |
| Playwright ampliado | **12 aprobadas, 7 fallidas**, 19 escenarios, 56,2 s | Incluye las cinco pruebas originales aprobadas y comprobaciones de negocio que revelan defectos. |
| Bloqueo externo pytest | 0 intentos inesperados; 14 sondas rechazadas | Las sondas prueban las barreras, no son llamadas enviadas a proveedores. |
| API de auditoría | Observaciones HTTP/SQL reproducibles | No se contabilizan como tests aprobados las solicitudes que aceptaron datos incorrectos. |
| Ciclo de estados de pedido | **Bloqueado** | No existe endpoint/interfaz para operador; no se sustituyó por SQL para aparentar entrega. |
| Comercio/sucursal/promoción | **Bloqueado/inexistente** | No hay rol, pantalla ni operaciones de mantenimiento que permitan esos recorridos. |
| PostgreSQL/pgvector real | **Pendiente** | Sin servidor aislado disponible; no se usó producción. |

Las siete expectativas de navegador fallidas fueron: ocultar borrador no aprobado, filtrar ayuda, persistir configuración, representar catálogo vacío, permitir detalle público anunciado, recuperar carrito corrupto y refrescar notificaciones. Los tiempos anteriores son de ejecución de pruebas, no benchmarks.

Una prueba adicional de restaurante sin productos pasó al comprobar únicamente ausencia de excepción. Una sonda posterior mostró que agrega un artículo sin identificador/precio y muestra `NaN`; **esa prueba aprobada no valida la compra**, véase AF-17.

## Arquitectura y módulos reales

```text
React/Vite → cliente HTTP con Bearer → FastAPI → repositorios SQL
                                                 ├─ SQLite local
                                                 └─ PostgreSQL opcional mediante psycopg

Chat → intención ligera → FAQ documental o consultas existentes/RAG general
Reclamo explícito → persistencia → ML y reglas → RAG con alcance → sugerencia
                                                            → agente → respuesta/estado
```

| Módulo | Estado | Dependencias/observación |
|---|---|---|
| Autenticación/perfil | Real local | `auth_users`, hash PBKDF2, token HMAC propio; CLIENT/AGENT/ADMIN. Recuperación de contraseña simulada. |
| Catálogo | Lectura real + respaldo ficticio | `restaurantes` y `productos`; filtro de activos/disponibles en lectura. Sin mantenimiento administrativo. |
| Carrito | Local | Clave de `localStorage` compartida por navegador; sin reserva ni validación de inventario. |
| Checkout | Persistencia real, pago simulado | Envía nombres y precios; cargos añadidos como productos. |
| Pedidos | Crear/consultar real; operación incompleta | Estado inicial, ETA calculada y nombre de repartidor de ejemplo; sin transiciones ni GPS. |
| Reclamos | CRUD parcial y atención real | Alta/lectura/estados/conversación; relación al pedido por texto y sin validación comercial. |
| ML/NLP | Real local | TF-IDF + Logistic Regression, reglas, prioridad y análisis léxico. |
| FAQ/RAG | Real local | FAQ activa; TF-IDF y filtros; JSON/pgvector opcionales no probados contra proveedor real. |
| Respuestas | Plantillas y flujo humano reales, con defecto de publicación | Edición, aprobación, mensaje, notificación; contratos no separan borrador/final de forma segura. |
| Documentos | Administración real | Crear/editar/desactivar/reindexar; sin versiones ni audiencia formal. |
| Configuración IA | Pantalla y endpoint; guardado defectuoso | Lectura real, PUT 200 que no cambia la fila sembrada. |
| Notificaciones | Persistencia real; actualización UI incompleta | Eventos de mensajes/respuestas; sin señal de entrada para reclamo nuevo ni refresco de campana. |
| Dashboard/reportes | Consultas reales, algunos alcances incorrectos | CSV y PDF descargados en Chromium. |
| Auditoría técnica IA | Persistencia real | JSON en `logs_sistema`, sin vista administrativa de trazas. |
| Comercio, sucursal, promociones, repartidores, conciliación/reembolsos | Inexistentes como módulos operables | Textos, imágenes o métodos de pago no equivalen a esas capacidades. |

## Inventario de pantallas, controles y conexión

Se revisaron los 21 archivos de páginas y sus componentes compartidos. `LandingPage.tsx` reexporta el catálogo; no es un módulo comercial adicional. Los componentes UI genéricos no son pantallas funcionales por sí mismos.

| Pantalla / ruta | Formularios, botones y operaciones | Conexión y limitaciones |
|---|---|---|
| Catálogo `/`, `/restaurants`, `/products` | Filtros comerciales, ver restaurante, agregar, destacado, cantidades, eliminar, checkout, login/registro/logout, enlaces al carrito | GET catálogo + carrito local; categorías son texto, destacado fijo; fallback sin aviso. |
| Restaurante `/restaurants/:id` | Volver, agregar cada producto | GET catálogo completo y selección local; sin dirección/contacto del establecimiento ni gestión de disponibilidad. Requiere login por el router. |
| Login `/login` | Correo/contraseña, iniciar, recuperar, registro, volver | Login real; reset simulado; error de conexión confundido con credenciales. |
| Registro `/register` | Nombre/correo/teléfono/contraseña/confirmación, crear cuenta y enlaces | POST registro; siempre cliente. No es alta de comercio ni agente. |
| Inicio cliente `/dashboard` | Explorar, crear reclamo, ver pedidos/reclamos/ayuda | GET pedidos y primera página de reclamos; contadores incompletos cuando hay más de diez. |
| Carrito `/cart` | Más/menos, eliminar, continuar, explorar | Solo almacenamiento local; «Total» no incluye todos los cargos del checkout. |
| Checkout `/checkout` | Dirección, referencia de entrega, método y referencia de pago, confirmar, volver | POST pedido; las dos referencias se descartan; no transacción financiera. |
| Pedidos `/orders` | Ver detalle; reportar problema solo en DELIVERED/DELAYED; explorar cuando vacío | GET propios. No cancelar ni actualizar estado. |
| Pedido `/orders/:id` | Volver, crear reclamo en DELIVERED/DELAYED | GET detalle; sin historial de transiciones, comprobante, tienda enlazada ni seguimiento geográfico. |
| Nuevo reclamo `/claims/new` | Selector de todos los pedidos propios, descripción, enviar/cancelar; diálogo con código y enlaces | GET pedidos + POST reclamo con análisis. No advierte incidentes anteriores ni plazo. |
| Reclamos `/claims` | Crear, fechas, limpiar, abrir detalle, anterior/siguiente | GET paginado. No agrupa incidentes del mismo pedido. |
| Reclamo `/claims/:id` | Línea de tiempo, respuesta, conversación, enviar mensaje, reabrir si cerrado | GET detalle/mensajes, POST mensaje/reapertura. No constituye expediente completo de soluciones/versiones. |
| Ayuda `/help` | Buscador, acordeones FAQ, crear reclamo, tarjetas chat/email, teléfono/email | FAQ hardcodeada; buscador/contactos sin acción, promesas no sustentadas. Es distinta de la FAQ del motor. |
| Perfil `/profile`, `/admin/profile` | Editar nombre/teléfono, guardar; correo bloqueado | PATCH perfil real; no gestión de terceros, contraseña o roles. Título de tarjeta sin `h1`, observación semántica menor. |
| Dashboard `/admin`, alias `/admin/dashboard` | Indicadores, distribuciones, recientes | GET dashboard; no consolida operación de pedidos/comercios. |
| Bandeja `/admin/claims` | Búsqueda, fechas, estado, paginación, abrir caso | GET global para staff; sin filtro/asignación por comercio o responsable. |
| Detalle staff `/admin/claims/:id` | Analizar si falta análisis, generar sugerencia, editar/guardar/cancelar, enviar, escalar, cerrar, reabrir, notas y conversación | Endpoints existentes; solo código de pedido, no artículos/importe. Analizar de nuevo existe por API, sin control equivalente visible tras análisis. |
| Documentos `/admin/knowledge`, alias `/admin/documents` | Búsqueda, título/tipo/categoría/contenido, crear, editar, cancelar edición, desactivar, reindexar | CRUD documental y reindexación reales; categoría de texto libre; no versiones. |
| IA `/admin/ai-config`, alias `/admin/settings` | Switch RAG/revisión, umbral, máximo de documentos, guardar; selector de modelo deshabilitado | GET/PUT; guardado no persistente sobre semilla. El modelo informado no coincide con el artefacto. |
| Reportes `/admin/reports` | Fechas/estado/categoría/prioridad, CSV, PDF | GET reportes y exportación cliente; mezcla agregados globales y filtrados. |
| Compartidos | Menú de cuenta, tema, salir, campana, marcar leídas, navegación, chatbot | Navegación/tema reales; la campana solo carga al montar. Chat usa API, contexto local de carrito y respuestas por reglas/FAQ/RAG. |

`/notifications` redirige a reclamos; no hay bandeja independiente. La navegación cliente está protegida por autenticación sin limitar sus rutas a CLIENT; el backend sí restringe operaciones de compra. No se detectó doble cabecera por los wrappers de layout: existe un contexto que evita su duplicación.

### Contratos HTTP

| Familia | Operaciones implementadas |
|---|---|
| Salud/chat | GET `/health`; POST `/api/chat` con identidad opcional. |
| Auth | POST login, registro, solicitud de reset; GET/PATCH `/api/auth/me`. |
| Catálogo | GET `/api/catalog`, sin escritura. |
| Notificaciones | GET `/api/notifications`, PATCH `/api/notifications/read`; este último marca todas, no una notificación. |
| Pedidos | GET/POST `/api/orders`; GET `/api/orders/{id}`. Listado de staff devuelve vacío. |
| Dashboard/reclamos | GET dashboard; GET/POST claims; GET claim; GET/POST messages; POST close/reopen/analyze; PATCH state; GET/POST comments. |
| Respuestas | PATCH `/api/responses/{id}`; POST `/api/responses/{id}/approve`. |
| Documentos | GET/POST documents; PUT/DELETE document; POST documents/reindex. |
| Configuración/reportes | GET/PUT config; GET reports. |

No se encontraron endpoints de administración de usuarios, comercios, productos/promociones, ciclo de pedidos, asignación de agentes, resolución económica o consulta de trazas. `asignar_responsable`, evaluaciones y listados de logs existen como funciones de repositorio, pero no están expuestos como operaciones de usuario.

## Hallazgos reproducibles y reglas pendientes

Leyenda: **D** defecto confirmado por ejecución; **C** capacidad incompleta confirmada por código/ausencia de contrato; **RN** decisión de negocio no definida; **R** riesgo técnico identificado por inspección, sin afirmar un incidente real. P0: antes de otra demostración con usuarios/datos sensibles; P1: necesario para MVP coherente; P2: consolidación. La severidad expresa impacto, no volumen de explotación.

### Seguridad, identidad y contratos

**AF-01 — Pedido fabricado desde el cliente [D · Alta · P0].**
- Evidencia/reproducción: POST `/api/orders` con comercio/producto inexistentes, precio 0 y método arbitrario → 201, total 0 y PREPARING. Con cadenas de espacios en tienda/dirección/artículo → 201. La lectura sí filtra disponibilidad, pero la compra no la verifica.
- Causa: `OrderCreate` acepta snapshots y `crear_pedido_cliente` suma valores enviados; no hay referencias al catálogo. Afecta `backend/main.py:135`, `:709`, `database/repositories.py:122`, checkout y esquema.
- Propuesta: aceptar identificadores/quantity, resolver comercio, disponibilidad y precios en servidor, validar texto tras trim y persistir snapshots. Pruebas: producto inexistente/inactivo, precio alterado, cantidades y cadenas vacías, total autorizado.

**AF-02 — Reclamo sin pedido válido o propio [D · Alta · P0].**
- Evidencia/reproducción: con correo del cliente A, enviar el código del pedido de B o `DOES-NOT-EXIST` → 201 en ambos. Leer pedido/reclamo ajeno sí devuelve 403. SQLite original contiene un reclamo cuyo código no enlaza a ningún pedido.
- Causa: se compara el correo del payload, no la propiedad del pedido; `reclamos.codigo_pedido` carece de FK. Afecta `backend/main.py:782`, `crear_reclamo` y ambos esquemas.
- Propuesta: resolver pedido desde la identidad autenticada, mantener intervención staff explícita y agregar relación estable al pedido tras reconciliar datos. Pruebas: código ajeno/inexistente rechazado; pedido propio aceptado; migración sin pérdida.

**AF-03 — Borrador expuesto y presentado como publicado [D · Crítica · P0].**
- Evidencia/reproducción: crear sugerencia; agente guarda edición sin aprobar. GET del cliente devuelve `status=EDITADA` y `finalResponse` con el borrador. Chromium mostró `DRAFT-NOT-APPROVED-AUDIT` antes del envío; la expectativa de ocultarlo falló. El historial traduce «Edición de respuesta» como «Respuesta publicada».
- Causa: `actualizar_respuesta_final` escribe también `respuesta_final`; DTO común y UI condicionada solo a existencia del texto. Afecta repositorios:479, API:350/948, `ClaimDetailPage.tsx:90/211`.
- Propuesta: separación borrador/publicación en persistencia y DTO por rol; publicar atómicamente solo al aprobar. Pruebas: borrador y notas internas invisibles por API/UI hasta publicación, incluso recarga y error de envío.

**AF-04 — Historial interno y metadatos enviados al cliente [D · Media · P1].**
- Evidencia/reproducción: PATCH state con comentario `INTERNAL AUDIT NOTE`; GET cliente contiene ese texto. También devuelve análisis, sugerencia y fragmentos internos aunque la pantalla no los muestre.
- Causa: mismo `_to_claim_detail` para cliente/staff; saneamiento solo visual. Afecta DTO y política de audiencia de documentos/historial.
- Propuesta: definir campos públicos e internos y filtrar en servidor. Pruebas: comentarios internos y metadatos no autorizados ausentes en JSON, manteniendo el seguimiento público útil.

**AF-05 — Atribución de agente incompleta [D/C · Media · P1].**
- Evidencia/reproducción: aprobar deja `id_usuario_revision=NULL`; mensajes aprobados usan `sender_id='support'`, historial conserva responsable genérico. Las tres respuestas de la SQLite original carecen de revisor. La firma textual no equivale a identidad auditable.
- Causa: IDs de autenticación y tabla heredada `usuarios` están separados; no se pasa actor a varias operaciones. Afecta seguridad, repositorios, historial, mensajes y esquema.
- Propuesta: identidad de actor consistente y snapshots de nombre para presentación. Pruebas: dos agentes distintos quedan diferenciados en aprobación, cierre, escalamiento y notas.

**AF-06 — Recuperación/acceso y errores aún de prototipo [C/R · Media · P1].**
- Evidencia: reset solo devuelve mensaje de simulación; `AuthContext` captura cualquier error de login como null y la página lo presenta como credenciales incorrectas. Hay cuentas demo en el arranque, secreto predeterminado en desarrollo y no se encontró rate limiting/revocación de sesión servidor. No se ensayó ataque contra servicios reales.
- Causa: implementación académica y manejo de errores agrupado. Afecta auth, seguridad, configuración y frontend.
- Propuesta: declarar reset simulado, distinguir red/401/503 y acordar controles de acceso para despliegue sin sustituir tecnología automáticamente. Pruebas: API caída, token expirado, usuario inactivo, secretos/semillas prohibidos en entorno productivo.

### Pedidos, catálogo y comercio

**AF-07 — Pedido sin ciclo de operación [C · Alta · P1].**
- Evidencia/reproducción: pedido nuevo permanece PREPARING; PATCH por CLIENT, AGENT o ADMIN a `/api/orders/{id}` → 405. No existe pantalla de operador. Escenario B bloqueado.
- Causa: solo alta/lectura; enum no implica transiciones, permisos, historial ni notificaciones. Afecta API, repositorios, pedidos y backoffice.
- Propuesta: operador ADMIN para MVP y máquina mínima de estados con historial. Pruebas: preparación→en camino→entregado, cancelación autorizada, cancelado→entregado rechazado y concurrencia.

**AF-08 — «Total pagado» sin pago registrado [D/C · Alta · P1].**
- Evidencia/reproducción: checkout sin proveedor financiero crea pedido; detalle dice `Total pagado: S/ 40.80`, incluso si método fuera efectivo o arbitrario. No hay transacción, conciliación o reembolso.
- Causa: método de pago es texto y se interpreta como confirmación financiera. Afecta checkout, detalle, esquema y ayuda.
- Propuesta: distinguir importe del pedido, pago simulado/pendiente y pago confirmado; no anunciar devoluciones sin evento registrado. Pruebas: efectivo/simulación nunca producen comprobante o estado financiero real.

**AF-09 — Totales y cargos con criterios distintos [D · Media · P1].**
- Evidencia: primer producto 32,90 y delivery del catálogo 4,90; catálogo calcula 37,80, carrito dedicado llama «Total» a 32,90, checkout usa delivery fijo 5,90 + servicio 2,00 y persiste 40,80. Delivery/Servicio se almacenan como artículos normales.
- Causa: tres cálculos frontend y ninguna cotización del servidor. Afecta `CatalogPage.tsx:271`, `CartPage.tsx:14`, `CheckoutPage.tsx:45/80`, pedidos.
- Propuesta: un desglose autorizado de subtotal/cargos/total, aclarar cuándo se cotiza y tipificar cargos. Pruebas: mismos importes en catálogo/carrito/checkout/pedido y precisión monetaria.

**AF-10 — Referencias solicitadas y descartadas [D · Media · P1].**
- Evidencia/reproducción: completar referencia de entrega y referencia de pago; capturar POST de checkout: ninguna viaja. Datos `AUDIT-DELIVERY-NOTE` y `AUDIT-PAYMENT-REF` ausentes del payload y no disponibles al soporte.
- Causa: estados de formulario sin correspondencia en el contrato. Afecta checkout, `OrderCreate` y persistencia.
- Propuesta: conservar solo datos útiles y no sensibles, o retirar campos que no se procesan; no pedir información de pago innecesaria. Pruebas: ida/vuelta de notas y minimización de referencias.

**AF-11 — Carrito de varios comercios sin política ni separación [RN/C · Alta · P1].**
- Evidencia/reproducción: agregar productos de Criollo Peruano y Cevichería La Marina conserva ambos. Checkout toma únicamente `cart[0].restaurantName`; los artículos no llevan comercio ni producto referenciados. No se presupone que varios comercios deban prohibirse.
- Causa: modelo de pedido monocomercio con carrito libre. Afecta carrito, cotización, pedido, responsabilidad de incidencias.
- Propuesta: decidir monocomercio con confirmación al cambiar, o partición en subpedidos. Para MVP, monocomercio es la opción de menor complejidad. Pruebas: ningún artículo atribuido al comercio equivocado y cargos coherentes con la decisión.

**AF-12 — Catálogo simulado indistinguible de catálogo vacío [D · Alta · P1].**
- Evidencia/reproducción: interceptar GET catálogo con `{items:[]}` → se muestran 12 enlaces «Ver restaurante» del fallback. También se usa fallback ante error. No se avisa que son datos de muestra.
- Causa: `apiRestaurants.length > 0 ? apiRestaurants : fallbackRestaurants`. Afecta catálogo y detalle restaurante.
- Propuesta: separar carga/vacío/error/demo explícita; no permitir compra aparente de un catálogo ficticio cuando no hay catálogo disponible. Pruebas: 200 vacío y 503 no aparentan operación real.

**AF-13 — Acceso público a detalle contradice recorrido anunciado [D/RN · Baja · P2].**
- Evidencia/reproducción: visitante pulsa «Ver restaurante» desde catálogo → `/login`; documentación técnica enumera detalle entre funciones públicas. La compra pública puede añadir desde el catálogo, pero no abrir ese detalle.
- Causa: `/restaurants/:id` está dentro de ProtectedRoute. Afecta router y documentación.
- Propuesta: decidir política pública y hacer coherentes enlaces/expectativas; exigir login al confirmar compra si ese es el MVP. Pruebas: visitante explora detalle y conserva destino/carrito al autenticarse, o ve claramente la restricción acordada.

**AF-14 — Sin administración comercial ni actor comercio [C · Alta · P1].**
- Evidencia: GET catálogo es la única operación; POST catálogo → 405, `/api/users` → 404. No hay pantallas de comercios, productos, promociones o sucursales. Solo restaurantes/productos sembrados.
- Causa: alcance centrado en soporte, con catálogo de demostración. Afecta modelo comercial, API y backoffice.
- Propuesta: ADMIN mantiene establecimientos/productos en MVP; justificar autoservicio de comercio antes de agregar un rol. Pruebas: altas/cambios/disponibilidad reflejados en catálogo y compra, con permisos.

**AF-15 — Promociones, marca y responsable comercial sin entidad operable [C/RN · Media · P2].**
- Evidencia: destacado «Combo urbano» a 32,90 toma el primer producto del primer restaurante; no hay promoción, vigencia o descuento asociado. Restaurante tiene nombre/categoría/imagen/rating/ETA/delivery, pero no dirección, responsable o pertenencia comercial.
- Causa: presentación comercial sobre datos simples. Afecta catálogo y modelo propuesto, no prueba vinculación a marcas reales.
- Propuesta: describirlo como selección destacada o referenciar un producto; modelar establecimiento y responsable primero. Empresa/marca/sucursal solo si hay múltiples establecimientos bajo un mismo operador o identidad compartida. Pruebas: cada destacado apunta al artículo anunciado y tiene precio/vigencia verificables si se denomina promoción.

**AF-16 — Carrito corrupto deja pantalla vacía [D · Media · P1].**
- Evidencia/reproducción: en navegador de prueba guardar JSON inválido en `smartclaim_pending_cart` y abrir `/cart` → errores JSON y cuerpo vacío. La prueba de recuperación falló.
- Causa: parseo sin protección en CartPage y RestaurantPage; no hay validación común del esquema. Afecta almacenamiento local y presentación.
- Propuesta: lector único validado, recuperación controlada y mensaje visible. Pruebas: JSON inválido, tipos erróneos y artículos incompletos no inutilizan navegación.

**AF-17 — Destacado añade artículo inválido si no hay productos [D · Media · P1].**
- Evidencia/reproducción: respuesta catálogo con primer restaurante sin productos; pulsar destacado. No hubo excepción en la comprobación inicial, pero la sonda posterior guardó solo `restaurantName`, `restaurantImage`, `quantity` y mostró `NaN`.
- Causa: acceso a `products[0]` sin comprobar disponibilidad, spread de undefined y cálculo con precio ausente. Afecta catálogo/carrito/checkout.
- Propuesta: deshabilitar destacado sin producto válido y validar artículos en todas las entradas. Pruebas: restaurante vacío y producto retirado entre carga/compra sin artículos fantasma.

### Reclamos, atención y resolución

**AF-18 — Elegibilidad temporal/por estado no definida [RN/C · Alta · P1].**
- Evidencia: selector incluye pedido de 2019 ya reclamado y cancelado sin señal de incidentes; API acepta un pedido cancelado antiguo y una `order_date` futura suministrada por el cliente. Listado/detalle de pedidos solo ofrecen enlace para entregados/demorados, pero formulario incluye todos.
- Causa: no hay política ejecutable, fecha de entrega real ni endpoint de elegibilidad. Afecta pedidos, formulario, API y documentos.
- Propuesta: acordar plazos por incidente, fecha base y excepciones; permitir retrasos antes de entrega y pagos tras cancelación cuando corresponda. No bloquear automáticamente todo pedido antiguo/cancelado. Pruebas: límites de plazo, demora sin entrega, cobro tras cancelación y excepción manual.

**AF-19 — Sin idempotencia ni distinción entre duplicado e incidente nuevo [D/RN · Alta · P1].**
- Evidencia/reproducción: repetir el mismo POST crea dos pedidos; repetir reclamo para mismo cliente/pedido/texto devuelve dos 201 e IDs distintos. Selector no informa reclamos relacionados.
- Causa: ausencia de clave de solicitud y agrupación de incidentes. La coincidencia por pedido no demuestra duplicado de negocio.
- Propuesta: idempotencia de transporte; mostrar incidentes abiertos/cerrados y permitir continuar, reabrir o describir uno distinto. Pruebas: reintento crea un único recurso; dos problemas legítimos del mismo pedido conservan casos separados y relacionados.

**AF-20 — Estados de reclamo incoherentes y cierre sin solución [D/C · Alta · P0].**
- Evidencia/reproducción: marcar RESPONDED sin respuesta → 200; reabrir un caso no cerrado → 200; cerrar y luego aprobar → RESPONDED con `closedAt` aún presente. No hay resultado estructurado que distinga solución ofrecida/aceptada/rechazada de cierre administrativo.
- Causa: funciones validan nombre de estado, no transición/invariantes; cierre no exige motivo/resultado. Afecta endpoints de estado/cierre/aprobación, repositorios, métricas y UI.
- Propuesta: una máquina de estados y resultado de atención; aprobación no revive un cerrado silenciosamente. Pruebas: matriz de transiciones por rol, fechas coherentes y cierre sin solución explícitamente diferenciado.

**AF-21 — Aprobación repetida duplica publicaciones [D · Media · P1].**
- Evidencia/reproducción: aprobar dos veces mismo `response_id` → dos 200, dos mensajes y notificaciones. La UI mantiene acción de envío disponible después de publicar.
- Causa: operación no idempotente y sin precondición de revisión. Afecta aprobar_respuesta y detalle staff.
- Propuesta: transición de revisión atómica/idempotente, controlar reenvío explícito y deshabilitar acción ya completada. Pruebas: doble clic/reintento concurrente produce un solo evento de publicación.

**AF-22 — Reanálisis oculta la respuesta publicada en el resumen [D · Media · P1].**
- Evidencia/reproducción: publicar, POST analyze otra vez → última respuesta PENDIENTE con final null, aunque los mensajes publicados sigan existiendo. `obtener_detalle_reclamo` selecciona solo mayor ID; el análisis previo se borra al guardar uno nuevo.
- Causa: borrador más reciente sustituye la vista de publicación vigente; no hay historial/versionado de análisis. Afecta repositorios, DTO, atención y trazabilidad.
- Propuesta: mantener publicación vigente e historial de análisis/sugerencias separados. Pruebas: reanalizar no retira respuesta visible y conserva modelo, entrada y documentos de cada ejecución.

**AF-23 — Agente e IA sin contexto estructurado del pedido [D/C · Alta · P1].**
- Evidencia: detalle JSON no contiene pedido; en Chromium agente ve código, pero no «Lomo saltado» ni 40,80 del pedido comprado. `_analyze_and_generate_traced` consulta reclamo/cliente, no pedido/artículos/pagos.
- Causa: vínculo textual y contrato de respuesta limitado. Afecta detalle staff, repositorios y construcción del contexto IA.
- Propuesta: contexto autorizado de pedido y artículos, distinguiendo hechos registrados de lo relatado; sugerencias nunca confirman reembolso/entrega/compensación ausentes. Pruebas: importe/artículo verificables, pedido inexistente bloqueado y alegaciones contradictorias sin decisiones automáticas.

**AF-24 — Asignación y escalamiento sin destino/responsable operable [C/D · Alta · P1].**
- Evidencia: escalar solo cambia estado; no bandeja/destinatario, SLA, asignación ni permisos de supervisor. Helper de responsable sin endpoint; el payload permite texto `ARBITRARY ASSIGNMENT` desde un cliente. Nuevos reclamos no notifican al staff: delta observado 0.
- Causa: actor y responsabilidad expresados por texto, no una asignación validada. Afecta API, modelo, bandeja y notificaciones.
- Propuesta: ADMIN/AGENT con asignación a usuarios activos y escalamiento a ADMIN para MVP, con motivo y aviso. Pruebas: cliente no elige responsable, agente receptor recibe caso, escalamiento tiene destino y seguimiento.

**AF-25 — Notificaciones de campana quedan antiguas [D · Media · P1].**
- Evidencia/reproducción: cliente abre inicio; un agente responde por API; abrir campana conserva 3 mientras API tiene 4 no leídas. La prueba falló.
- Causa: carga depende solo del rol al montar. Afecta ClientLayout y coordinación de eventos.
- Propuesta: refrescar al abrir y después de acciones relevantes; decidir si hace falta polling, sin presumir tiempo real. Pruebas: aviso nuevo aparece sin recarga completa y lectura individual/todas es explícita.

### IA, conocimiento, reportes y persistencia

**AF-26 — Ayuda promete capacidades no implementadas [D/C · Alta · P0].**
- Evidencia: HelpCenterPage afirma reembolsos automáticos, GPS en tiempo real, cambios en cinco minutos, respuesta en cinco minutos/dos horas y cumplimiento PCI DSS. No hay pagos/reembolsos/GPS/cambio de pedido ni soporte técnico verificable para esas afirmaciones. Checkout ofrece Yape/Plin; ayuda menciona PayPal y otras opciones.
- Causa: contenido fijo de demo separado de políticas operativas. Afecta ayuda, documentación y confianza del cliente.
- Propuesta: retirar afirmaciones no sustentadas; usar textos aprobados y declarar simulación. Pruebas: ninguna promesa operativa/financiera fuera del alcance y vocabulario consistente. No se emitió una certificación legal ni de cumplimiento.

**AF-27 — Buscador y contactos de ayuda aparentes [D/C · Media · P1].**
- Evidencia/reproducción: escribir una consulta imposible conserva las preguntas; Input no tiene handler. Tarjetas chat/email y botones teléfono/email no tienen enlace ni acción. Contacto español de muestra en producto orientado a Lima.
- Causa: elementos visuales sin operación conectada. Afecta HelpCenterPage.
- Propuesta: búsqueda funcional sobre conocimiento autorizado y contactos reales o explícitamente simulados. Pruebas: filtrar/restablecer y cada acción ejecuta su destino o se muestra indisponible.

**AF-28 — Guardado de configuración devuelve éxito sin guardar [D · Alta · P1].**
- Evidencia/reproducción: PUT con umbral 0,6/RAG false/máximo 1 devuelve 200 con 0,85/true/3; UI anuncia «Configuración guardada. RAG: activo» y al recargar sigue true.
- Causa confirmada: semilla `Configuracion principal`, UPDATE busca `Configuración principal`. La SQLite original tiene además dos filas activas, elegidas por mayor ID.
- Propuesta: actualización por ID activo, unicidad de configuración efectiva y verificación de filas afectadas. Pruebas: ida/vuelta de cada parámetro, semilla limpia y copia con múltiples activas sin pérdida silenciosa.

**AF-29 — Modelo mostrado no coincide con modelo ejecutado [D/C · Media · P2].**
- Evidencia: GET config sobre semilla devuelve `modelo_simulado_reglas`; el pipeline real cargado por pytest es TF-IDF/Logistic Regression. Selector deshabilitado solo ofrece `modelo_ml_tfidf_logistic_regression`.
- Causa: metadatos históricos de semilla usados como estado operativo. Afecta configuración y transparencia de IA.
- Propuesta: informar artefacto/proveedor realmente utilizado y fallback separado. Pruebas: modelo disponible/ausente y reglas reportados sin confundir clasificación y generación.

**AF-30 — Reportes mezclan períodos y conceptos [D · Media · P1].**
- Evidencia/reproducción: filtro desde 2099 produce total 0, pero analizados 1, respuestas 2 y grupos de confianza/revisión no vacíos. `tasa_automatizacion` mide reclamos analizados, no respuestas autónomas, aunque hay aprobación humana.
- Causa: solo parte de métricas aplica `scoped`; etiquetas no definen denominador. Afecta endpoint reports, métricas y CSV/PDF.
- Propuesta: alcance único o rotulado global explícito y diccionario de métricas. Pruebas: período vacío produce todos los agregados de ese período vacíos; conteos/porcentajes/exportación coherentes.

**AF-31 — Dashboard cliente cuenta solo primera página [D/C · Media · P1].**
- Evidencia: con 12 reclamos abiertos, GET devuelve 10 ítems y pagination.total=12; DashboardPage calcula sus contadores desde esos ítems. Los recientes pueden limitarse; los totales no deberían confundirse con ellos.
- Causa: consumo del listado paginado como agregado. Afecta inicio cliente y contrato de métricas.
- Propuesta: agregados por cliente o uso de totales adecuados, manteniendo permisos. Pruebas: 0/10/12/100 casos abiertos y cerrados sin truncar indicadores.

**AF-32 — Consulta de un código inexistente responde por otro pedido [D · Media · P1].**
- Evidencia/reproducción: chat autenticado pregunta `Estado del pedido ORD-NO-EXISTE`; devuelve estado del último pedido real del usuario. No inventa ese registro, pero lo atribuye a una consulta no resuelta.
- Causa: `matched_order or last_order`; análogo para reclamos. Afecta chatbot_service.
- Propuesta: código explícito sin coincidencia debe responder «no encontrado/no accesible», y reservar último pedido para preguntas sin código. Pruebas: código propio, ajeno, inexistente y consulta de último pedido.

**AF-33 — Documentos sin versión/audiencia verificable [C/R · Media · P2].**
- Evidencia: categorías documentales de texto libre; `documentos_consultados` conserva un fragmento truncado y referencia a documento mutable, no versión; FAQ puede contener instrucciones para operadores y devolverse literalmente al público. Ayuda tiene otra fuente fija.
- Causa: repositorio único sin distinción editorial/audiencia/versiones. Afecta base documental, FAQ/RAG y evidencia de respuestas.
- Propuesta: una fuente autorizada con tipo/audiencia y versión o snapshot suficiente de evidencia. No duplicar FAQs ni agregar taxonomías innecesarias. Pruebas: documento editado/desactivado no altera la evidencia histórica y contenido interno no se publica como FAQ cliente.

**AF-34 — Integridad y dinero insuficientemente restringidos [D/R · Alta · P1].**
- Evidencia: escritura directa en base temporal admite cantidad -2/precio -10; ambos esquemas carecen de CHECK de cantidades/importes de pedidos/items. Clientes se identifican por correo sin unicidad case-insensitive; pedidos/items no enlazan catálogo y respuesta/actor usa identidad heredada. Importes REAL y códigos basados en COUNT+1 añaden riesgos de redondeo/concurrencia; no se afirmó haber reproducido esas carreras.
- Causa: invariantes en capa parcial y referencias textuales. Afecta ambos esquemas/repositorios.
- Propuesta: restricciones coherentes tras saneamiento, moneda/precisión acordada, IDs generados sin COUNT y transacciones para altas compuestas. Pruebas: integridad ante SQL/importaciones, fallos parciales, reintentos y concurrencia en ambos proveedores.

**AF-35 — Paridad/migración SQLite-PostgreSQL incompleta [C/R · Alta · P1].**
- Evidencia: tablas y columnas comunes son equivalentes en la revisión estática; PostgreSQL añade `rag_embeddings` y usa TIMESTAMP/SERIAL frente a TEXT/AUTOINCREMENT. La migración omite auth, pedidos/items, restaurantes/productos, mensajes, notificaciones y embeddings; confirma tabla por tabla. No se ejecutó contra servidor real.
- Causa: script anterior al alcance comercial y adaptación SQL manual. Afecta schemas, db_connection y migrate_sqlite_to_postgres.
- Propuesta: plan no destructivo con respaldo, inventario completo, conciliación, secuencias y pruebas de paridad. Pruebas: exportación/importación de fixture completa, totales/FK/identidades/fechas, pgvector aislado y recuperación de fallo parcial.

**AF-36 — Inicialización mezcla arranque y modificación de datos [C/R · Alta · P1].**
- Evidencia: lifespan ejecuta esquema/semillas/ajustes de usuarios/pedidos demo. El ajuste de dimensión pgvector puede borrar embeddings si difiere. Se inspeccionó código; solo se arrancó con rutas temporales.
- Causa: bootstrap de demo dentro del proceso web. Afecta backend y db_connection.
- Propuesta: separar operación normal de preparación explícita, con migración revisable y modo demo deliberado. Pruebas: reinicio de instancia productiva de prueba no cambia catálogo, usuarios o vectores.

**AF-37 — Trazas sin consulta administrativa y errores poco claros [C/D · Media · P2].**
- Evidencia: eventos IA reales en SQL; `/api/logs` → 404 y menú sin auditoría. Dashboard convierte errores de pedidos/reclamos en arrays vacíos; formulario de reclamo oculta fallos de listado como «sin pedidos». Varias excepciones de API incluyen texto técnico al cliente.
- Causa: herramientas de observación solo de repositorio y patrones de manejo de error dispares. Afecta logs, dashboards, API y experiencia de recuperación.
- Propuesta: consulta ADMIN limitada/sin contenido sensible; separar error, carga y vacío. Pruebas: 503, timeout, datos vacíos, trazas por operación y permisos de acceso.

**AF-38 — Desbordamiento en móvil [D · Media · P2].**
- Evidencia: tras cargar a 360 px, pedidos tiene scrollWidth 540 y base documental 449; captura de pedidos muestra importe/acciones fuera de pantalla. Las demás rutas medidas no presentaron ese desbordamiento global; no es una certificación de usabilidad integral.
- Causa probable: filas/tablas y encabezados con anchos mínimos sin apilado/scroll local. Afecta OrdersPage y KnowledgeBasePage.
- Propuesta: reflujo de tarjetas y tablas dentro de su contenedor. Pruebas: 320/360/768 px con nombres/importe largos, acciones accesibles y zoom.

## Persistencia observada, sin alterarla

La SQLite original pasó integridad y no tiene violaciones de las FK existentes. Eso no detecta relaciones que el esquema nunca declaró.

| Observación original | Resultado |
|---|---:|
| Pedidos / reclamos / productos | 4 / 3 / 14 |
| Reclamos sin pedido enlazable por código | 1 |
| Reclamos con dueño distinto en pedidos enlazables | 0 |
| Candidatos a duplicado exacto cliente/pedido/texto | 0 |
| Correos duplicados en clientes, normalizados | 0 |
| Configuraciones activas | 2 |
| Respuestas sin ID de revisor | 3 |
| Inconsistencia estado/fecha de cierre ya almacenada | 0 |

Las incoherencias de cierre y cantidades negativas se provocaron únicamente en bases temporales para demostrar que son posibles; no estaban presentes en los conteos originales.

### Relaciones que requieren decisión/cambio futuro

| Relación actual | Carencia | Propuesta a evaluar, no implementada |
|---|---|---|
| Producto → restaurante por FK | Correcta para catálogo simple; pedido no la utiliza | Mantener y referenciar producto/restaurante en pedido con snapshot histórico. |
| Pedido → cliente por FK | Cuenta auth vinculada indirectamente por correo | Vincular identidad estable tras reconciliar clientes/cuentas heredadas. |
| Reclamo → código de pedido libre | Sin propiedad/FK | ID de pedido y, opcionalmente, relación con uno o varios items afectados. |
| Reclamo → estado | Sin matriz de transición ni solución | Estado controlado, motivo de cierre y resultado de atención separado. |
| Pedido → estado enum | Sin historial/actor/entrega real | Historial de pedidos con actor, origen, motivo y timestamps. |
| Respuesta → revisor `usuarios` | No coincide con actor autenticado | Identidad de actor y publicación auditable, sin perder snapshots. |
| Documento/evidencia | Mutable y fragmento truncado | Versiones/snapshots y audiencia. |
| Restaurante | Sin responsable/dirección comercial | Establecimiento operativo mínimo; empresa/marca/sucursal solo con necesidad concreta. |
| Método/importe de pedido | Sin estado financiero | Simulación explícita; registro de conciliación/reembolso solo si se incorpora ese alcance. |

No se crearon tablas ni se ejecutaron migraciones.

## Actores: alcance actual y responsabilidad propuesta

| Actor | Realidad actual | Responsabilidad razonable para MVP |
|---|---|---|
| CLIENT | Compra simulada, consulta propia y reclamos | Identidad/pedido propio, descripción del incidente y aceptación/consulta de la solución; sin elegir agente ni confirmar pagos del servidor. |
| AGENT | Bandeja global, mensajes, análisis, respuesta, notas, cierre/escalamiento | Atención, propuesta y revisión; no inventar eventos comerciales ni tener mantenimiento de usuarios/catálogo por defecto. |
| ADMIN | Lo anterior + documentos/config/reportes | Catálogo y operación manual de pedidos inicialmente, asignaciones y resolución de escalados, configuración/auditoría. |
| Comercio | No existe como rol/interfaz/tenant | No agregarlo todavía. Si se requiere que cada operador gestione sus propios establecimientos/pedidos, justificar alcance y aislamiento antes de un rol/relación nueva. |
| Repartidor/supervisor/pagos | Nombres/textos, sin operación independiente | No simular permisos ni integraciones reales. ADMIN puede asumir tareas de demo explícitas; separar permisos solo al crecer el negocio. |

Empresa es operador legal/comercial; marca es identidad compartida; establecimiento/sucursal es el punto que prepara el pedido. Para un MVP de un punto por comercio basta establecimiento con responsable/dirección. Crear cuatro entidades desde el inicio sin esos casos añadiría complejidad sin resolver AF-01/02/07.

## Recorridos A–I: ejecutado frente a bloqueado

| Escenario | Resultado y límite |
|---|---|
| A Compra | Ejecutado por UI: restaurante, producto, carrito, checkout y pedido 201. Pago simulado, cargos/referencias con hallazgos. |
| B Operador lleva pedido hasta entrega | Bloqueado: ningún rol dispone de la operación; PATCH 405. No se alteró SQL para declarar éxito. |
| C Historial y reclamo | Ejecutado: consulta y alta desde formulario. Nuevo pedido PREPARING carece de enlace en detalle, pero aparece en selector global. |
| D Reconocer reclamos previos | Fallo funcional observado: selector no distingue el pedido antiguo con incidente abierto. No hay agrupación ni detección de duplicado. |
| E Agente atiende con IA local | Ejecutado: ve caso, clasificación y documentos, envía respuesta. Contexto de artículos/pago no disponible y aviso de entrada ausente. |
| F Resolución y consulta | Cierre y respuesta visibles ejecutados. Resolución económica/aceptación formal bloqueada por ausencia de modelo; cerrado no equivale a reembolsado. |
| G Métricas/trazabilidad ADMIN | Reportes y descargas CSV/PDF ejecutados. Trazas comprobadas por SQL en copia; sin vista ADMIN, no se declara ese recorrido completo. |
| H Acceso a recurso ajeno | Lectura pedido/reclamo ajeno rechazada con 403, también mensaje visible en UI. Registro de reclamo sobre código ajeno aceptado: AF-02. Modificación de pedidos no existe. |
| I Transiciones/duplicados/inconsistencias | Defectos reproducidos por API: cierre→aprobación, respondido sin respuesta, aprobación repetida, reintentos duplicados, datos arbitrarios. Cancelado→entregado no se ensayó como operación real porque falta el endpoint. |

## Flujo mínimo propuesto

Pedido: catálogo vigente → cotización servidor → confirmación idempotente → PREPARING → IN_TRANSIT → DELIVERED. Cancelación desde estados acordados por operador autorizado, con motivo. DELAYED conviene tratarlo como incidencia del proceso/ETA, o definir claramente sus transiciones si sigue como estado; no asumir entrega ni GPS.

Reclamo: pedido propio → elegibilidad por incidente → revisar casos relacionados → continuar/reabrir o registrar nuevo incidente → ML/RAG/contexto verificado → sugerencia interna → revisión/publicación → seguimiento → resultado y cierre coherentes. Plazos, compensaciones y reglas de reapertura requieren aprobación de negocio, no valores arbitrarios incorporados al código.

Chat/FAQ: preservar búsqueda directa documentada y las rutas personales autorizadas; un código explícito no encontrado nunca se sustituye silenciosamente por otro. Un FAQ no crea un reclamo formal.

## Documentación frente a implementación

- La documentación técnica reconoce pago/reset simulados, pero HelpCenter y detalle de pedido los presentan con afirmaciones incompatibles.
- La documentación describe escalamiento hacia supervisor/especialista; código solo registra estado/texto, sin responsable de destino.
- Se documenta detalle público de restaurante, pero el router exige sesión.
- `frontend/ENTREGA.md` conserva el relato de autenticación simulada; el código usa API real.
- `DICCIONARIO_DATOS.md` no cubre el esquema completo actual. `AUDITORIA_CALIDAD.md` lista como pendientes varias capacidades ya implementadas; no reemplaza esta evaluación funcional.
- Los informes anteriores de pruebas aprobadas son válidos para su alcance, pero no deben utilizarse como evidencia de todos los recorridos comerciales.

## Cierre de la auditoría

Priorizar AF-01/02/03/20/26 antes de presentar el sistema como operación confiable con datos de usuarios. Después completar ciclo de pedido, reglas de incidentes, contexto, asignación y veracidad financiera. El plan detallado está en [BACKLOG_MEJORAS_FUNCIONALES.md](BACKLOG_MEJORAS_FUNCIONALES.md).

Se conservaron código, variables, datos, modelo, índices y cambios previos. La comparación final de hashes de **132 archivos preexistentes**, incluidos ambos `.env`, la SQLite, modelo e índices, no detectó cambios. Solo se agregan los dos documentos solicitados; arneses/capturas/datos de auditoría están en ubicaciones temporales o ignoradas. La API temporal terminó correctamente y confirmó **0 intentos externos inesperados**; Vite también fue detenido. No hubo commits, pushes, despliegues ni escrituras sobre producción.
