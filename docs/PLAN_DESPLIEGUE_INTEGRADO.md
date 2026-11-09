# Plan de despliegue integrado de SmartClaim AI

El candidato local incluye el flujo de cinco roles y la ampliación RAG. La ejecución productiva requiere autorización, una restauración ensayada y aprobación del cierre de exposición confirmado en el [informe de auditoría](AUDITORIA_INTEGRACION_SMARTCLAIM.md).

## Preparación y control de acceso

1. Inventariar consumidores de REST, GraphQL y Realtime, roles, propietarios y permisos por defecto en la configuración real. El manifiesto de seguridad considera public un esquema dedicado a SmartClaim. Confirmar ese alcance antes de revocar acceso al esquema. En este diseño, el navegador usa FastAPI.
2. Obtener una copia autorizada y restaurarla sin salida pública. Restringir acceso al respaldo, aislar credenciales y anonimizar los datos que el ensayo no necesita. Guardar huellas por tabla, secuencias con is_called, grants, políticas, propietario, constraints y versión de extensiones. Inventariar roles y membresías sin contraseñas. Recrear los roles necesarios antes de restaurar en un clúster distinto. Evaluar el alcance del incidente con el responsable del proyecto.
3. Provisionar una credencial nueva exclusivamente para smartclaim_backend tras crear el rol. Usar almacenamiento de secretos y TLS con verificación de certificado. Conectar como ese login y comprobar current_user y session_user. La identidad del servicio debe carecer de propiedad de objetos, membresías, BYPASSRLS, CREATE sobre public y privilegios administrativos. Reservar una cuenta separada para migraciones y mantenimiento documental. Usar APP_ENV=production en staging y producción.
4. Confirmar que la cuenta de migración puede modificar los objetos de public y crear el rol en Supabase. Si el proyecto no necesita Data API para otros consumidores, prever su desactivación por configuración aprobada además de los controles SQL. Validar que cualquier API administrada con otro esquema mantenga su contrato.

## Orden de aplicación en la copia

Usar psql con ON_ERROR_STOP, un search_path conocido y la cuenta de migración. Suspender escritores, cerrar el acceso directo de la Data API durante la ventana y drenar el pool previo. Registrar cada paso completado. Mantener deshabilitados el bootstrap y los proveedores de pago.

| Orden | Archivo o paso | Control |
|---|---|---|
| 1 | database/migrations/phase1_postgres.sql, una transacción | Agrega relaciones y campos de costos. Mantener NULL en vínculos históricos sin evidencia. |
| 2 | database/migrations/phase2b_postgres.sql, una transacción | Amplía CHECK de roles y estados. Crea operadores, repartidores, asignaciones, eventos y auditoría. |
| 3 | database/migrations/phase2c_postgres.sql, transacción propia | Agrega responsables, comandos y destinos de notificación. |
| 4 | database/migrations/integrated_order_integrity.sql | Valida la FK de pedido y titular. Si existen asociaciones cruzadas, aborta y deja el caso para conciliación. Crea índices de pedidos y alcance de comercio. |
| 5 | database/migrations/integrated_sequence_repair.sql | Revisa SERIAL e IDENTITY de tablas no gestionadas por extensiones en public. Solo adelanta secuencias que colisionarían. Usa RESTART transaccional y preserva secuencias adelantadas o tablas vacías. Requiere secuencias ascendentes, sin ciclo, y el pool anterior drenado. |
| 6 | database/migrations/integrated_database_security.sql | Instala el rol y las políticas con RLS forzado. Revoca acceso al esquema para los roles públicos y privilegios directos sobre las tablas de aplicación. Cambia permisos por defecto del ejecutor en public. Validar otros creadores de objetos y permisos heredados por separado. |
| 7 | Incorporación documental revisada | Ejecutar el plan en solo lectura, aprobar solo altas y confirmar huellas de documentos, fragmentos y vectores antiguos. |

En la copia PostgreSQL local, el ensayo de altas se reproduce con python -m scripts.import_documents --postgres-test --append-fragments --dry-run y luego el mismo comando sin --dry-run, con SMARTCLAIM_TEST_PG_DSN explícita. Ejecutar primero scripts.plan_document_migration y revisar su ayuda para el modo de planificación. El lote cancela todas las altas si hay un rechazo. Escribe documentos nuevos, metadatos y fragmentos en una transacción. Una repetición exacta se omite. Un registro previo sin fragmentos se revisa por separado. El importador bloquea destinos remotos. Una ejecución productiva requiere preparar y aprobar el procedimiento del operador sobre el mismo catálogo y la copia autorizada.

Preservar vector(1536) y las filas existentes. Los documentos añadidos quedan disponibles para TF-IDF. Mantener embeddings previos y evaluar su vigencia para el recuperador. Excluir del procedimiento el reindexado global, la regeneración de embeddings y la eliminación de versiones. [Semántica de RESTART en PostgreSQL](https://www.postgresql.org/docs/17/sql-altersequence.html)

## Pruebas, autorización y rollback

- Probar en la copia los cinco roles con el login limitado, accesos cruzados, integridad, flujo RAG y borrador privado. Comprobar que REST rechaza lectura y mutación para anon y para un JWT autenticado de prueba. Revisar GraphQL, secuencias, ausencia de permisos de escritura RAG y las huellas de datos. Verificar CORS y reportes en los orígenes de staging.
- Si falla un paso antes del commit, cancelar la transacción y volver a medir huellas, ACL y secuencias. Si el cambio ya se confirmó, mantener las escrituras suspendidas, restaurar en otra base y cotejar huellas, conteos, secuencias y permisos. Probar la versión anterior contra esa restauración. Mantener cerrada la Data API durante la reversión. Una copia previa puede restaurar los grants vulnerables.
- Si hubo tráfico después del cambio, conservar los eventos y escrituras nuevos para conciliación. Evitar un downgrade de 2B o 2C con roles y eventos en uso. Un rollback de código por sí solo no revierte DDL, ACL, secuencias ni datos. No revertir secuencias hacia abajo en una base que continuó recibiendo escrituras.
- La autorización productiva exige un ensayo con copia real, restauración verificada, comprobación de roles efectivos desde el servicio y comprobaciones HTTP en la configuración administrada. Confirmar respaldo y recuperación, revisar credenciales y sesiones potencialmente afectadas y verificar los SHA de frontend y backend antes de cualquier cambio de tráfico.


## Repetición del ensayo técnico

- En un clúster desechable local con vector y base smartclaim_test, definir SMARTCLAIM_TEST_PG_DSN con host 127.0.0.1 y puerto explícito, y habilitar SMARTCLAIM_TEST_SECURITY_PG=1. Ejecutar python -m pytest. La suite crea y elimina bases de prueba, y crea roles sintéticos globales en ese clúster. Usar un clúster dedicado. Para el navegador, usar tests/serve_offline.py, Vite preview y la configuración playwright.offline.config.ts.
- En una red de laboratorio interna, iniciar PostgreSQL con pgvector y PostgREST contra public. Dar a authenticator la capacidad de asumir anon y authenticated. Usar claves y filas sintéticas. Reproducir los grants anteriores y ejecutar HEAD de límite cero antes y después de las migraciones. Probar PATCH con un identificador ficticio y JWT autenticado solo en ese laboratorio. Revisar todos los endpoints de tabla y comprobar el bloqueo para ambos roles.
- Antes de las migraciones, generar pg_dump de formato personalizado. Restaurarlo con pg_restore en una base separada y comparar huellas de filas documentales, conteos, is_called y permisos. La red interna debe mantenerse durante la restauración.
