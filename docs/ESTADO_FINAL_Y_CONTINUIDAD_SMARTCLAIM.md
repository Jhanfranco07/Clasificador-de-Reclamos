# Estado final y continuidad de SmartClaim AI

Revisión del 13 de noviembre de 2026. La rama integration/smartclaim-cinco-roles-rag contiene la integración funcional de 8287d1d, la ampliación documental de b72583c, la corrección definitiva de registro de b5e24a8 y los controles PostgreSQL posteriores. La rama ya está publicada y el [PR definitivo #2](https://github.com/Jhanfranco07/Clasificador-de-Reclamos/pull/2) está abierto en borrador hacia main. El main remoto sigue en 86691f7 y no se modificó. El PR #1 continúa abierto en borrador desde la rama documental y no se modificó; integrarlo por separado duplicaría parte del recorrido RAG sin incorporar el conjunto de cinco roles y controles de corte.

## Estado por capacidad

| Capacidad | Candidato local | Producción observada |
|---|---|---|
| CLIENT | Catálogo y carrito, cotización del servidor, creación de pedido, historial y reclamos de pedidos propios. | Catálogo público operativo. OpenAPI publica sesión, pedidos y reclamos. Las operaciones con sesión quedaron pendientes de verificación en el despliegue. |
| MERCHANT | Gestión de productos existentes según permiso, recepción y preparación de pedidos del comercio y registro de demoras. | La API publicada carece de endpoints de operaciones y transiciones. No hay cuentas activas de este rol en el catálogo observado. |
| COURIER | Disponibilidad, entrega asignada, recogida y entrega con historial y avisos. | La API publicada carece de asignación y transiciones. No hay cuentas activas de este rol en el catálogo observado. |
| AGENT y ADMIN | Clasificación y bandeja, asignación, escalamiento, revisión y publicación humana, cierre, reapertura, notificaciones. Administración de usuarios, comercios y repartidores con trazabilidad. | OpenAPI publica el flujo previo de reclamos y reportes. La asignación versionada, los portales operativos y la administración de roles del candidato no están publicados. |
| IA y RAG | Clasificador local, prioridad, TF-IDF y plantillas de respuesta, con fuentes vigentes y publicación humana. Importación documental académica y vista previa PDF. pgvector tiene cobertura local con vectores sintéticos. | PostgreSQL conserva el corpus de 18 documentos y sus embeddings. OpenAPI carece de la vista previa PDF. El uso real de un LLM y la calidad de los embeddings productivos siguen sin verificarse. |
| PostgreSQL y seguridad | Migraciones, RLS/revocaciones y login limitado preparados y ensayados. El arranque productivo del candidato exige ese login. | Render mantiene el parche privado temporal sobre 86691f7 con AutoDeploy desactivado. FastAPI y PostgreSQL están operativos; la Data API permanece desactivada. El esquema productivo aún no recibió las migraciones integradas. |

El checkout registra el método de pago. El cobro electrónico y la recuperación de contraseña por correo siguen siendo funciones fuera del recorrido validado. La gestión de comercio opera sobre productos existentes. La generación mediante proveedor externo es opcional y se mantiene separada del flujo local. Las referencias de RAG documentan el origen de la sugerencia y un agente decide si publica.

Se conservaron los contratos de los cinco roles y de RAG en la misma rama. La duplicación relevante que queda está en los recorridos documentales. El mantenimiento local puede reconstruir el índice y eliminar fragmentos obsoletos. El corte alojado requiere la ruta aditiva descrita abajo, que preserva IDs y embeddings. Las pantallas administrativas del alojamiento limitan las escrituras documentales a un procedimiento de mantenimiento controlado.

## Bloqueantes comprobados y cambios de esta entrega

- **Fragmentos históricos de RAG.** En un conteo de solo lectura, solo 2 de los 24 fragmentos existentes coincidían con el contenido y orden canónicos del recuperador. Para los 18 documentos activos faltaban 32 de los 34 fragmentos esperados. La ruta de alta del catálogo académico cubría los documentos nuevos. Se añadió al importador existente el modo --backfill-fragments con --dry-run. Añade únicamente fragmentos canónicos faltantes, en una transacción, y al repetirlo omite lo ya presente. Las filas, IDs y embeddings anteriores se conservan. Los fragmentos nuevos sirven a TF-IDF. El comando de escritura permanece restringido a copias locales de ensayo. Con SMARTCLAIM_TEST_PG_DSN configurada para loopback, el plan se obtiene con python -m scripts.import_documents --postgres-test --backfill-fragments --dry-run.
- **Pedidos y reclamos históricos.** De 12 pedidos, 11 permanecen abiertos, 10 en PREPARING y uno en DELAYED. Los 11 tienen un único candidato por nombre de comercio. La coincidencia orienta la revisión, y la vinculación exige confirmación operativa. De 16 reclamos, 14 tienen un candidato con el mismo código de pedido y titular. Conservar NULL en los casos sin evidencia. Las migraciones aditivas dejan los vínculos históricos pendientes y la aplicación evita inferir estados o titularidad.
- **Corte del candidato.** La API publicada tiene 27 rutas y aún no ejecuta los contratos operativos integrados. El despliegue exige ensayar el esquema y la conexión limitada sobre una copia autorizada, confirmar la asignación de roles operativos y usar un par frontend y backend de la misma revisión.

### Validación del recorrido

- La regresión PostgreSQL de datos heredados aprobó el plan de solo lectura, la reparación idempotente, la recuperación de la FAQ de faltantes y la igualdad de filas anteriores, incluidos los embeddings sintéticos. La comprobación incluye importación y repetición del lote académico.
- Se ejecutaron tres recorridos de Chromium contra el frontend local y FastAPI con APP_ENV=production y smartclaim_backend en PostgreSQL sintético. Pasaron compra, comercio, asignación, recogida, entrega y publicación por agente. También pasaron asignación y escalamiento del reclamo, avisos, evidencia RAG y privacidad del borrador antes de publicar. La protección de red registró cero intentos externos en la ejecución válida. El arranque inicial del arnés rechazó la conexión local por comparar cadenas DSN en vez de sus parámetros. Se corrigió el arnés temporal y se repitió la prueba sin relajar el destino permitido.
- En esa copia se añadieron los 32 fragmentos faltantes y los 42 documentos académicos. El resultado fue de 60 documentos y 92 fragmentos físicos, con cero faltantes canónicos. Las filas heredadas se mantienen disponibles para trazabilidad. El recorrido usó TF-IDF y respuestas locales, sin servicios de pago.

## Cierre de la intervención de seguridad

**Mitigación inmediata verificada, con riesgos residuales documentados.** Las 25 sondas REST dejaron de responder con éxito tras apagar la Data API. PostgreSQL y FastAPI siguieron operativos. El parche privado temporal del registro está Live en Render sobre 86691f7 y AutoDeploy permanece desactivado. La Data API sigue apagada. Los permisos SQL amplios, la falta de RLS en las tablas actuales y vector en public siguen siendo deuda priorizada; la corrección de permisos requiere el corte ya preparado. [Evidencia de contención](CONTENCION_SUPABASE_Y_CORTE_RENDER.md). El informe postcierre se conserva localmente y no forma parte de esta publicación.

## Candidato de publicación

- **Corrección de registro.** El commit b5e24a8 reserva correos asociados a cuentas, clientes o notificaciones existentes. El alta normal crea cuenta y cliente en una sola transacción. La regresión SQLite y PostgreSQL comprobó que un correo histórico obtiene 409, no crea una cuenta y no modifica el titular del pedido. El candidato definitivo no depende del lanzador temporal de Render.
- **Publicación completada.** La contención temporal de FastAPI ya fue verificada. La rama integrada está publicada y el PR #2 se abrió separado y en borrador hacia main. El PR documental #1 permanece intacto y no debe integrarse además del PR definitivo sin revisar duplicaciones.
- **Despliegues automáticos.** La configuración de Vercel desactiva los despliegues por Git solo para la rama de integración. El título y los commits documentales usan [skip render], Render conserva AutoDeploy apagado y GitHub no registró despliegues para la rama tras la publicación. [Vercel](https://vercel.com/docs/project-configuration/git-configuration) · [Render](https://render.com/docs/service-previews)
- **Resultado del ensayo con datos reales.** El 13 de noviembre se generó una copia lógica autorizada y cifrada del esquema `public` productivo. Se restauró en PostgreSQL 17/pgvector efímero y se aplicaron dos veces Fase 1, 2B, 2C, integridad, secuencias y seguridad. La copia de origen permaneció separada e inmutable; la base migrada y una restauración de rollback reprodujeron las huellas esperadas. Producción no se modificó.

La revisión del 13 de noviembre aprobó 194 pruebas Pytest con SQLite y PostgreSQL 16/pgvector 0.8.6 locales, incluidas las dos regresiones de registro, las migraciones, RLS/GRANT, secuencias, conservación documental y recorridos de los cinco roles. TypeScript 5.8.3 aprobó sin errores y Vite compiló 2.611 módulos. Chromium aprobó 64 de 64 pruebas sobre FastAPI y SQLite desechables. Una primera carga fría excedió el tiempo de espera; el caso aislado pasó al repetirlo y la corrida completa posterior aprobó. La suite registró un aviso de deprecación de Starlette/httpx y cero intentos externos inesperados. No hubo llamadas de pago ni acceso a Supabase durante estas pruebas.

Las migraciones quedaron validadas sobre la copia real de staging, no aplicadas en producción. Se conservaron 3 cuentas, 3 clientes, 12 pedidos, 16 reclamos y los 24 embeddings históricos. Los 18 documentos y 24 fragmentos originales permanecieron iguales; el proceso aditivo produjo 60 documentos y 98 fragmentos. Los 11 pedidos abiertos tienen un único candidato por nombre de comercio, pero no se asignó ninguno automáticamente. Catorce reclamos tienen un único pedido candidato y dos requieren conciliación manual. La repetición no añadió duplicados.

### Backup y validación reproducibles

El ejecutor reutiliza Docker y la imagen local de Supabase PostgreSQL 17.11. Lee `DATABASE_URL` desde un archivo privado, pasa la contraseña solo por el entorno del proceso, usa `pg_dump` 17 sobre `public`, valida el catálogo con `pg_restore`, cifra por bloques con Windows DPAPI y restringe la ACL al usuario actual y `SYSTEM`. No usa los archivos del parche de Render.

~~~powershell
# Comando 1: backup productivo de solo lectura, cifrado y verificado.
& .venv\Scripts\python.exe -B -m scripts.smartclaim_backup backup --source-env-file "RUTA_PRIVADA\.env"

# Comando 2: restauración, migraciones, pruebas focalizadas y rollback efímeros.
& .venv\Scripts\python.exe -B -m scripts.smartclaim_backup validate
~~~

El respaldo vigente está fuera de Git en `%LOCALAPPDATA%\SmartClaim-Privado\backups\smartclaim-20261113T211244Z`. Su SHA-256 cifrado es `fb94c361ba77e0d725fd47936d5300e674ce9ceb16aa73c2d41aaa91c2548906`; el manifest y el informe final no contienen credenciales ni filas. DPAPI lo vincula al usuario y equipo Windows actuales. Storage binario, configuración Auth/SMTP/OAuth, Edge Functions, claves, secretos JWT, Realtime y contraseñas de roles globales no pertenecen a este dump de aplicación y deben respaldarse por procedimientos separados si se incorporan al alcance.

La restauración final aprobó cuatro pruebas PostgreSQL focalizadas, cero restricciones inválidas, cero tablas de aplicación sin RLS forzado y cero pares rol público/tabla con privilegios. El login `smartclaim_backend` quedó limitado. El contenedor, la red, la contraseña sintética y el dump descifrado se eliminaron al terminar.

### Corte definitivo y rollback

1. Con copia autorizada restaurada en staging, ensayar las migraciones en el orden documentado, comprobar conteos y huellas de usuarios, pedidos, reclamos, documentos, fragmentos y embeddings, y confirmar manualmente los 11 pedidos abiertos. Ensayar rollback antes de solicitar producción.
2. En una ventana autorizada, mantener la Data API apagada y AutoDeploy desactivado. Tomar el respaldo final, aplicar las migraciones con el operador de base, instalar el login PostgreSQL limitado y ejecutar las sondas de permisos y relaciones antes de habilitar escrituras.
3. Desplegar el backend desde el SHA definitivo, restaurar el comando normal `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT` y comprobar salud, registro legítimo, rechazo del correo reservado, login y acceso horizontal. Solo entonces desplegar el frontend del mismo SHA y repetir los cinco recorridos.
4. Cuando backend y frontend hayan pasado, retirar de Render el lanzador y los archivos privados temporales, verificar que el servicio ya no los referencia y reactivar AutoDeploy. Mantener la Data API apagada.
5. Si falla antes de confirmar las migraciones, revertir la transacción. Si falla después, suspender escrituras y restaurar el respaldo en una base separada para conciliación. El rollback de aplicación debe usar una revisión que contenga b5e24a8 o volver al modo de contingencia que suspende solo el registro; nunca redeplegar 86691f7 sin su parche temporal. [Plan SQL y rollback](PLAN_DESPLIEGUE_INTEGRADO.md)

## Acciones concretas y criterio de término

1. Confirmar manualmente los vínculos de los 11 pedidos abiertos y revisar los dos reclamos sin candidato único. Mantener `NULL` donde la evidencia no baste; el ensayo no inventó relaciones.
2. Preparar una contraseña productiva nueva para `smartclaim_backend` mediante el gestor de secretos del despliegue. La migración crea el rol sin contraseña deliberadamente.
3. Presentar el SHA del candidato, respaldo, resultados y ventana. Con autorización explícita, aplicar el corte de base, desplegar backend y frontend de la misma revisión y retirar el parche temporal solo tras repetir registro, login, acceso horizontal y cinco roles.
4. Mantener la Data API apagada. Conservar el respaldo DPAPI sin alterarlo y crear una segunda copia cifrada portable antes del corte si se requiere recuperación en otro equipo.

SmartClaim se considera terminado para este alcance cuando los cinco actores pueden operar el recorrido en la versión publicada, el historial y la autorización son verificables, las sugerencias citan evidencia vigente y quedan privadas hasta aprobación, y el cambio es reversible con los datos preservados. El proveedor LLM de pago, el cobro electrónico y el envío de correos requieren una decisión de alcance independiente.
