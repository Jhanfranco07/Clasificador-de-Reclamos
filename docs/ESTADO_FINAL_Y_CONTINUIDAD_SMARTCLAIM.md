# Estado final y continuidad de SmartClaim AI

Revisión del 9 de noviembre de 2026. La rama local integration/smartclaim-cinco-roles-rag parte de e7b72b5 y contiene la integración funcional de 8287d1d y los controles PostgreSQL posteriores. El main remoto sigue en 86691f7. El candidato base e7b72b5 contiene todo main y estaba 18 commits por delante antes de las correcciones de esta entrega. La rama de integración no está publicada. El PR #1 continúa abierto en borrador desde la rama documental a117e4c. El respaldo de cinco roles 92f64b6 permanece publicado. Integrar solo el PR #1 dejaría fuera el flujo de cinco roles y los controles de corte.

## Estado por capacidad

| Capacidad | Candidato local | Producción observada |
|---|---|---|
| CLIENT | Catálogo y carrito, cotización del servidor, creación de pedido, historial y reclamos de pedidos propios. | Catálogo público operativo. OpenAPI publica sesión, pedidos y reclamos. Las operaciones con sesión quedaron pendientes de verificación en el despliegue. |
| MERCHANT | Gestión de productos existentes según permiso, recepción y preparación de pedidos del comercio y registro de demoras. | La API publicada carece de endpoints de operaciones y transiciones. No hay cuentas activas de este rol en el catálogo observado. |
| COURIER | Disponibilidad, entrega asignada, recogida y entrega con historial y avisos. | La API publicada carece de asignación y transiciones. No hay cuentas activas de este rol en el catálogo observado. |
| AGENT y ADMIN | Clasificación y bandeja, asignación, escalamiento, revisión y publicación humana, cierre, reapertura, notificaciones. Administración de usuarios, comercios y repartidores con trazabilidad. | OpenAPI publica el flujo previo de reclamos y reportes. La asignación versionada, los portales operativos y la administración de roles del candidato no están publicados. |
| IA y RAG | Clasificador local, prioridad, TF-IDF y plantillas de respuesta, con fuentes vigentes y publicación humana. Importación documental académica y vista previa PDF. pgvector tiene cobertura local con vectores sintéticos. | PostgreSQL conserva el corpus de 18 documentos y sus embeddings. OpenAPI carece de la vista previa PDF. El uso real de un LLM y la calidad de los embeddings productivos siguen sin verificarse. |
| PostgreSQL y seguridad | Migraciones y login limitado preparados y ensayados. El arranque productivo del candidato exige ese login. | Render respondió 200 en salud y catálogo, con PostgreSQL operativo y seis comercios. El esquema carece de las cuatro columnas operativas comprobadas. El login limitado no estaba instalado en la auditoría vigente. |

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

**Mitigación inmediata verificada, con riesgos residuales documentados.** Las 25 sondas REST dejaron de responder con éxito tras apagar la Data API. PostgreSQL y FastAPI siguieron operativos. Se conservan como evidencia las 126 pruebas Pytest, 64 Playwright y el cierre de sesión adicional de la intervención. La Data API permanece apagada. Los permisos SQL amplios, la falta de RLS en las tablas actuales y vector en public siguen siendo deuda priorizada. La configuración HTTP contiene la exposición observada. La corrección de permisos requiere el corte ya preparado. [Evidencia de contención](CONTENCION_SUPABASE_Y_CORTE_RENDER.md). El informe postcierre se conserva en el worktree local.

## Candidato de publicación

