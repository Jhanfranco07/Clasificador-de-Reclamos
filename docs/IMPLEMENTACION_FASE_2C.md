# Implementación de Fase 2C — BF-12

Trabajo del 6 de noviembre de 2026. Rama `feature/optimizacion-flujo-ia`, base `eb8dd2d91b4d5db220554ad065e00bacc07521bd`.

## Diagnóstico previo y evidencia de AF-25

Se revisaron la auditoría, BF-12 del backlog y los informes de Fase 1, 2A y 2B. Git comenzó únicamente con los cinco binarios protegidos modificados previamente. El inventario SHA-256 también incluye ambos `.env`.

La campana anterior consultaba al montar y al cambiar el rol, calculaba el contador desde una lista de hasta 20 registros y no consultaba al abrir. Abrir un aviso marcaba todos los avisos. Un error de GET se convertía en lista vacía. AGENT/ADMIN y los portales operativos carecían de campana.

AF-24 conservaba un helper de asignación por texto sin endpoint operativo. Escalar solo cambiaba estado y no asignaba destinatario. Los avisos por mensajes se escribían después del commit y sus excepciones se capturaban, permitiendo confirmar un mensaje sin persistir su aviso. La publicación aprobada sí era atómica e idempotente y se conserva esa garantía.

Antes de modificar el código se ejecutó la prueba histórica AF-25 sobre la base del commit. Con Playwright y Chrome local falló por la diferencia concreta **API 2 no leídas frente a campana 1**. La evidencia está en `baseline-af25-chrome.log`. Otros intentos agotaron tiempo creando la página o cargando login con Chromium. Un intento con Chromium sobre preview terminó aprobado tras una carga de dos minutos. Se conserva ese resultado variable y no se interpreta como corrección del código base.

Para diagnosticar el arranque lento se compiló el frontend base y se utilizó `vite preview` local en 5173. La API siempre fue `tests/serve_offline.py`, con SQLite/artefactos temporales y barreras de red. Los presupuestos extendidos usados durante ese diagnóstico no cambiaron expectativas de las pruebas históricas.

## Modelo de responsabilidad e identidad

- `responsable_auth_id` referencia `auth_users`. `responsable_asignado` permanece como snapshot legible. `id_usuario_asignado` conserva su FK histórica a `usuarios`. No se intenta asociar identidades por coincidencia de nombre.
- `fecha_asignacion` y `version_asignacion` permiten auditar y rechazar decisiones sobre una asignación antigua. El contador de versión corresponde a asignaciones/escalamientos, no a todas las ediciones del reclamo.
- AGENT puede asumir un caso sin responsable autenticado activo, exclusivamente para sí mismo. ADMIN puede asignar/reasignar a AGENT o ADMIN activos. No se asigna a CLIENT/MERCHANT/COURIER.
- Un responsable desactivado o que perdió el rol de soporte conserva su referencia e historial. El caso aparece en la bandeja no asignada efectiva y puede reasignarse. Las notas heredadas no se convierten silenciosamente en asignaciones autenticadas.
- Se conserva la lectura y atención global del staff existente. «Mis casos» es una vista de trabajo. No se introduce un aislamiento de lectura entre agentes que altere los permisos previos.

## Escalamiento

AGENT puede escalar un caso propio o no asignado. ADMIN puede escalar casos activos. Se exige motivo, versión y clave de solicitud. Un destinatario explícito debe ser ADMIN activo. Sin destinatario se selecciona el ADMIN activo de menor ID, regla determinista del MVP que no representa una especialidad real.

La operación actualiza estado a Escalado, responsable, fecha, versión, historial con actor/destinatario y notificaciones en una transacción. No cierra el caso. Repetir la misma clave/contenido devuelve el resultado existente. Otra solicitud sobre un caso ya escalado se rechaza. El seguimiento usa conversación/notas y la reasignación administrativa, preservando eventos anteriores.

## Notificaciones e integridad

Se amplía la tabla existente `notificaciones` con destinatario autenticado nullable, FK de pedido, tipo de evento y clave única. Se conservan correo, FK de reclamo, textos, fecha y estado de lectura históricos. Los registros antiguos sin estos campos permanecen como LEGACY.

