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
|-- .env.example                   # Variables de entorno de ejemplo
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
Copy-Item .env.example .env
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
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
```

No subas `.env` al repositorio. La cadena real de `DATABASE_URL` debe quedar solo como variable secreta en Render o en tu entorno local.

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
En modo PostgreSQL/Supabase usa `pgvector` con embeddings neuronales locales de `sentence-transformers`.
En modo SQLite conserva TF-IDF como respaldo local.

### Reportes

Presenta metricas por categoria, prioridad, estado, canal, sentimiento, revision humana, respuestas aprobadas, tiempos de atencion y casos criticos.

### Configuracion

Permite ajustar parametros basicos del prototipo: umbral de confianza, revision humana obligatoria, uso de RAG y maximo de documentos recuperados.

## Aclaracion Academica Sobre IA Y RAG

Este prototipo usa dos modos de RAG. En SQLite local usa TF-IDF como aproximacion academica. En PostgreSQL/Supabase usa `pgvector` con embeddings neuronales open source (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) para recuperacion semantica.

Si `OPENAI_API_KEY` esta configurada, la respuesta sugerida se genera con OpenAI mediante la Responses API usando los documentos recuperados como contexto. Si no hay clave, el sistema usa una plantilla local para mantener la demo operativa.

## Limitaciones Actuales

- No hay envio real de respuestas al cliente.
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
