# Validación de SmartClaim AI sin OpenAI

Fecha: 30 de octubre de 2026. Rama: `feature/optimizacion-flujo-ia`.

## Resultado final

| Comprobación | Resultado |
|---|---|
| pytest | **70 aprobadas, 0 fallidas**; ejecución final de 18,73 s. |
| Playwright / Chromium | **5 aprobadas, 0 fallidas**; ejecución de 15,7 s. |
| Total de pruebas | **75 aprobadas, 0 fallidas**. |
| Compilación | `npm run build` correcto; 2.603 módulos transformados. |
| Dependencias Python | `pip check`: sin incompatibilidades declaradas. |
| Integridad del diff | `git diff --check`: correcto; avisos informativos LF/CRLF. |
| Intentos externos inesperados en pytest | **0**. |
| Autocomprobaciones del bloqueo | **14 sondas bloqueadas**, sin conexiones reales. |

Los tiempos son duraciones de las ejecuciones de pruebas, no mediciones de rendimiento del producto.

## Preparación e identificación de llamadas

Se conservaron los cambios existentes y la rama actual. No se modificó código de negocio durante esta validación.

Puntos que pueden utilizar OpenAI en la aplicación:

- `modules/chatbot_service.py`: `OpenAI(...).responses.create` para consultas generales.
- `modules/rag_engine.py`: `OpenAI(...).responses.create` para respuestas sugeridas; construcción y búsqueda pgvector a través de `create_embeddings`.
- `modules/openai_embeddings.py`: `OpenAI(...).embeddings.create` para construir el índice JSON y vectorizar consultas. Lo invoca también el script de indexación existente.

No se ejecutaron scripts de entrenamiento, migración o reindexación contra datos del workspace o producción. El modelo existente se copió a rutas temporales para probar su carga y predicción reales.

## Aislamiento y ausencia de consumo

El aislamiento se instala antes de recopilar/importar los tests:

1. Se deshabilita la carga del `.env` mediante `PYTHON_DOTENV_DISABLED`.
2. Se usan valores de configuración únicamente en el proceso de pytest y se restauran al finalizar. No se borran archivos ni variables del entorno del usuario.
3. Se bloquean clientes OpenAI, AsyncOpenAI, Client, AsyncClient, AzureOpenAI y AsyncAzureOpenAI.
4. Se bloquean HTTP síncrono/asíncrono, resolución DNS, `socket.connect` y `connect_ex`.
5. Se bloquean conexiones psycopg síncronas/asíncronas, incluidas las entradas por clase.
6. SQLite, índices TF-IDF, JSON y copia del modelo utilizan rutas temporales por prueba.
7. Cualquier intento inesperado queda contado y hace fallar el teardown y la sesión, aunque el código de aplicación haya capturado la excepción.

Se permite exclusivamente el `socketpair` local que necesita asyncio en Windows; no habilita conexiones arbitrarias a localhost ni a servicios externos. FastAPI se prueba con TestClient en memoria.

Las 14 sondas de seguridad invocan deliberadamente las barreras para comprobar que rechazan la operación. No son solicitudes enviadas a OpenAI ni conexiones a PostgreSQL: el bloqueo ocurre antes de cualquier I/O externo.

Algunas pruebas sustituyen los clientes por stubs deterministas y habilitan una clave ficticia solo en su proceso. En esos casos, `openai_used=true` representa una rama de código simulada, no una petición real, tokens o facturación.

**No hubo llamadas reales a OpenAI Chat, Responses ni Embeddings. No se consumieron tokens.** Esta conclusión se basa en el aislamiento y sus contadores; no se consultó el panel de facturación del proveedor.

## Componentes comprobados realmente

