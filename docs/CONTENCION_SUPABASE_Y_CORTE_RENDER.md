# Contención de Supabase y verificación del corte de Render

## Riesgo y dependencias comprobadas

El 9 de noviembre de 2026 seguían existiendo 25 tablas en public con RLS desactivado y SELECT efectivo para anon y authenticated. La auditoría anterior confirmó INSERT, UPDATE y DELETE efectivos y respuestas HTTP 200 a HEAD anónimo en las 25 tablas. Esto permite alcanzar por REST relaciones con datos de clientes, pedidos, reclamos, mensajes privados y el campo password_hash. La verificación usó metadatos y consultas sin filas. La exposición demostrada no acredita accesos ni alteraciones de terceros. [Auditoría integrada](AUDITORIA_INTEGRACION_SMARTCLAIM.md)

| Dependencia | Evidencia y efecto esperado |
|---|---|
| Frontend publicado | Se recorrieron los 51 módulos JavaScript alcanzables desde el HTML público de Vercel. Apuntan a SmartClaim API en Render. En los módulos y el código revisado no se encontraron clientes ni rutas directas de Supabase. VITE_API_URL apunta a FastAPI. |
| FastAPI y PostgreSQL | Render devolvió HTTP 200 y PostgreSQL activo en /health, y HTTP 401 para GET /api/orders sin sesión. OpenAPI del servicio publicado aún carece de la transición operativa de pedidos. El backend usa psycopg y DATABASE_URL. La aplicación emite su propio token y consulta su tabla de usuarios. pgvector funciona por SQL. |
| Supabase Auth, Storage, Realtime, Functions y GraphQL | Cero cuentas de Supabase Auth, cero buckets y objetos, cero tablas en supabase_realtime y ninguna Edge Function registrada. La extensión pg_graphql está ausente. El repositorio y el frontend publicado carecen de integraciones directas con esos servicios. |
| Consumidores externos | Inventariar integraciones fuera del repositorio, automatizaciones, clientes HTTP y el alcance de esquemas en el panel. El muestreo de logs y el análisis estático solo cubren la ventana y los artefactos observados. |
| Render administrado | El conector no tenía workspace seleccionado. La comprobación pública no identifica el usuario PostgreSQL ni las claves efectivas del servicio. smartclaim_backend todavía no existe en Supabase. Antes del corte, el operador debe confirmar workspace, servicio, revisión activa y origen de las claves, sin revelar valores. |

## Ventana de contención autorizada

