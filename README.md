# SmartClaim AI

SmartClaim AI es una plataforma full stack para comercio delivery y gestión inteligente de reclamos. Integra catálogo, carrito, pedidos, autenticación por roles, atención de reclamos, clasificación automática, recuperación documental RAG, respuestas sugeridas, revisión humana, conversación con soporte y reportes.

La interfaz oficial está construida con **React + Vite** y consume una API desarrollada con **FastAPI**.

## Funciones principales

### Cliente

- Explorar restaurantes y productos.
- Gestionar carrito y registrar pedidos.
- Consultar pedidos propios.
- Crear y consultar reclamos.
- Conversar con soporte dentro del reclamo.
- Recibir notificaciones.
- Consultar ayuda mediante chatbot.
- Editar perfil.

### Agente

- Consultar dashboard operativo.
- Revisar la bandeja de reclamos.
- Ejecutar análisis IA.
- Revisar documentos recuperados mediante RAG.
- Editar y enviar respuestas al cliente.
- Conversar con el cliente.
- Agregar comentarios internos.
- Escalar y cerrar reclamos.

### Administrador

- Todas las funciones del agente.
- Administrar la base documental.
- Reindexar embeddings y documentos.
- Configurar parámetros de IA y RAG.
- Consultar y exportar reportes.

## Tecnologías

### Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Radix UI
- Recharts
- Playwright

### Backend, datos e IA

- Python 3.11+
- FastAPI
- SQLite para desarrollo local
- PostgreSQL/Supabase para producción
- pgvector
- scikit-learn
- TF-IDF + Logistic Regression
- OpenAI Chat y Embeddings
- pytest

## Estructura

```text
smartclaim_ai/
|-- backend/                       # API FastAPI
|-- frontend/                      # Aplicación React/Vite
|-- database/                      # Conexión, repositorios, esquemas y semillas
|-- modules/                       # Clasificador, RAG, chatbot, seguridad y métricas
|-- scripts/                       # Preparación, entrenamiento, índices y migración
|-- tests/                         # Pruebas funcionales y de API
|-- data/                          # Dataset y base SQLite local
|-- models/                        # Modelo ML entrenado
|-- vector_store/                  # Índices vectoriales locales de respaldo
|-- requirements.txt
|-- render.yaml
|-- DOCUMENTACION_TECNICA_COMPLETA.md
|-- DICCIONARIO_DATOS.md
`-- AUDITORIA_CALIDAD.md
```

## Instalación local

### 1. Backend

```powershell
cd smartclaim_ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/prepare_database.py
python scripts/train_model.py
python scripts/build_rag_index.py
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

URLs:

```text
API:          http://127.0.0.1:8000
Documentación: http://127.0.0.1:8000/docs
Salud:        http://127.0.0.1:8000/health
```

### 2. Frontend

En otra terminal:

```powershell
cd smartclaim_ai\frontend
npm install
$env:VITE_API_URL="http://127.0.0.1:8000"
npm run dev -- --host 127.0.0.1 --port 5173
```

Abrir:

```text
http://127.0.0.1:5173
```

## Cuentas de demostración

```text
Cliente: maria.gonzalez@email.com        Contraseña: 123456
Agente:  laura.martinez@smartclaim.com   Contraseña: 123456
Admin:   admin@smartclaim.com             Contraseña: 123456
```

## PostgreSQL y Supabase

El proyecto soporta:

```text
DB_PROVIDER=sqlite
DB_PROVIDER=postgres
```

Para migrar los datos locales hacia PostgreSQL:

```powershell
python scripts/migrate_sqlite_to_postgres.py
```

La migración utiliza:

- `database/postgres_schema.sql`
- `database/postgres_seed_data.sql`
- `DATABASE_URL`

## IA y RAG

El clasificador combina un modelo local TF-IDF + Logistic Regression con reglas de negocio. El motor RAG puede usar:

1. Supabase PostgreSQL + pgvector.
2. Índice local con embeddings OpenAI.
3. TF-IDF como respaldo local.

Con `OPENAI_API_KEY`, las respuestas sugeridas y ciertas respuestas del chatbot pueden generarse con OpenAI. Sin la clave, el sistema mantiene el flujo mediante reglas y plantillas locales.

Variables relevantes:

```text
APP_ENV=production
DB_PROVIDER=postgres
DATABASE_URL=postgresql://...
AUTH_SECRET=una-clave-segura-de-al-menos-32-caracteres
CORS_ORIGINS=https://clasificador-de-reclamos.vercel.app
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
USE_OPENAI_EMBEDDINGS=true
ENABLE_PGVECTOR_RAG=true
USE_RAG=true
RAG_TOP_K=3
RAG_SIMILARITY_THRESHOLD=0.70
```

No publiques `.env`, claves reales ni cadenas privadas de conexión.

## Scripts

```powershell
python scripts/prepare_database.py
python scripts/train_model.py
python scripts/build_rag_index.py
python scripts/build_openai_embeddings_index.py
python scripts/migrate_sqlite_to_postgres.py
```

## Verificación

### Backend

```powershell
python -m compileall -q backend database modules scripts tests
pytest
```

### Frontend

```powershell
cd frontend
npm install
npm run build
npm run test:e2e
```

## Despliegue

### Vercel

- Directorio raíz: `frontend`
- Build: `npm run build`
- Salida: `dist`
- Variable: `VITE_API_URL`

### Render

- Build: `pip install -r requirements.txt`
- Start:

```text
python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

- Health check: `/health`

## Documentación

Consulta [DOCUMENTACION_TECNICA_COMPLETA.md](DOCUMENTACION_TECNICA_COMPLETA.md) para conocer toda la arquitectura, módulos, endpoints, modelo de datos, seguridad, flujos, pruebas y limitaciones.