- Inicio de sesión, registro y permisos de CLIENT, AGENT y ADMIN en FastAPI.
- Creación, consulta, paginación y estados de reclamos.
- Carga del artefacto existente, componentes TF-IDF y Logistic Regression, predicción y probabilidades.
- Categorías y prioridades de entrega, cobros y fraude mediante el clasificador híbrido real.
- FAQ directa sobre documentos activos de la base temporal, umbral y referencia documental.
- Bypass FAQ tanto por servicio como por HTTP: espías confirman cero llamadas al clasificador, predictor ML, RAG, embeddings y cliente OpenAI.
- Construcción y recuperación TF-IDF real, filtros por categoría, baja confianza, categorías sin cobertura y similitud cero.
- Plantillas locales reales, edición y aprobación por agente, firma, cierre y reapertura.
- Registro de trazas en SQLite temporal y exclusión del texto sensible de las métricas.
- Regresión de pedidos, conversaciones, notificaciones, catálogo, dashboard, administración documental, perfil y reportes según las pruebas existentes.
- Compilación completa de frontend con el comando del proyecto.

Las cinco pruebas de navegador existentes comprobaron navegación cliente por reclamos/perfil, retorno después del login, persistencia del tema oscuro, restricciones del agente y acceso administrativo a reportes/documentos. No constituyen una validación visual exhaustiva ni prueban todos los recorridos de compra en navegador.

Para Chromium se inició una API temporal con las mismas barreras externas y persistencia aislada, y Vite con URL local. Se ejecutaron copias temporales de las pruebas existentes, añadiendo una fixture que aborta solicitudes fuera de los puertos locales 8000/5173. No se alteraron las pruebas E2E originales. Ambos servidores fueron detenidos al finalizar.

## Componentes simulados

| Componente | Alcance de la simulación |
|---|---|
| Generación OpenAI | Respuesta fija y fallo deliberado para comprobar generación simulada y plantilla de respaldo. |
| OpenAI Embeddings | Vectores deterministas `[1, 0]`; escritura/lectura del índice JSON y cálculo de coseno sí se ejecutan localmente. |
| PostgreSQL/pgvector | Consulta parametrizada, categoría, identificadores activos, respuesta simulada y errores que preservan el filtro al pasar a TF-IDF. |

La similitud de los vectores JSON idénticos se comprobó como 1. Esto no mide calidad semántica del embedding.

## PostgreSQL/pgvector real pendiente

No se encontró un servidor PostgreSQL escuchando en los puertos locales comprobados (5432/5433), ni ejecutables `psql`/`postgres` disponibles en PATH. Docker CLI está instalado, pero su motor Linux no estaba disponible. No se inició infraestructura ni se utilizó `DATABASE_URL` para contactar Supabase.

Por ello quedan pendientes en un entorno PostgreSQL aislado:

- Inserción real de vectores deterministas en `rag_embeddings`.
- Ejecución SQL de similitud y filtros con la extensión pgvector.
- Permisos, dimensión vectorial, índices y comportamiento de transacciones del servidor.

Las pruebas con mocks no acreditan estos puntos. No se modificó ni reindexó ninguna base Supabase.

## Incidencias y cambios de esta validación

La primera ejecución ampliada obtuvo 69 aprobadas y una fallida: una expectativa nueva suponía prioridad crítica para «Me cobraron dos veces el mismo pedido». La regla implementada asigna prioridad alta a esa formulación. Se corrigió la expectativa a `Alta`, manteniendo categoría y revisión humana; no se cambió el clasificador ni sus reglas.

La suite final pasó completa. Se observó una advertencia de deprecación Starlette/AnyIO. Durante el navegador, el servidor temporal mostró un `ConnectionResetError` de asyncio/Windows al cerrar una conexión local; las cinco pruebas terminaron correctamente. No se cambió lógica de aplicación para silenciarlo.

Un intento inicial de cargar la configuración temporal Playwright como TypeScript dentro de `node_modules` fue rechazado por Node. Se transpilaron solo las copias temporales a ESM y se repitió la ejecución con éxito. No fue un fallo funcional del producto.

Archivos modificados o añadidos en esta validación:

