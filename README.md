# SmartClaim AI

SmartClaim AI es un prototipo academico de Ingenieria de Sistemas para registrar, clasificar y apoyar la respuesta inicial de reclamos de clientes en una empresa digital tipo delivery.

El sistema permite ingresar reclamos, clasificarlos con un modelo local de Machine Learning, recuperar informacion desde una base documental mediante un RAG academico con TF-IDF, generar una respuesta sugerida y dejarla disponible para revision humana antes de su aprobacion.

## Problema Que Resuelve

En operaciones de delivery, los reclamos llegan por multiples canales y suelen requerir revision rapida, clasificacion por tipo de incidencia, priorizacion y una respuesta inicial consistente. SmartClaim AI centraliza ese flujo y ayuda al agente de soporte a:

- Registrar reclamos de clientes.
- Clasificar automaticamente el caso.
- Identificar prioridad, confianza y sentimiento.
- Recuperar documentos internos relevantes.
- Generar una respuesta sugerida.
- Revisar, editar y aprobar la respuesta final.
- Consultar historial, metricas, trazabilidad y reportes.

## Tecnologias Usadas

- Python 3.12 o superior.
- Streamlit para la interfaz web.
- FastAPI para la API backend full stack.
- React + Vite para la interfaz web adaptada desde Figma.
- SQLite para persistencia local.
- Pandas para manejo de datos.
- scikit-learn para clasificacion y recuperacion TF-IDF.
- Joblib para serializacion de modelo e indice.
- TF-IDF + similitud coseno para busqueda documental local.

## Estructura De Carpetas

```text
smartclaim_ai/
|-- app.py                         # Dashboard principal de Streamlit
|-- backend/                       # API FastAPI para la version full stack
|-- frontend/                      # Interfaz React/Vite adaptada desde Figma
|-- requirements.txt               # Dependencias del proyecto
|-- README.md                      # Documentacion de instalacion y uso
|-- .env                           # Variables locales privadas, ignoradas por Git
|-- assets/                        # Estilos visuales y componentes UI
|-- data/                          # Base SQLite y dataset de entrenamiento
|   |-- smartclaim.db
|   `-- reclamos_entrenamiento.csv
|-- database/                      # Conexion, esquema SQL, seed y repositorios
|-- models/                        # Modelo ML entrenado y reporte de entrenamiento
|-- modules/                       # Clasificador, RAG, metricas y procesamiento de texto
|-- pages/                         # Paginas del sistema Streamlit
|-- scripts/                       # Scripts de preparacion, entrenamiento e indice RAG
`-- vector_store/                  # Vectorizador, matriz TF-IDF y metadata del RAG
```

## Requisitos Previos

- Windows 10/11.
- PowerShell.
- Python instalado y disponible como `python` o `py`.
- Node.js 20 o superior para ejecutar la version React/Vite.
- Conexion a internet para instalar dependencias la primera vez.

Verificar Python:

```powershell
python --version
```

o:

```powershell
py --version
```

## Instalacion En Windows PowerShell

Desde la carpeta donde se encuentra el proyecto:

```powershell
cd smartclaim_ai
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si tu instalacion usa el lanzador `py`, puedes crear el entorno asi:

```powershell
py -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Preparar Base De Datos

El proyecto incluye `data/smartclaim.db` como base local preparada. Si se elimina o se quiere regenerar la estructura, ejecutar:

```powershell
python scripts/prepare_database.py
```

Este comando crea las tablas, carga catalogos, documentos base y registra el dataset de entrenamiento en SQLite cuando corresponde.

## Entrenar El Modelo

Para regenerar el clasificador local:

```powershell
python scripts/train_model.py
```

El script entrena un pipeline con `TfidfVectorizer` y `LogisticRegression`, y genera:

```text
models/claim_classifier.joblib
models/training_report.txt
```

## Construir Indice RAG

Para reconstruir fragmentos documentales y el indice TF-IDF:

```powershell
python scripts/build_rag_index.py
```

Este comando genera o actualiza:

```text
vector_store/rag_tfidf_vectorizer.joblib
vector_store/rag_tfidf_matrix.joblib
vector_store/rag_metadata.joblib
```

## Ejecutar El Sistema

Con el entorno virtual activado:

```powershell
python -m streamlit run app.py
```

La aplicacion se abrira en:

```text
http://localhost:8501
```

Si el puerto 8501 esta ocupado, Streamlit puede usar otro puerto y lo mostrara en consola.

## Ejecucion Full Stack React + FastAPI

La version full stack conserva la logica Python existente, pero la expone por API y usa la interfaz React adaptada desde la demo de Figma.

Terminal 1 - backend:

```powershell
cd smartclaim_ai
.\.venv\Scripts\activate
python scripts/prepare_database.py
python scripts/train_model.py
python scripts/build_rag_index.py
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2 - frontend:

```powershell
cd smartclaim_ai\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

URLs locales:

```text
Frontend React: http://127.0.0.1:5173
Backend API:    http://127.0.0.1:8000
Docs API:       http://127.0.0.1:8000/docs
```

Usuarios base creados por el backend:

