"""Local browser-test server. Always creates its own disposable persistence."""
import argparse
import json
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-dir", required=True)
    args = parser.parse_args()
    control = Path(args.control_dir).resolve()
    if not control.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        parser.error("El directorio de control debe estar en temporales del sistema")
    control.mkdir(parents=True, exist_ok=False)
    scope = runpy.run_path(str(ROOT / "tests/conftest.py"))
    scope["pytest_configure"](None)
    from database import db_connection as db
    from modules import rag_engine as rag, openai_embeddings as emb, classifier
    from backend.main import app
    import uvicorn
    with tempfile.TemporaryDirectory(prefix="smartclaim-browser-", ignore_cleanup_errors=True) as tmp:
        directory = Path(tmp)
        db.DB_PATH = directory / "test.db"
        rag.VECTOR_DIR = directory / "vectors"
        rag.VECTORIZER_PATH = rag.VECTOR_DIR / "v.joblib"
        rag.MATRIX_PATH = rag.VECTOR_DIR / "m.joblib"
        rag.METADATA_PATH = rag.VECTOR_DIR / "metadata.joblib"
        emb.INDEX_PATH = rag.VECTOR_DIR / "embeddings.json"
        shutil.copyfile(classifier.MODEL_PATH, directory / "model.joblib")
        classifier.MODEL_PATH = directory / "model.joblib"
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning"))
        def watch():
            while not (control / "stop").exists():
                time.sleep(0.2)
            server.should_exit = True
        threading.Thread(target=watch, daemon=True).start()
        try:
            server.run()
        finally:
            (control / "network.json").write_text(json.dumps({"unexpected": scope["_guard"].pending}))
            scope["pytest_unconfigure"](None)
            import gc
            gc.collect()


if __name__ == "__main__":
    main()