| Evento | Destinatario determinado por backend |
|---|---|
| Nuevo reclamo | AGENT/ADMIN activos de la cola |
| Asignación/reasignación | Nuevo responsable y responsable anterior activo, sin duplicarlos |
| Escalamiento | ADMIN destinatario y responsable anterior activo |
| Respuesta aprobada | Cliente titular, una vez por respuesta |
| Mensaje del agente | Cliente titular |
| Mensaje del cliente | Responsable activo o cola de soporte activa |
| Cierre/reapertura | Cliente y responsable activo o cola |
| Eventos de pedidos | Titular, MERCHANT autorizados y COURIER asignado cuando corresponda |

Los avisos contienen textos genéricos y referencias de recurso, sin borradores, mensajes privados, contraseñas o tokens. Los motivos internos se conservan en el historial staff, no se copian al aviso público. Los eventos de pedido siguen usando el registro transaccional de Fase 2B y ahora generan enlaces operativos, sin un segundo emisor duplicado.

Creación, mensajes, cierre/reapertura, asignación y escalamiento pueden llevar clave de solicitud. Se conserva compatibilidad con llamadores antiguos sin clave, que generan una operación nueva. Las claves de mensaje/creación del frontend permanecen mientras no cambie el contenido. La aprobación conserva su identidad de respuesta como control de reintento.

`claim_commands` es un registro de comandos confirmados con FK de reclamo, actor, acción y payload. No duplica la conversación ni reemplaza el historial. Una clave con otra acción, actor, caso o contenido se rechaza. Evento, historial, comando y avisos se confirman juntos. Un error de persistencia revierte la operación completa.

SQLite usa `BEGIN IMMEDIATE`. PostgreSQL prepara el advisory lock operativo de Fase 2B antes de bloquear el reclamo con `FOR UPDATE`, también compartido por cambios de roles. Las notificaciones usan índice único de clave. Se admite el resultado sin fila de `INSERT ... ON CONFLICT DO NOTHING RETURNING`, sin tratar el reintento como una inserción fallida.

## Campana e interfaces

Una campana compartida se integra en ClientLayout, AdminLayout y el encabezado operativo de MERCHANT/COURIER.

- El backend calcula no leídas sobre todo el conjunto autorizado en una consulta con ventana, antes del límite de 20 filas.
- Se consulta al montar, abrir, recuperar foco/visibilidad y confirmar mutaciones locales de reclamos/pedidos/respuestas. Polling cada 30 segundos solo mientras la página está visible.
- Consultas simultáneas se agrupan. No se emite el evento de refresco para GET o para marcar lectura, evitando bucles. Lecturas y refrescos se coordinan para impedir que un GET anterior revierta visualmente una lectura confirmada.
- Hay carga, error, reintento, vacío, lectura individual y lectura de todos. El contador se toma de la respuesta del servidor. Marcar una no marca todas.
- Cada aviso abre el recurso y portal de su rol. Las filas antiguas sin recurso no reciben una relación inventada.
- La bandeja añade No asignados, Mis casos y Escalados, con responsable visible. El detalle añade asignación, toma propia, motivo y escalamiento a un ADMIN. El historial mantiene snapshots y actor autenticado.
- La cabecera administrativa oculta el texto de marca en móvil para conservar las tres acciones. Se mantiene la identidad visual y no se introduce un rediseño general.

## Permisos y privacidad

| Acción | CLIENT | AGENT | ADMIN | MERCHANT/COURIER |
|---|---|---|---|---|
| Notificaciones | Propias y recursos propios | Propias | Propias | Propias y pedidos autorizados |
| Marcar una/todas | Mismo alcance | Mismo alcance | Mismo alcance | Mismo alcance |
| Asumir | No | Solo para sí, si no hay responsable activo | Puede asignar | No |
| Reasignar | No | No | Sí, a soporte activo | No |
| Escalar | No | Propio/no asignado | Casos activos | No |
| Contexto interno/historial de asignación | DTO público propio | Alcance previo | Sí | No |