```text
Cliente: maria.gonzalez@email.com        Password: 123456
Agente:  laura.martinez@smartclaim.com   Password: 123456
Admin:   admin@smartclaim.com            Password: 123456
```

La autenticacion full stack usa usuarios en base de datos, hash PBKDF2 y token Bearer firmado con `AUTH_SECRET`.
El registro de cliente crea una cuenta real y tambien registra el cliente para pedidos y reclamos.

Permisos por rol:

- `CLIENT`: catálogo, pedidos, reclamos propios, conversación y notificaciones.
- `AGENT`: dashboard operativo, bandeja de reclamos, análisis, respuestas, escalamiento y cierre.
- `ADMIN`: funciones del agente, base documental, reindexación, configuración IA y reportes globales.

## PostgreSQL En Supabase

El proyecto puede trabajar en dos modos:

```text
DB_PROVIDER=sqlite    # modo local por defecto
DB_PROVIDER=postgres  # modo produccion con Supabase/PostgreSQL
```

Para crear tablas y migrar datos desde SQLite hacia Supabase:

```powershell
cd smartclaim_ai
.\.venv\Scripts\activate
python scripts/migrate_sqlite_to_postgres.py
```

El script ejecuta:

- `database/postgres_schema.sql`
- `database/postgres_seed_data.sql`
- migracion de registros desde `data/smartclaim.db`

Variables necesarias en Render para usar Supabase:

```text
APP_ENV=production
DB_PROVIDER=postgres
DATABASE_URL=postgresql://...
USE_RAG=true
MODEL_PROVIDER=local
AUTH_SECRET=change-this-secret-in-production
CORS_ORIGINS=https://clasificador-de-reclamos.vercel.app
ALLOW_VERCEL_PREVIEWS=false
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
USE_OPENAI_EMBEDDINGS=true
ENABLE_PGVECTOR_RAG=true
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.70
```

No subas `.env` al repositorio. La cadena real de `DATABASE_URL` debe quedar solo como variable secreta en Render o en tu entorno local.
En producción, `AUTH_SECRET` debe tener al menos 32 caracteres. Mantén `ALLOW_VERCEL_PREVIEWS=false`
para aceptar únicamente los dominios definidos en `CORS_ORIGINS`.

## Pruebas Funcionales

Si `pytest` no esta instalado, puedes instalarlo junto con las dependencias del proyecto:

```powershell
pip install -r requirements.txt
```

O instalarlo de forma puntual:

```powershell
pip install pytest
```

Para ejecutar las pruebas automatizadas:

```powershell
pytest
```

Las pruebas incluidas validan:

- Creacion de cliente.
- Creacion de reclamo.
- Clasificacion automatica de reclamos.
- Recuperacion documental con RAG activo.
- Generacion de respuesta con RAG activo.
- Generacion de respuesta basica con RAG desactivado.
- Guardado de analisis IA.
- Guardado de respuesta sugerida.
- Cambio de estado del reclamo.
- Registro de historial de cambios.

Flujo recomendado para prueba manual en la interfaz:

1. Ejecutar `python -m streamlit run app.py`.
2. Abrir `http://localhost:8501`.
3. Ir a Nuevo Reclamo.
4. Registrar un reclamo y usar Guardar reclamo sin analizar.
5. Ir a Historial y verificar que el caso aparece como Nuevo.
6. Usar Analizar con IA.
7. Revisar categoria, prioridad, confianza, respuesta sugerida y documentos consultados.
8. Editar y aprobar la respuesta.
9. Marcar como Respondido, Escalar o Cerrar segun el escenario.
10. Ir a Reportes y verificar que los indicadores reflejan los cambios.
11. Ir a Configuracion, desactivar Usar contexto RAG y regenerar una respuesta desde Historial.
12. Verificar que la respuesta indique que fue generada sin RAG y que no registra documentos consultados.

Flujo recomendado para prueba manual full stack:

1. Abrir el frontend React.
2. Agregar productos al carrito desde el catalogo.
3. Seleccionar Iniciar sesion y pagar.
4. Iniciar sesion como cliente o registrar una cuenta nueva.
5. Confirmar direccion y metodo de pago en Checkout.
6. Verificar el pedido en Mis pedidos.
7. Reportar un problema desde el detalle del pedido.
8. Iniciar sesion como agente o admin y revisar el reclamo en la bandeja administrativa.

## Modulos Del Sistema

### Dashboard

Vista principal con indicadores operativos: reclamos recibidos, casos clasificados por IA, pendientes, automatizacion, revision humana, aprobacion, confianza promedio y casos criticos.

### Nuevo Reclamo

Formulario para registrar cliente, pedido, canal, fecha y descripcion del reclamo. Permite guardar el caso sin analizar o guardarlo y ejecutar analisis IA de inmediato.

### Historial

Bandeja operativa para consultar reclamos registrados, aplicar filtros, revisar detalle del caso, analizar con IA, regenerar respuesta, editarla, aprobarla, escalar el caso, marcarlo como respondido o cerrarlo.

### Analisis IA