| Archivo | Justificación |
|---|---|
| `tests/conftest.py` | Bloqueo previo a colección, clientes asíncronos, red y PostgreSQL; detección de intentos capturados; restauración de configuración del proceso. |
| `tests/test_ai_routing.py` | Espías explícitos adicionales que demuestran que la FAQ omite OpenAI y embeddings. |
| `tests/test_offline_validation.py` | 23 pruebas adicionales, incluidas parametrizaciones, sobre aislamiento, modelo real, prioridad, plantillas, stubs y FAQ por HTTP. |
| `docs/VALIDACION_SIN_OPENAI.md` | Este informe. |
| `docs/OPTIMIZACION_FLUJO_IA.md` | Enlace a la nueva validación, conservando los resultados históricos de implementación. |

`npm run build` regeneró únicamente los artefactos ignorados de `frontend/dist`. Las copias de E2E y sus salidas se ubicaron en una carpeta temporal ignorada bajo `frontend/node_modules/.cache`; el lanzador de la API y su base se ubicaron en temporales del sistema. No se sobrescribieron reportes E2E previos.

Se compararon hashes SHA-256 antes y después: `.env`, `frontend/.env`, SQLite, modelo y los tres artefactos RAG del workspace permanecen idénticos. Las modificaciones Git que ya tenían esos binarios son previas a esta validación.

## Preparación para despliegue

El flujo local sin proveedor de modelos queda validado mediante pruebas de API y navegador, con frontend compilable. No se detectaron fallos funcionales que requirieran modificar código de negocio en esta tarea.

Esto no certifica producción: faltan la integración real pgvector y, cuando haya acceso autorizado, una prueba del proveedor de modelos. También siguen vigentes los riesgos previos documentados sobre inicialización con escrituras, migración incompleta y configuración activa. No se afirma que estén resueltos por estas pruebas.

No se realizaron commits, pushes, despliegues ni cambios de configuración/datos de producción.

## Repetición de las comprobaciones principales

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pip check
cd frontend
npm run build
```

No ejecutar Playwright contra una API compartida o producción. La ejecución de navegador descrita utilizó un lanzador temporal con rutas de persistencia y barreras explícitas; el comando E2E normal del proyecto no proporciona por sí solo ese aislamiento.

## Revalidación previa al commit y publicación de la rama

El 30 de octubre de 2026 se repitieron las comprobaciones antes de guardar los avances en `feature/optimizacion-flujo-ia`, sin implementar las correcciones funcionales futuras:

- **pytest: 70 aprobadas, 0 fallidas**; cero intentos externos inesperados y 14 sondas de bloqueo rechazadas. Se mantiene una advertencia de deprecación Starlette/AnyIO.
- **`npm run build`: correcto**, con 2.603 módulos transformados. Los artefactos de `dist` permanecen excluidos de Git.
- **Playwright ampliado: 11 aprobadas y 8 fallidas de 19** en la ejecución completa. Se reprodujeron las siete fallas de negocio ya documentadas; hubo además un timeout de 30 segundos al navegar a `/login` durante el recorrido compra/reclamo/respuesta/cierre (`page.goto: net::ERR_ABORTED`).
- Se repitió únicamente ese recorrido, con el mismo código, expectativas y timeout: **1 aprobado**. Esto registra la variabilidad observada; no reemplaza ni oculta el resultado de la ejecución completa. No se atribuye una causa definitiva al timeout ni se declara corregido.
- Las cinco pruebas Playwright originales pasaron en la ejecución completa. La copia temporal de los escenarios ampliados, capturas y bases aisladas no se incluye en el commit; los hallazgos y pasos de reproducción quedan en los documentos de auditoría.

Se revisaron 17 archivos de código, pruebas y documentación para el commit selectivo. No se encontraron valores privados de los `.env` ni patrones habituales de claves en esos candidatos. `.gitignore` cubre secretos, entornos, dependencias y salidas temporales. La SQLite y cuatro artefactos ML/RAG ya eran archivos seguidos por Git: sus modificaciones locales previas se conservan fuera del staging, sin borrarlos, restaurarlos ni incluir cambios binarios en este commit.