Los avisos por ID autenticado no se transfieren por coincidencia posterior de correo. Para avisos LEGACY se conserva la relación por correo. MERCHANT/COURIER solo pueden consultar avisos con FK de pedido y asignación/autorización vigente, incluso si en el pasado tuvieron un rol de soporte. La lectura de un ID ajeno o fuera de alcance devuelve 404. La desactivación sigue invalidando sesión mediante la consulta de usuario activo en cada petición.

## Persistencia y endpoints

Migración aditiva `20261106_phase2c`, posterior a Fase 2B. Añade referencias a `reclamos`, `historial_estados`, `respuestas_sugeridas`, `comentarios_agente`, `notificaciones`, índices y `claim_commands`. No reescribe actores históricos ni borra avisos. SQLite y PostgreSQL disponen del mismo contrato aditivo. El SQL PostgreSQL se entrega para ensayo aislado, sin acreditar ejecución contra servidor real.

El runner existente admite `--phase 2c` sobre copia SQLite con backup nuevo. Conserva el valor predeterminado 2b. Revertir código conserva las columnas/tablas aditivas y los eventos. Se rechaza un downgrade destructivo desde el runner. El arranque normal sigue sin migrar ni sembrar.

| Endpoint | Contrato |
|---|---|
| `GET /api/claim-assignees` | Staff, identidades activas AGENT/ADMIN |
| `POST /api/claims/{id}/assignment` | ID verificado, versión, motivo y clave |
| `POST /api/claims/{id}/escalate` | Destino ADMIN opcional, versión, motivo y clave |
| `GET /api/claims?assignment=UNASSIGNED/MINE/ESCALATED` | Filtros staff, anteriores filtros conservados |
| `GET /api/notifications` | Filas autorizadas y conteo global real |
| `PATCH /api/notifications/{id}/read` | Lectura individual propia |
| `PATCH /api/notifications/read` | Lectura de todas las autorizadas |

Los endpoints existentes de alta, mensajes, cierre y reapertura aceptan clave opcional, y mantienen sus contratos previos. El endpoint genérico de estado delega Escalado al servicio con destino validado, evitando una vía alternativa sin destinatario. Las respuestas staff incorporan asignación e identidad de actor. El DTO cliente sigue filtrando metadatos internos.

## Validación en curso

Se añadirán los resultados efectivos de las suites completas y el inventario final. La primera ejecución durante edición encontró un error de indentación del handler genérico de cierre. Se corrigió y el parseo de todos los archivos Python aprobó. No se considera esa ejecución un diagnóstico funcional del producto terminado.

La primera compilación modificada aprobó con 2611 módulos y 2 min 51 s. La compilación Vite no acredita `tsc`/lint independiente.

Se ajustó una aserción de Fase 1 que contaba todas las notificaciones de un reclamo como si todas fueran publicaciones. Ahora cuenta específicamente CLAIM_PUBLISHED, manteniendo la expectativa de una única publicación concurrente. Los nuevos avisos de entrada/asignación son parte del alcance solicitado. La inyección de fallo de notificación de esa prueba se conserva.

## Límites y recomendaciones para Fase 2D

- Ensayar migración, SQL de ventana, bloqueo y reintentos contra PostgreSQL aislado antes de producción. No se usa Supabase como banco de pruebas.
- No hay entrega externa de correo/push. La campana registra eventos internos y refresco acotado, sin garantía de tiempo real.
- Se muestran 20 avisos priorizando no leídos. El contador y «marcar todas» cubren todo el conjunto autorizado. Un explorador paginado completo puede evaluarse posteriormente.
- Los productores internos heredados sin actor/clave permanecen como compatibilidad. Las rutas autenticadas nuevas suministran identidad y validación. La conciliación global de `usuarios`, `clientes` y `auth_users` sigue en BF-06/17.
- La política MVP de toma propia, destinatario ADMIN de menor ID y lectura global de staff queda explícita para revisión futura. No se inventa una especialización profesional ni un SLA.
- BF-08 y BF-13 completos permanecen pendientes. Fase 2D puede priorizar catálogo administrable y conciliación comercial, manteniendo snapshots y decisiones de elegibilidad separadas.
