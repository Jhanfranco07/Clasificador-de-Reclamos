# Auditoría de calidad de SmartClaim AI

## Estado general

SmartClaim AI es un prototipo full stack funcional y presentable. Implementa autenticación por roles, catálogo, pedidos, reclamos, clasificación local, RAG con pgvector/OpenAI, revisión humana, conversación, notificaciones, base documental y reportes.

## Mejoras aplicadas

- Actualización de React Router para eliminar vulnerabilidades conocidas.
- Validación obligatoria de `AUTH_SECRET` seguro en producción.
- Restricción de CORS mediante `CORS_ORIGINS`, `FRONTEND_URL` y control opcional de previews.
- Endpoint `/health` con comprobación real de base de datos y proveedor activo.
- Registro de fallos de OpenAI, embeddings y pgvector en logs del backend.
- Expiración de sesión gestionada globalmente en el frontend.
- Navegación posterior al login basada en el rol real, no en el dominio del correo.
- Timeout explícito para solicitudes del frontend.
- Eliminación de acciones de perfil sin implementación.
- Mejoras semánticas y de accesibilidad en navegación, cuenta y notificaciones.
- Pruebas para salud del servicio y configuración insegura de producción.

## Riesgos pendientes priorizados

### Alta

- Sustituir el token HMAC artesanal por un estándar JWT o autenticación administrada.
- Incorporar rate limiting para login, chatbot, reclamos y generación IA.
- Añadir migraciones versionadas con Alembic para PostgreSQL.
- Implementar recuperación real de contraseña mediante proveedor de correo.
- Añadir monitoreo, alertas y seguimiento de errores en producción.

### Media

- Dividir `backend/main.py` por routers y servicios.
- Dividir `database/repositories.py` por dominios.
- Separar `LandingPage.tsx` en catálogo, carrito y restaurante.
- Añadir filtros por fecha y paginación en reclamos y reportes.
- Añadir pruebas E2E de cliente, agente y administrador.
- Guardar auditoría estructurada de llamadas IA, costo, latencia y fallback.

### Baja

- Añadir perfil editable de usuario.
- Incorporar tema oscuro solo si responde a una necesidad real.
- Añadir exportación PDF y filtros avanzados de reportes.

## Criterios recomendados para producción

- Definir `AUTH_SECRET` de al menos 32 caracteres.
- Definir `CORS_ORIGINS` con el dominio exacto del frontend.
- Mantener `ALLOW_VERCEL_PREVIEWS=false` salvo pruebas temporales.
- Proteger y rotar `OPENAI_API_KEY` y `DATABASE_URL`.
- Ejecutar `pytest`, `npm run build` y `npm audit --omit=dev` antes de cada despliegue.