Muestra la clasificacion automatica, prioridad, confianza, sentimiento, palabras clave, entidades detectadas y recomendacion de atencion.

### Base Documental

Lista documentos internos usados como base de conocimiento. Incluye politicas, procedimientos, FAQ, manuales, SLA, reglas de escalamiento, criterios de cierre, reglas de privacidad, evidencia permitida y plantillas de respuesta por categoria.
El seed inicial carga 18 documentos detallados para alimentar el RAG y el LLM con informacion operativa del negocio.

### Motor RAG

Permite reconstruir fragmentos, generar el indice vectorial y probar recuperacion documental por similitud.
Puede usar OpenAI Embeddings para recuperacion semantica sin instalar modelos pesados en Render.
En modo SQLite conserva TF-IDF como respaldo local.

### Reportes

Presenta metricas por categoria, prioridad, estado, canal, sentimiento, revision humana, respuestas aprobadas, tiempos de atencion y casos criticos.

### Configuracion

Permite ajustar parametros basicos del prototipo: umbral de confianza, revision humana obligatoria, uso de RAG y maximo de documentos recuperados.

## Aclaracion Academica Sobre IA Y RAG

Este prototipo usa OpenAI Embeddings cuando existe una clave configurada y conserva TF-IDF como respaldo local. El indice OpenAI se guarda en JSON para no recalcular embeddings en cada solicitud. Opcionalmente, PostgreSQL/Supabase puede usar pgvector.

Si `OPENAI_API_KEY` esta configurada, la respuesta sugerida se genera con OpenAI mediante la Responses API usando los documentos recuperados como contexto. Si no hay clave, el sistema usa una plantilla local para mantener la demo operativa.

## Limitaciones Actuales

- El envio ocurre dentro del hilo del reclamo; no integra correo, WhatsApp ni SMS externos.
- En modo SQLite, el RAG usa TF-IDF; el modo vectorial real requiere PostgreSQL/Supabase con `pgvector`.
- La generacion de respuesta usa OpenAI si hay API key; si no, usa plantilla local.
- La version full stack tiene API FastAPI; para produccion se recomienda usar PostgreSQL/Supabase en lugar de SQLite local.
- El checkout registra pedidos reales en base de datos, pero no integra una pasarela de pago externa.
- No incluye Dockerfile ni docker-compose en esta fase.

## Mejoras Futuras

- Evaluar calidad de respuestas generadas por OpenAI con metricas y feedback del agente.
- Optimizar indices `pgvector` si la base documental crece.
- Integrar OAuth/Supabase Auth si se requiere autenticacion administrada por terceros.
- Agregar pruebas automatizadas para endpoints FastAPI y componentes React.
- Agregar Dockerfile y docker-compose.
- Incorporar auditoria avanzada de prompts, respuestas y decisiones del modelo.
- Crear un flujo real de envio de respuesta al cliente.

## OpenAI Embeddings Y Render Gratuito

SmartClaim AI no instala `torch`, `transformers` ni `sentence-transformers`. La recuperacion semantica usa la API de OpenAI y cae automaticamente al RAG TF-IDF si falta la clave, no hay credito o la API falla.

Generar manualmente el indice:

```powershell
python scripts/build_openai_embeddings_index.py
```

El resultado se guarda en `vector_store/openai_embeddings.json`. El script compara el hash de cada fragmento y solo vuelve a generar los embeddings modificados. No se ejecuta durante el inicio de FastAPI.

## Conversacion Continua De Reclamos

Cada reclamo tiene un hilo de mensajes. La descripcion inicial se registra como primer mensaje; cliente y soporte pueden responder mientras el caso este abierto. Una respuesta del cliente devuelve el caso a revision, una respuesta del agente genera una notificacion y el caso puede cerrarse o reabrirse.

```text
GET  /api/claims/{claim_id}/messages
POST /api/claims/{claim_id}/messages
POST /api/claims/{claim_id}/close
POST /api/claims/{claim_id}/reopen
```

## Chatbot De Ayuda

El widget flotante consulta `POST /api/chat`. Todas las llamadas a OpenAI ocurren en FastAPI; la clave nunca se expone al frontend. Sin OpenAI, el chatbot responde con orientacion local basica.

## Navegacion De Cliente

Un cliente autenticado puede navegar entre Inicio, Restaurantes, Carrito, Mis pedidos, Mis reclamos y Ayuda. Las rutas `/restaurants`, `/products` y `/cart` mantienen acceso al catalogo sin cerrar sesion.

## Verificacion Full Stack

```powershell
python -m compileall -q backend database modules scripts tests
python -m pytest -q
cd frontend
npm install
npm run build
```

## Flujo Recomendado De Demo

1. Abrir el Dashboard.
2. Ir a Nuevo Reclamo.
3. Registrar un reclamo y seleccionar Guardar y analizar con IA.
4. Revisar categoria, prioridad, confianza y respuesta sugerida.
5. Ir a Historial.
6. Seleccionar el reclamo.
7. Editar y aprobar la respuesta.
8. Marcar como respondido o cerrar el caso.
9. Revisar Reportes y Panel Ejecutivo.
