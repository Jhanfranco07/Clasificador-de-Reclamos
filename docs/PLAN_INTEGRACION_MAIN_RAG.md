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
