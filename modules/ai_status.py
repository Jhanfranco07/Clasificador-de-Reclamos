"""Read recorded execution evidence without loading/training models or calling providers."""
import json

from database.db_connection import fetch_all
from modules import classifier


def execution_status():
    last = None
    for row in fetch_all("""SELECT detalle,fecha_log FROM logs_sistema
            WHERE modulo='Flujo IA' AND accion='request_completed' ORDER BY id_log DESC LIMIT 100"""):
        try:
            event = json.loads(row['detalle'] or '{}')
        except (ValueError, TypeError):
            continue
        # Historical model metadata is not evidence that this runtime executed it.
        model = event.get('classification_model') if isinstance(event, dict) else None
        if model not in {'modelo_ml_tfidf_logistic_regression', 'modelo_hibrido_ml_reglas', 'modelo_reglas_mejorado'}:
            continue
        last = dict(classifierModel=model, generationStrategy=event.get('generation_strategy'),
                    retrievalStrategy=event.get('retrieval_strategy'), openaiUsed=event.get('openai_used') is True,
                    recordedAt=row['fecha_log'], outcome=event.get('outcome'))
        break
    return dict(classifierArtifactPresent=classifier.MODEL_PATH.is_file(), lastExecution=last)
