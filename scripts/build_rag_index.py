import argparse
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from database import db_connection
from modules.rag_engine import construir_indice_vectorial, obtener_resumen_indice


def main():
    parser = argparse.ArgumentParser(description="Reconstruye el índice TF-IDF sin servicios externos.")
    parser.add_argument("--sqlite", type=Path, help="Ruta de una SQLite existente.")
    args = parser.parse_args()
    if db_connection.using_postgres():
        parser.error("Este comando requiere un entorno SQLite.")
    if args.sqlite:
        if not args.sqlite.is_file():
            parser.error("La SQLite especificada no existe.")
        db_connection.DB_PATH = args.sqlite
    else:
        db_connection.init_db()
    resultado = construir_indice_vectorial(forzar=True)
    resumen = obtener_resumen_indice()

    print("SmartClaim AI - Construcción de índice RAG")
    print("=" * 60)
    print(f"Fragmentos generados: {resultado['fragmentos']}")
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