**Opción preferida.** Desactivar Enable Data API en [Integrations → Data API → Settings](https://supabase.com/dashboard/project/fydoupwykkshtpongcih/integrations/data_api/settings), sin cambiar credenciales, RLS ni servicios de Render. Esto cierra el tráfico de la Data API en el proyecto. La conexión SQL que usa SmartClaim sigue un canal distinto. Puede interrumpir cualquier consumidor externo que dependa de REST o RPC. La evidencia disponible permite priorizar este control en una ventana breve tras confirmar ese inventario con el operador. [Desactivar la Data API](https://supabase.com/docs/guides/api/securing-your-api#disable-the-data-api)

**Si existe un consumidor legítimo.** Mantener el servicio Data API habilitado y retirar public de Exposed schemas, conservando únicamente los esquemas que el consumidor necesita. Si depende de una relación de public, trasladar primero su contrato a un esquema dedicado con permisos explícitos y políticas validadas. Como alternativa SQL transitoria, ensayar la revocación de USAGE sobre public a PUBLIC, anon y authenticated, verificar permisos efectivos y preservar USAGE explícito solo para las identidades necesarias. Este control puede afectar a consumidores SQL que heredaban USAGE. Si se necesitan revocaciones por objeto, revisar grants de tabla, columna, secuencia y funciones por separado. Cambiar el ajuste de exposición automática de tablas nuevas no retira grants de tablas existentes. [Esquemas y privilegios en Supabase](https://supabase.com/docs/guides/api/securing-your-api)

1. Obtener autorización explícita, registrar hora UTC, operador y opción. Capturar el estado del ajuste, esquemas expuestos y una línea base de HTTP. Confirmar consumidores externos con el propietario del proyecto. Registrar /health, una lectura de catálogo sin imprimir el cuerpo y el rechazo de /api/orders sin token. Si existe una cuenta sintética autorizada, comprobar login y lectura del pedido sintético sin registrar el token.
2. Aplicar una sola opción. Para la preferida, abrir el proyecto correcto, ir a Integrations → Data API → Settings, apagar Enable Data API y guardar. Mantener el backend y su configuración actuales. Registrar hora y alcance del cambio.
3. Desde un origen controlado, repetir HEAD con limit=0 para las 25 rutas del informe, con la clave pública en memoria y sin imprimir headers ni cuerpos. Requerir una denegación confirmada por el gateway en todas las rutas. Un 2xx, un 5xx o un timeout requieren investigar antes de dar el cierre por confirmado. Si hay un JWT sintético autorizado, repetir con ese token. Cuando no exista, usar PostgREST aislado para comprobar el rol y dejar explícita la falta de prueba HTTP autenticada en producción. Reservar todas las pruebas de mutación para staging.
4. Repetir los checks FastAPI desde el dominio de frontend y fuera de él. Verificar HTTP 200 en /health con database=ok y databaseProvider=postgres, catálogo accesible y 401 en el recurso protegido. Comprobar login, pedidos y reclamos con la cuenta sintética si está autorizada. Correlacionar errores REST y Render con la hora registrada.
5. Ante una regresión, identificar la dependencia afectada. Si falla FastAPI, revisar primero salud, logs y conexión SQL de Render. Mantener el cierre de la Data API mientras se recupera el backend. Si falla un consumidor HTTP legítimo, recuperar su acceso mediante un esquema dedicado probado. Rehabilitar la Data API requiere autorización y verificación previa de que public queda excluido o efectivamente denegado. Conservar la evidencia y repetir las comprobaciones de ambos servicios.

La contención HTTP deja los grants actuales en la base. Mantenerla activa hasta validar la migración de privilegios. Revisar con el responsable del incidente si corresponde proteger cuentas y sesiones por separado. Rotar claves por sí solo deja disponible el acceso anónimo cuando persisten los permisos públicos.

## Investigación de accesos

- Logs Explorer de Supabase, gateway y PostgREST. Buscar método, ruta sin query string, estado, identificador de solicitud y hora UTC. Revisar GET o HEAD 2xx y escrituras 2xx sobre las tablas expuestas, separando las sondas conocidas. Correlacionar request ID cuando exista. Guardar evidencias con acceso restringido. Evitar exportar IP, URL completa, JWT, headers, cuerpos o datos personales.
- En la consulta agregada de las últimas 24 h se observaron 25 HEAD REST 200, un GET REST 406 y un POST GraphQL 200. Coinciden con las sondas documentadas, incluida la introspección que indicó que GraphQL estaba deshabilitado. No se observó escritura REST en esa ventana. Esto no cubre periodos anteriores, retención insuficiente ni exclusiones.
- Se encontraron fuentes de PostgreSQL, PostgREST, PgBouncer y Supavisor. PostgreSQL reportó log_statement=ddl, log_connections=off y pgAudit ausente. Usar esas fuentes para errores, DDL y conexiones cuando haya eventos, y los logs de Render para correlacionar el tráfico por FastAPI. La configuración observada no proporciona un historial fiable de todos los SELECT. Confirmar retención y exportaciones antes de que expiren. [Logs Explorer y límites](https://supabase.com/docs/guides/observability/logs)

Consulta segura de ejemplo para la interfaz unificada de logs. Seleccionar ventanas UTC de hasta 24 h y registrar cuál se consultó.

~~~sql
SELECT log_attributes['request.method'] AS method,
       log_attributes['response.status_code'] AS status, count(*) AS events
FROM logs
WHERE source = 'edge_logs'
  AND startsWith(log_attributes['request.path'], '/rest/v1/')
GROUP BY method, status
ORDER BY method, status
~~~

## Validación de Render para un corte posterior

La contención HTTP no requiere un cambio de entorno. Para el corte posterior, revisar en Render Environment las claves del servicio y de grupos vinculados. El Blueprint local fija CORS y previews. Los valores secretos y la procedencia efectiva se validan en el panel por un operador, sin copiarlos al informe.

| Clave | Acción en el corte |
|---|---|
| DATABASE_URL | Sustituir por la conexión de smartclaim_backend tras aplicar la migración y provisionar su secreto. Usar TLS con sslmode=verify-full, CA aprobada y nombre del servidor verificado. Guardar la credencial anterior en el gestor seguro para rollback limitado. |
| APP_ENV, DB_PROVIDER | Confirmar production y postgres. El candidato verifica identidad en producción y rechaza el fallback SQLite. |
| AUTH_SECRET | Preservar la clave para mantener sesiones durante el corte, salvo rotación aprobada por el plan de incidente. |
| CORS_ORIGINS, FRONTEND_URL, ALLOW_VERCEL_PREVIEWS | Confirmar orígenes y política vigente. Conservarlos durante el corte. |
| SMARTCLAIM_BOOTSTRAP_DEMO, OPENAI_API_KEY, ENABLE_PGVECTOR_RAG | Mantener bootstrap deshabilitado. En staging usar recuperación local y deshabilitar llamadas pagadas. Conservar la configuración aprobada del proveedor en producción hasta su revisión. |
| VITE_API_URL | Confirmar en Vercel que apunta al servicio FastAPI correcto. Cambiarla solo si cambia ese destino. |

Desde staging, comprobar conectividad directa si existe ruta IPv6 o usar Session pooler IPv4. Usar el usuario del pool con el formato del proyecto que muestra Connect y confirmar que la sesión PostgreSQL queda como smartclaim_backend. La ruta de transacciones requiere validar por separado la compatibilidad con prepared statements de psycopg. Confirmar TLS en el cliente y el modo elegido. El panel de Render distingue guardar sin desplegar de aplicar valores mediante un despliegue. Programar ambos únicamente en el corte autorizado. [Conexión a Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres) · [Variables de Render](https://render.com/docs/configure-environment-variables)

1. Después de aplicar el manifiesto integrated_database_security.sql en staging, ejecutar database/verification/render_login.sql como smartclaim_backend con psql -X -v ON_ERROR_STOP=1. Conectar mediante un perfil libpq de staging y resolver el secreto fuera de la terminal. La salida esperada es verified_role=smartclaim_backend.
2. Verificar permisos en el manifiesto. El login requiere USAGE del esquema, SELECT de datos operativos y RAG, las escrituras por tabla que necesita FastAPI y USAGE de secuencias para insertar. El login carece de propiedad de relaciones, membresías, BYPASSRLS, CREATE y permisos de modificación sobre el corpus. La sonda comprueba identidad, permisos clave y vector(1536). Ejecutar las pruebas con los cinco roles para cubrir las operaciones DML y el aislamiento que la sonda de solo lectura no ejecuta.
3. Antes del cambio definitivo, confirmar health del candidato, consultas autorizadas de los cinco roles, denegaciones cruzadas y REST cerrado. Si falla el candidato, volver al artefacto y la configuración anteriores autorizados únicamente si son compatibles con el esquema vigente. Mantener cerrada la Data API. Evitar volver al login propietario como solución permanente.

## Copia real, validación de migración y recuperación

La copia real todavía no está disponible. El ensayo sintético anterior sigue siendo la evidencia ejecutada sobre el flujo completo. El procedimiento siguiente requiere autorización y un responsable de datos. [Respaldos y límites de descarga en Supabase](https://supabase.com/docs/guides/platform/backups)

1. En Supabase Database → Backups, comprobar fecha, alcance y disponibilidad de un respaldo lógico. Si solo hay un backup físico o PITR, usar la opción autorizada de restaurar en otro proyecto o pedir una exportación lógica del esquema de aplicación mediante una conexión aprobada. No restaurar sobre el origen. Usar PostgreSQL y pgvector de versiones compatibles, un volumen cifrado fuera del repositorio y un perfil libpq con credenciales protegidas. Con pg_dump, usar --format=custom --schema=public --no-owner --no-acl y una salida protegida. Inventariar ACL, políticas, miembros, owners y secuencias por separado, sin passwords. Conservar el original inmutable y registrar la huella del archivo.
2. Restaurar en una base vacía de PostgreSQL aislado, sin puertos ni egreso público. Preparar la extensión vector y las definiciones de rol requeridas antes de pg_restore --exit-on-error --single-transaction --no-owner --no-acl. El dueño de migración local debe controlar los objetos restaurados. Recrear la ACL inicial revisada con roles inertes o sintéticos si se quiere verificar el cierre desde un estado equivalente. Mantener la copia íntegra bajo custodia. En una copia de prueba separada, anonimizar campos innecesarios y reemplazar credenciales activas antes de habilitar FastAPI o PostgREST.
3. Congelar escritores y capturar la línea base en la copia de prueba después de anonimizar. Ejecutar psql -X -qAt -v ON_ERROR_STOP=1 -f database/verification/migration_snapshot.sql. La salida contiene conteo, máximo ID y SHA-256 por tabla, sin filas. Guardar ese manifiesto como evidencia restringida. Guardar también los conteos de discrepancias de titularidad, la lista de columnas y los estados de claves foráneas e índices.
4. Aplicar el orden del plan integrado, con psql -X -v ON_ERROR_STOP=1. Usar --single-transaction para phase1_postgres.sql y phase2b_postgres.sql. Los scripts que contienen BEGIN y COMMIT se ejecutan sin esa opción. Revisar nombres y definiciones de FK con pg_get_constraintdef y exigir convalidated. Revisar pg_index.indisvalid e indisready. Confirmar que el cruce de reclamos no nulos con pedidos por id_pedido e id_cliente tenga cero discrepancias. Para las secuencias vinculadas a IDs, consultar pg_get_serial_sequence y comparar last_value e is_called con max(id) sin consumir nextval. Con incremento uno, el próximo valor es last_value más uno si is_called es true. Validar que supere el máximo y que una secuencia adelantada conserve su posición.
5. Correr de nuevo migration_snapshot.sql con los cinco límites del manifiesto, mediante -v orders_max, -v claims_max, -v documents_max, -v fragments_max y -v embeddings_max con sus respectivos valores. Exigir igualdad para las filas preexistentes y revisar por separado los campos aditivos. Comparar también los totales sin límites. Antes de importar, los cinco totales deben coincidir. Después de importar, solo pueden aumentar documentos y fragmentos conforme al lote autorizado. Requerir que el total de embeddings permanezca igual.
6. Probar permisos efectivos de anon, authenticated y service_role, incluyendo grants de columnas, secuencias y alcance del esquema. Confirmar RLS forzado y la ausencia de privilegios públicos en las relaciones de aplicación. Repetir denegaciones HTTP y la sonda de Render en staging.
7. Ante un fallo de migración, hacer rollback de la transacción abierta y registrar cuál fue la última fase confirmada. Para una fase confirmada, mantener detenidos escritores y Data API, restaurar el respaldo en otra base, recrear los roles y cotejar huellas, conteos, ACL, políticas y secuencias. Probar el artefacto anterior antes de redirigir tráfico. Si hubo escrituras desde el respaldo, preservar y conciliar ese delta antes del retorno. Una restauración que reponga grants antiguos debe permanecer aislada. [Plan integrado y orden SQL](PLAN_DESPLIEGUE_INTEGRADO.md)


Ejemplos para el operador autorizado. Los perfiles libpq se definen fuera del repositorio y las rutas apuntan a almacenamiento protegido. Revisar el destino antes de ejecutar cada comando.

~~~text
pg_dump "service=smartclaim_export" --format=custom --schema=public --no-owner --no-acl --file=<archivo_protegido>
pg_restore --dbname="service=smartclaim_staging_owner" --exit-on-error --single-transaction --no-owner --no-acl <archivo_protegido>
psql "service=smartclaim_staging_owner" -X -qAt -v ON_ERROR_STOP=1 -f database/verification/migration_snapshot.sql
psql "service=smartclaim_staging_owner" -X -qAt -v ON_ERROR_STOP=1 -v orders_max=<id> -v claims_max=<id> -v documents_max=<id> -v fragments_max=<id> -v embeddings_max=<id> -f database/verification/migration_snapshot.sql
psql "service=smartclaim_staging_backend" -X -v ON_ERROR_STOP=1 -f database/verification/render_login.sql
~~~

### Evidencia de preparación

Se comprobaron las dos sondas nuevas en una base sintética en loopback. La sonda aceptó el login limitado y rechazó al propietario de la base. Las cinco huellas coincidieron antes y después de las fases de esquema ensayadas. La comprobación pública de Render usó health, OpenAPI, catálogo y una ruta protegida sin sesión. El catálogo devolvió 200. El primer health agotó el tiempo de espera, y la repetición devolvió 200. No se repitieron las suites de la integración ni se probó el login futuro contra el servicio alojado.