- **Corrección de registro.** En un ensayo sintético, el alta pública devolvía 201 para un correo de cliente histórico. La corrección reserva correos asociados a cuentas, clientes o notificaciones existentes. El alta normal crea cuenta y cliente en una transacción. La regresión comprueba que no se crea una cuenta ni se modifica el titular del pedido cuando el correo está reservado.
- **Publicación retenida.** GitHub confirma que el repositorio es público. El registro de la versión anterior sigue publicado y una comprobación productiva de solo lectura encontró registros históricos sin cuenta asociada. La corrección y las pruebas quedan locales hasta contener el acceso por FastAPI. El PR final está preparado para la rama de integración hacia main y deberá abrirse en borrador. El PR documental #1 permanece intacto.
- **Despliegues automáticos.** La configuración de Vercel desactiva los despliegues por Git solo para la rama de integración. Al abrir el PR, incluir [skip render] en el título para omitir previews de Render y usar [skip render] en el commit de punta para cubrir un push conectado. Verificar que no aparezca un despliegue antes de cambiar el estado del PR. [Vercel](https://vercel.com/docs/project-configuration/git-configuration) · [Render](https://render.com/docs/service-previews)
- **Resultado del ensayo con datos reales.** El propietario confirmó que aún no dispone de una copia autorizada. Los ensayos de Fase 1, 2B, 2C, integridad, secuencias y seguridad son sintéticos. En el ensayo previo se aplicaron dos veces, se comprobó el login limitado y se restauró el respaldo sintético en otra base. El recorrido local con los cinco roles y PostgreSQL limitado no acredita la compatibilidad de los datos de producción.

La revisión final aprobó 194 pruebas Pytest con SQLite y PostgreSQL/pgvector locales, 64 pruebas Chromium, TypeScript y el build de Vite. La regresión de alta falló antes de la corrección con HTTP 201 en vez de 409. Pasó en SQLite y PostgreSQL tras el cambio. La suite final registró un aviso de deprecación de Starlette/httpx y cero intentos externos inesperados. La importación aditiva, RAG local por categoría, borrador privado, permisos cruzados y restauración se comprobaron con datos sintéticos. Render con el login limitado, la restauración real y el rollout aún requieren autorización y evidencia.

### Obtener la copia autorizada

1. En [Backups del proyecto](https://supabase.com/dashboard/project/fydoupwykkshtpongcih/database/backups), comprobar si hay un respaldo lógico descargable y registrar fecha y alcance. Si solo hay respaldo físico o PITR, reservarlo para el procedimiento autorizado del proveedor o generar una exportación lógica. Evitar el botón de restauración del proyecto de origen. [Respaldos de Supabase](https://supabase.com/docs/guides/platform/backups)
2. Para generar una exportación lógica, abrir **Connect** en el proyecto, seleccionar la conexión directa si la red lo permite o **Session pooler** si se necesita IPv4, y copiar host, puerto, usuario y base. Usar pg_dump de PostgreSQL 17 o una versión compatible. Descargar el certificado CA desde la configuración SSL de la base y usar TLS con verificación completa. Los ajustes del ejemplo son del proceso local. pg_dump pide la contraseña en la terminal y escribe el archivo fuera del repositorio. [Conexión a PostgreSQL](https://supabase.com/docs/guides/database/connecting-to-postgres)

~~~powershell
$env:PGSSLMODE = 'verify-full'
$env:PGSSLROOTCERT = 'RUTA_LOCAL_AL_CERTIFICADO_CA'
pg_dump -h HOST -p PUERTO -U USUARIO -d BASE -W --format=custom --schema=public --no-owner --no-acl --file="RUTA_CIFRADA_FUERA_DEL_REPO/smartclaim.dump"
pg_restore --list "RUTA_CIFRADA_FUERA_DEL_REPO/smartclaim.dump"
Get-FileHash -Algorithm SHA256 -LiteralPath "RUTA_CIFRADA_FUERA_DEL_REPO/smartclaim.dump"
~~~

3. Guardar el archivo en un volumen cifrado con acceso limitado al propietario y al operador autorizado, fuera de todos los worktrees y de carpetas sincronizadas. Registrar hora y SHA-256. Conservar aparte un inventario de propietarios, ACL y roles sin contraseñas. Confirmar la ruta protegida y autorizar la restauración aislada. Mantener el original inmutable y usar una copia sanitizada para las pruebas con usuarios.

### Publicación y rollback

Antes de publicar, autorizar y verificar la mitigación de registro en la versión activa por un canal privado. Después, publicar la rama y abrir el PR en borrador con alcance, pruebas, cambios SQL, verificación del login y recuperación. Mantener la Data API apagada. Si falla el corte antes de confirmar una transacción, revertir esa transacción. Si falla después, suspender escrituras y restaurar el respaldo en otra base aislada. Comparar huellas, secuencias y permisos, conservar las escrituras posteriores para conciliación y comprobar la versión anterior antes de redirigir tráfico. [Plan SQL y rollback](PLAN_DESPLIEGUE_INTEGRADO.md)

## Acciones concretas y criterio de término

1. Obtener una copia autorizada de PostgreSQL y restaurarla aislada. Confirmar y registrar el vínculo de los 11 pedidos abiertos, revisar el estado DELAYED y validar los candidatos de reclamos por código y titular. Mantener los vínculos que no se puedan demostrar sin asignar.
2. Ensayar las migraciones y el login limitado en esa copia. Ejecutar primero el plan de fragmentos faltantes y comprobar sus altas sin pérdida. Validar la importación de los 42 documentos académicos y preparar la ejecución del lote aditivo por el operador de base para el entorno alojado. Reutilizar las sondas de identidad y huellas ya preparadas. [Orden y rollback](PLAN_DESPLIEGUE_INTEGRADO.md)
3. Con cuentas de prueba autorizadas, verificar el mismo flujo del navegador en staging. Exigir compra, preparación, asignación, entrega, reclamo del titular, evidencia RAG, revisión humana, publicación y notificación. Comprobar rechazos de acceso ajeno y un rollback que conserve IDs, históricos y vectores.
4. Presentar el SHA del candidato, resultados, riesgos y ventana. Con autorización, integrar ese candidato, aplicar el corte de base y publicar el frontend y backend correspondientes. Mantener la Data API apagada. Confirmar salud PostgreSQL y repetir el recorrido con las cuentas autorizadas de la revisión publicada.

SmartClaim se considera terminado para este alcance cuando los cinco actores pueden operar el recorrido en la versión publicada, el historial y la autorización son verificables, las sugerencias citan evidencia vigente y quedan privadas hasta aprobación, y el cambio es reversible con los datos preservados. El proveedor LLM de pago, el cobro electrónico y el envío de correos requieren una decisión de alcance independiente.
