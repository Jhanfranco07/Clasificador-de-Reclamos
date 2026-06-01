from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from database.db_connection import init_db
from modules.rag_engine import reconstruir_fragmentos_desde_documentos, construir_indice_vectorial, obtener_resumen_indice

def main():
    init_db()
    total = reconstruir_fragmentos_desde_documentos()
    resultado = construir_indice_vectorial(forzar=True)
    resumen = obtener_resumen_indice()

    print("SmartClaim AI - Construcción de índice RAG")
    print("=" * 60)
    print(f"Fragmentos generados en SQLite: {total}")
    print(f"Estado del índice: {resultado.get('status')}")
    print(f"Documentos indexados: {resumen['documentos']}")
    print(f"Fragmentos indexados: {resumen['fragmentos']}")
    print(f"Vectorizador generado: {resumen['vectorizador']}")
    print(f"Matriz vectorial generada: {resumen['matriz']}")

if __name__ == "__main__":
    main()
