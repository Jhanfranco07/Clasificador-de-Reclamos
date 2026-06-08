from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.db_connection import init_db
from modules.openai_embeddings import build_index
from modules.rag_engine import reconstruir_fragmentos_desde_documentos


if __name__ == "__main__":
    init_db()
    reconstruir_fragmentos_desde_documentos()
    print(build_index())
