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
    print(f"Fragmentos generados: {total}")
    print(f"Estado del índice: {resultado.get('status')}")
    print(f"Proveedor vectorial: {resultado.get('provider', resumen.get('provider'))}")
    if resumen.get("modelo_embedding"):
        print(f"Modelo de embeddings: {resumen['modelo_embedding']}")
    print(f"Documentos indexados: {resumen['documentos']}")
    print(f"Fragmentos indexados: {resumen['fragmentos']}")
    print(f"Embeddings registrados: {resumen.get('embeddings', 0)}")
    print(f"Vectorizador generado: {resumen['vectorizador']}")
    print(f"Matriz vectorial generada: {resumen['matriz']}")


if __name__ == "__main__":
    main()
