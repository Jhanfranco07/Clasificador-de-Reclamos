# Plan de despliegue integrado de SmartClaim AI

La rama integration/smartclaim-cinco-roles-rag es un candidato de evaluación. La integración a main, la configuración de los proveedores y las operaciones sobre producción quedan para una fase autorizada.

## Prerrequisitos y bloqueo de seguridad

1. Confirmar SHA, ramas de autodespliegue, URL efectiva del backend, CORS, secretos separados y cuenta PostgreSQL dedicada. Desactivar OpenAI en staging. Revisar que no se use el bootstrap local de SQLite en servicios alojados.
2. Verificar si Data API expone public. Inventariar todos los grants y políticas. Diseñar privilegios mínimos para la cuenta de servidor y aislar o retirar acceso de anon y authenticated a tablas internas. Aplicar RLS y políticas solo donde exista un contrato explícito. Probar denegación directa y autorización a través del backend en una copia antes de publicar. El hallazgo de RLS y grants en producción bloquea el despliegue.
3. Obtener respaldo autorizado, verificar restauración aislada con pgvector y guardar huellas, conteos, identificadores, secuencias, restricciones y configuración del entorno. Ensayar desde el esquema real restaurado, no solo desde una base nueva.

## Migración y catálogo

1. Sobre la copia autorizada, inventariar versiones de migración y reconciliar pedidos/reclamos históricos sin asignar titulares por inferencia. Ensayar Fase 1, 2B y 2C en el orden de dependencias. Revisar database/migrations/phase1_postgres.sql, scripts/migrate_phase2b.py y database/migrations/phase2c_postgres.sql, con las precondiciones de cada paso y controles de esquema y conteos. Verificar los nuevos roles, constraints, tablas operativas, notificaciones, historial y reintentos. El arranque alojado no ejecuta estas migraciones.
2. Mantener los documentos existentes y sus IDs. En la copia, confirmar el estado de la secuencia de documentos, incluida la marca is_called, y reconciliarla con el máximo ID antes de una inserción que use nextval. En la auditoría se observó 6 frente a 18. Usar scripts.plan_document_migration sobre la copia local para clasificar altas, revisiones y conflictos. Revisar títulos, categorías y versiones. Importar 42 académicos solo si la identidad de las filas y la aprobación del operador lo permiten. Verificar 60 documentos y 76 fragmentos únicamente para el catálogo de referencia sin divergencias.
3. Verificar vector(1536), coincidencia de modelo, metadatos y texto. Conservar embeddings vigentes. Contabilizar los vectores que se perderían por cascada si se sustituyen fragmentos. Ejecutar cambios documentales transaccionales y mantener TF-IDF como respaldo. No generar embeddings reales sin presupuesto y autorización explícita.

## Validación y rollback

En staging, ejecutar pytest, TypeScript, Vite, Chromium y las auditorías. Verificar los cinco roles y aislamiento entre titulares, pedidos y estados, RAG con abstención, aprobación antes de publicación, reportes con CORS y descarga PDF/CSV, y presentación America/Lima. Registrar resultado de los checks de seguridad, versión y permisos de la base. Validar el par de SHAs de frontend y backend y observar errores tras el eventual cambio de tráfico.

Antes de la ventana aprobada, identificar el par de despliegues anterior y suspender cambios incompatibles. Si falla una transacción, revertirla y verificar huellas. Si falla después del commit, detener escrituras y restaurar el respaldo a una base separada. Validar los datos y el código anterior contra esa copia antes de redirigir tráfico. No ejecutar el downgrade de Fase 2B si ya existen roles o eventos incompatibles. Conservar historial, comandos, asignaciones y avisos nuevos al evaluar rollback de código. El rollback de código no restaura fragmentos ni vectores borrados.

Véase el [plan previo de integración RAG](PLAN_INTEGRACION_MAIN_RAG.md) para el ensayo sintético de respaldo y restauración. La decisión productiva requiere resolver el bloqueo de seguridad y repetir el ensayo sobre una copia autorizada.
