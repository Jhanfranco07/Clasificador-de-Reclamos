# Plan de integración de RAG a main

## Origen y dependencias

La rama origen es `feature/ampliacion-base-documental-rag`, con base `86691f7da69554ab5173afd5cb0bd5464d5169e4`. Los commits de referencia son `2ba33e6` para ampliación documental y PDF, `14f2a18` para TF-IDF híbrido e integración pgvector y el commit que contiene este plan para la validación final. Al iniciar la fase 3, el `main` remoto coincidía con el commit base.

El backend utiliza los pins de `requirements.txt`, incluidos FastAPI, Starlette, pypdf, psycopg y las dependencias científicas. El frontend se construye desde su lockfile. La recuperación TF-IDF puede operar sin servicios externos. Para PostgreSQL se necesita pgvector y la columna `rag_embeddings.embedding` de 1536 dimensiones. La evaluación semántica pagada es una operación separada.

## Esquema y riesgos

- `documentos_base` conserva IDs persistentes. `fragmentos_documento` referencia cada documento y `rag_embeddings` referencia los fragmentos. La reindexación sustituye fragmentos obsoletos y puede eliminar sus vectores por cascada. Haz un respaldo antes de sincronizar una base persistente.
- El catálogo nuevo usa `documentos_importados` para ID externo y metadatos. El importador de PostgreSQL incluido se limita a destinos locales de prueba. Para una base ya poblada, revisa conflictos y prepara una migración aprobada que compare la versión previa, conserve IDs y actualice texto y metadatos en la misma transacción. Evita aplicar el seed como mecanismo para reemplazar documentos existentes.
- Una columna vectorial de dimensión distinta ahora detiene el arranque y preserva los datos. Haz inventario de dimensión, extensión, vector de respaldo, asociaciones y secuencias antes del primer arranque. Si hay discrepancia, prepara una migración respaldada con ventana aprobada.
- El modo de producción evita crear cuentas demo nuevas. Antes de desplegar, verifica qué cuentas demo quedaron de versiones anteriores y cómo se aprovisionarán administradores y agentes autorizados.
- En Supabase, verifica privilegios del usuario de backend, grants y RLS si se exponen tablas vía Data API. La aplicación usa conexión de servidor. La validación con PostgreSQL local no acredita las políticas ni permisos de la instancia productiva. [Seguridad de la Data API de Supabase](https://supabase.com/docs/guides/api/securing-your-api)

## Ensayo y revisión posterior

1. Confirma de nuevo los SHA de `origin/main` y de la rama documental. Usa un worktree de ensayo separado. Si el objetivo sigue siendo ancestro, simula un avance rápido solo en la rama temporal. Si cambió, vuelve a verificar diferencias y conflictos.
2. Instala dependencias desde los archivos del repositorio. Ejecuta pytest con un DSN local de pruebas, TypeScript, compilación, Playwright y las auditorías. Comprueba reportes, PDF y CSV, pedido, reclamo, borrador privado, publicación por agente, historial y referencias documentales.
3. Repite la verificación sobre una copia de la base de destino debidamente aislada. Revisa conteos, versiones, privilegios, credenciales de servicio, plan de migración y rollback. Conserva los resultados de la prueba antes de autorizar cambios productivos.
4. Solicita revisión del diff en GitHub y del plan de datos. Ejecuta el merge real únicamente después de la aprobación correspondiente.

El ensayo local partió del SHA de main verificado en GitHub, usó la rama temporal `codex/ensayo-rag-main-fase3` en `smartclaim_rag_integration_phase3` y avanzó sin conflictos al candidato local d5ac5b9. Allí pasaron las 42 pruebas de backend con una instalación limpia, npm ci, TypeScript y la compilación. La suite Playwright de siete casos pasó sobre el mismo código funcional contra PostgreSQL local. Main conservó su SHA y la rama de ensayo quedó local.

## Entorno de prueba y rollback

- **Vercel.** Usa un frontend Preview con `VITE_API_URL` apuntando al backend aislado. Comprueba navegación SPA, llamadas al API y el origen efectivo. No reutilices variables sensibles de producción para Preview. [Variables de entorno en Vercel](https://vercel.com/docs/environment-variables)
- **Render.** Usa un servicio de prueba con base separada y `APP_ENV=production` para ensayar la configuración real. Configura un secreto nuevo, el origen exacto en `CORS_ORIGINS`, `ALLOW_VERCEL_PREVIEWS=false` y el health check `/health`. El `render.yaml` existente usa el origen productivo y requiere configuración específica del entorno de prueba antes de reutilizarse. [Preview Environments de Render](https://render.com/docs/preview-environments)
- **Rollback.** Registra los SHA de frontend y backend y toma un respaldo verificable de base e índice antes de migrar. Ante un problema, revierte primero el tráfico al par de versiones compatible. Restaura datos solo si la migración los alteró y la restauración fue aprobada. Un rollback de código por sí solo puede volver a habilitar el comportamiento anterior del seed o de la dimensión vectorial. Valida el arranque y el catálogo en la copia restaurada antes de reabrir tráfico.

## Rama de cinco roles

La rama `feature/optimizacion-flujo-ia` permanece en su propio worktree. La intersección con los cambios publicados incluye backend, conexión y repositorios, API frontend, Base documental, Playwright, motor RAG, embeddings y pruebas de autenticación. El trabajo local de esa rama también toca pantallas de reclamos y transacciones. Revisa explícitamente contratos de roles y permisos, estado de respuestas, migraciones, seeds y endpoints antes de combinar ambas ramas. El ensayo de integración documental con `main` no resuelve esa integración futura.


## Fase 4. Candidato y condiciones para integrar

Origen auditado `ea2b6d9b5f71e57024d82b238652ee908773a045`. GitHub devolvió `86691f7da69554ab5173afd5cb0bd5464d5169e4` para `main`. La rama documental tenía tres commits exclusivos y 30 archivos distintos. El candidato de fase 4 se ensayó con un avance rápido sin conflictos en `codex/ensayo-rag-main-fase4`, dentro de `smartclaim_rag_integration_phase4`. La rama de cinco roles conservó su commit `eb8dd2d91b4d5db220554ad065e00bacc07521bd` y sus 35 cambios de estado local. El candidato no se publicó como rama separada.

### Protección de datos incorporada

- El arranque automático aplica esquema, seeds y sincronización solo en desarrollo local. En producción, Render, Vercel o PostgreSQL sin destino de loopback inequívoco, se omite la preparación automática. Con PostgreSQL se conserva únicamente la inspección de dimensión en lectura. Una incompatibilidad detiene el inicio y conserva el índice anterior.
- En esos destinos, las operaciones documentales de creación, edición, baja y reindexación del panel responden 503 y requieren una intervención de mantenimiento separada. El listado y la vista previa de PDF conservan la autorización administrativa. Es una restricción deliberada de esta entrega hasta aprobar una ruta de escritura alojada.
- La sincronización local conserva IDs de fragmentos coincidentes. Elimina fragmentos obsoletos y puede borrar por cascada sus vectores. El seed PostgreSQL preserva documentos con ID existente, ajusta la secuencia y puede insertar filas faltantes, por lo que permanece fuera del arranque alojado. El importador de PostgreSQL solo acepta bases de prueba locales.
- Frente a main, se usa el esquema PostgreSQL documental existente y la dimensión 1536 ya declarada. La tabla de metadatos del importador se crea al cargar explícitamente. Las reglas de consulta excluyen asociaciones obsoletas o incompatibles. Que el esquema del repositorio sea compatible con un PostgreSQL nuevo no acredita el esquema efectivo de producción.

### Preflight pendiente sobre una copia autorizada

1. Identificar el SHA activo de frontend y backend, rama vinculada, automatización de despliegues, proveedor de base, permisos del rol y configuración de CORS, con evidencia que omita valores secretos.
2. Obtener un respaldo restaurable de la base de destino y ensayar su restauración en una instancia aislada. Inventariar extensión, tipos, secuencias y constraints, incluidas las cascadas, junto a IDs, categorías, versiones y conteos de documentos, fragmentos y vectores.
3. Comparar en lectura el catálogo objetivo y las asociaciones. Resolver IDs heredados, duplicados y versiones con el responsable de los datos. Preparar un cambio explícito y transaccional para conservar IDs y actualizar metadatos si hay registros existentes. Revisar el conjunto de fragmentos que se invalidaría antes de aceptar la reindexación.
4. Ensayar arranque protegido, autenticación de los tres roles, PDF y CRUD según política, pedidos, reclamos, reportes, fallback y rollback en esa copia. Acordar ventana y responsable antes de reactivar escritura o sincronización.
5. Si falla el preflight, mantener el PR sin integrar y conservar el despliegue anterior. Si más adelante se aplica una migración aprobada y falla, usar el respaldo probado y verificar conteos y referencias. Un rollback de código al main actual puede reintroducir seeds automáticos, por lo que debe coordinarse con el control del despliegue.

### Estado operativo

GitHub registra despliegues de producción para SHAs de main y previews para la rama documental. La automatización efectiva de Render y la compatibilidad de la base productiva no se verificaron. No hubo acceso a una copia aislada de esa base. La fase 4 usa PostgreSQL 16.15 y pgvector 0.8.6 locales, con datos académicos. La migración, la reindexación productiva y la evaluación semántica pagada quedan pendientes. Main permanece en `86691f7da69554ab5173afd5cb0bd5464d5169e4` hasta superar ese preflight. [Variables de entorno en Render](https://render.com/docs/configure-environment-variables) · [Entornos de despliegue en Vercel](https://vercel.com/docs/deployments/environments)


### Resultados y PR

- Backend y base aislada: 46 pruebas aprobadas, 0 fallidas y 0 omitidas. PostgreSQL local pasó las pruebas de importación, rollback, dimensión y fallback con vectores sintéticos. La demo SQLite arrancó y las tres cuentas ficticias accedieron al catálogo.
- Frontend: 7 pruebas Playwright aprobadas, 0 fallidas y 0 omitidas. TypeScript y Vite aprobados. El ensayo reutilizó la instalación previa de npm tras confirmar que el frontend y su lockfile coincidían. La instalación nueva del worktree temporal se interrumpió por demora.
- Auditorías de ejecución de npm y Python sin hallazgos conocidos. El escaneo del diff completo no encontró patrones de secretos, bases, modelos o índices incluidos.
- TF-IDF híbrido: 60 documentos y 76 fragmentos íntegros. Recall@3 de 69,64 % y 71,43 % en los conjuntos original y adicional. Abstención correcta 4/4 y 6/7. Se conserva el falso positivo ya conocido.
- GitHub Actions: cero workflows y cero ejecuciones registrados al auditar. Vercel informó éxito para la Preview del commit de origen y para el registro de Production del SHA actual de main. La última Preview y los checks del candidato se consultan en el PR. El backend remoto, sus permisos y la base de destino no se validaron.
- [PR #1](https://github.com/Jhanfranco07/Clasificador-de-Reclamos/pull/1), en borrador. Sin merge. SHA de main: `86691f7da69554ab5173afd5cb0bd5464d5169e4`. La decisión de despliegue sigue condicionada al preflight y al rollback ensayado.
