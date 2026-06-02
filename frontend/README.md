# SmartClaim AI Frontend

Interfaz React/Vite adaptada desde la demo de Figma para consumir el backend FastAPI de SmartClaim AI.

## Ejecucion local

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev -- --host 127.0.0.1 --port 5173
```

La app queda disponible en:

```text
http://127.0.0.1:5173
```

## Variable de entorno

```text
VITE_API_URL=http://localhost:8000
```

Para Vercel, configurar `VITE_API_URL` con la URL publica del backend desplegado. Vercel no ejecuta el backend Python/SQLite de este proyecto por si solo.
