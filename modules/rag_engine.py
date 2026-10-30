from pathlib import Path
import logging
import os
import re
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from modules.text_processing import normalizar_texto
from database.repositories import (
    listar_documentos,
    listar_fragmentos_documento,
    eliminar_fragmentos_documento,
    crear_fragmento_documento,
    contar_fragmentos_documento,
    actualizar_estado_indexacion_documento,
    eliminar_embeddings_rag,
    crear_embedding_rag,
    buscar_embeddings_rag,
    contar_embeddings_rag,
)
from database.db_connection import using_postgres

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DIR = BASE_DIR / "vector_store"
VECTORIZER_PATH = VECTOR_DIR / "rag_tfidf_vectorizer.joblib"
MATRIX_PATH = VECTOR_DIR / "rag_tfidf_matrix.joblib"
METADATA_PATH = VECTOR_DIR / "rag_metadata.joblib"
OPENAI_MODEL = os.getenv("OPENAI_CHAT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
logger = logging.getLogger(__name__)

def _pgvector_habilitado():
    return os.getenv("ENABLE_PGVECTOR_RAG", "false").strip().lower() in {"1", "true", "yes", "on"}

def dividir_en_fragmentos(texto, max_palabras=70, solapamiento=15):
    """
    Divide un documento en fragmentos con solapamiento.
    Esto permite recuperar partes específicas del documento y no solo el texto completo.
    """
    texto = re.sub(r"\s+", " ", str(texto or "")).strip()
    palabras = texto.split()

    if not palabras:
        return []

    if len(palabras) <= max_palabras:
        return [texto]

    fragmentos = []
    inicio = 0

    while inicio < len(palabras):
        fin = min(inicio + max_palabras, len(palabras))
        fragmento = " ".join(palabras[inicio:fin]).strip()
        if fragmento:
            fragmentos.append(fragmento)
        if fin >= len(palabras):
            break
        inicio = max(fin - solapamiento, inicio + 1)

    return fragmentos

def reconstruir_fragmentos_desde_documentos():
    """
    Regenera fragmentos en SQLite desde documentos_base.
    """
    documentos = listar_documentos()
    eliminar_fragmentos_documento()

    total_fragmentos = 0

    for doc in documentos:
        fragmentos = dividir_en_fragmentos(doc["contenido"], max_palabras=70, solapamiento=15)
        for idx, fragmento in enumerate(fragmentos, start=1):
            embedding_id = f"doc_{doc['id_documento']}_frag_{idx}"
            crear_fragmento_documento(doc["id_documento"], fragmento, idx, embedding_id)
            total_fragmentos += 1

        actualizar_estado_indexacion_documento(doc["id_documento"], "INDEXADO")

    return total_fragmentos

def _obtener_textos_fragmentos():
    if contar_fragmentos_documento() == 0:
        reconstruir_fragmentos_desde_documentos()

    fragmentos = listar_fragmentos_documento()

    if not fragmentos:
        reconstruir_fragmentos_desde_documentos()
        fragmentos = listar_fragmentos_documento()

    textos = []
    metadata = []

    for frag in fragmentos:
        texto_enriquecido = " ".join([
            str(frag.get("titulo") or ""),
            str(frag.get("categoria_asociada") or ""),
            str(frag.get("tipo_documento") or ""),
            str(frag.get("texto_fragmento") or "")
        ])
        textos.append(texto_enriquecido)
        metadata.append(frag)

    return textos, metadata

def construir_indice_pgvector(forzar=False):
    """
    Construye una base vectorial real en PostgreSQL/Supabase usando pgvector.
    Requiere la extension vector y embeddings generados mediante OpenAI.
    """
    if not using_postgres():
        return construir_indice_tfidf(forzar=forzar)

    if not forzar and contar_embeddings_rag() > 0:
        return {
            "status": "existente",
            "provider": "pgvector",
            "modelo_embedding": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            "fragmentos": contar_embeddings_rag(),
        }

    if contar_fragmentos_documento() == 0:
        reconstruir_fragmentos_desde_documentos()

    fragmentos = listar_fragmentos_documento()
    eliminar_embeddings_rag()

    for frag in fragmentos:
        texto_enriquecido = " ".join([
            str(frag.get("titulo") or ""),
            str(frag.get("categoria_asociada") or ""),
            str(frag.get("tipo_documento") or ""),
            str(frag.get("texto_fragmento") or ""),
        ])
        from modules.openai_embeddings import create_embeddings
        embedding = create_embeddings([texto_enriquecido])[0]
        crear_embedding_rag(frag, os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"), len(embedding), embedding)

    return {
        "status": "reconstruido",
        "provider": "pgvector",
        "modelo_embedding": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        "fragmentos": len(fragmentos),
    }

def construir_indice_tfidf(forzar=False):
    """
    Construye un índice vectorial local usando TF-IDF como representación vectorial.
    Para el prototipo académico funciona como una base vectorial ligera, sin depender de servicios externos.
    """
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    if not forzar and VECTORIZER_PATH.exists() and MATRIX_PATH.exists() and METADATA_PATH.exists():
        return {
            "status": "existente",
            "vectorizer_path": str(VECTORIZER_PATH),
            "matrix_path": str(MATRIX_PATH),
            "metadata_path": str(METADATA_PATH)
        }

    textos, metadata = _obtener_textos_fragmentos()

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=1
    )

    matrix = vectorizer.fit_transform(textos)

    joblib.dump(vectorizer, VECTORIZER_PATH)
    joblib.dump(matrix, MATRIX_PATH)
    joblib.dump(metadata, METADATA_PATH)

    return {
        "status": "reconstruido",
        "provider": "tfidf",
        "fragmentos": len(metadata),
        "vectorizer_path": str(VECTORIZER_PATH),
        "matrix_path": str(MATRIX_PATH),
        "metadata_path": str(METADATA_PATH)
    }

def construir_indice_vectorial(forzar=False):
    if forzar:
        reconstruir_fragmentos_desde_documentos()
    if using_postgres() and _pgvector_habilitado():
        try:
            return construir_indice_pgvector(forzar=forzar)
        except Exception as exc:
            logger.exception("Falló la construcción del índice pgvector; se utilizará TF-IDF")
            fallback = construir_indice_tfidf(forzar=forzar)
            fallback["fallback_reason"] = str(exc)
            return fallback
    return construir_indice_tfidf(forzar=forzar)

def cargar_indice_vectorial():
    if not (VECTORIZER_PATH.exists() and MATRIX_PATH.exists() and METADATA_PATH.exists()):
        construir_indice_tfidf(forzar=True)

    vectorizer = joblib.load(VECTORIZER_PATH)
    matrix = joblib.load(MATRIX_PATH)
    metadata = joblib.load(METADATA_PATH)

    return vectorizer, matrix, metadata

def _document_scope(categoria, confianza=None, umbral_confianza=0.85):
    """Resolve canonical categories against live data; ambiguous requests stay general."""
    from database.db_connection import fetch_all
    from modules.ai_trace import trace_append
    documents = listar_documentos()
    category = None
    if confianza is not None and confianza < umbral_confianza:
        trace_append("fallback_reasons", "low_classification_confidence")
    elif categoria and normalizar_texto(categoria) != "soporte general":
        categories = fetch_all("SELECT nombre FROM categorias_reclamo WHERE activo = 1")
        category = next((row["nombre"] for row in categories
                         if normalizar_texto(row["nombre"]) == normalizar_texto(categoria)), None)
        if category is None:
            trace_append("fallback_reasons", "unknown_category")
    if category:
        selected = [doc for doc in documents
                    if normalizar_texto(doc.get("categoria_asociada") or "") == normalizar_texto(category)]
        minimum = max(1, int(os.getenv("RAG_MIN_CATEGORY_DOCUMENTS", "1")))
        if len(selected) >= minimum:
            return category, [doc["id_documento"] for doc in selected]
        trace_append("fallback_reasons", "insufficient_category_documents")
    return None, [doc["id_documento"] for doc in documents]


def recuperar_documentos(texto_reclamo, categoria=None, max_docs=3,
                         confianza=None, umbral_confianza=0.85):
    from modules.ai_trace import trace_update, trace_append
    category, ids = _document_scope(categoria, confianza, umbral_confianza)
    trace_update(rag_executed=True, category=category)
    max_docs = max(1, int(max_docs))

    def retrieve(scope_category, document_ids):
        trace_append("retrieval_attempts", "openai_json")
        try:
            from modules.openai_embeddings import search
            semantic = search(
                str(texto_reclamo or ""),
                top_k=max(max_docs, int(os.getenv("RAG_TOP_K", str(max_docs)))),
                threshold=float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.70")),
                category=scope_category, document_ids=document_ids,
            )
            if semantic:
                trace_update(retrieval_strategy="openai_json")
                return semantic[:max_docs]
        except Exception:
            trace_append("fallback_reasons", "openai_json_unavailable")
            logger.warning("Indice local de embeddings no disponible; se intenta respaldo")

        if using_postgres() and _pgvector_habilitado():
            trace_append("retrieval_attempts", "pgvector")
            try:
                if contar_embeddings_rag() > 0:
                    from modules.openai_embeddings import create_embeddings
                    embedding = create_embeddings([str(texto_reclamo or "")])[0]
                    rows = buscar_embeddings_rag(embedding, max_docs=max_docs,
                                                categoria=scope_category, document_ids=document_ids)
                    results = [{
                        "id_documento": row["id_documento"], "id_fragmento": row["id_fragmento"],
                        "titulo": row["titulo"], "tipo_documento": row["tipo_documento"],
                        "categoria_asociada": row["categoria_asociada"],
                        "contenido": row["texto_fragmento"], "fragmento": row["texto_fragmento"],
                        "score": round(float(row.get("score") or 0), 4),
                        "embedding_id": f"pgvector_{row['id_fragmento']}",
                        "modelo_embedding": row.get("modelo_embedding"), "vector_store": "supabase_pgvector",
                    } for row in rows if float(row.get("score") or 0) > 0]
                    if results:
                        trace_update(retrieval_strategy="pgvector")
                        return results
            except Exception:
                trace_append("fallback_reasons", "pgvector_unavailable")
                logger.warning("pgvector no disponible; se intenta TF-IDF con el mismo filtro")

        trace_append("retrieval_attempts", "tfidf")
        results = recuperar_documentos_tfidf(texto_reclamo, scope_category, max_docs,
                                            document_ids=document_ids)
        trace_update(retrieval_strategy="tfidf")
        return results

    results = retrieve(category, ids) if ids else []
    if category and not results:
        trace_append("fallback_reasons", "no_relevant_category_results")
        category = None
        trace_update(category=None)
        all_ids = [doc["id_documento"] for doc in listar_documentos()]
        results = retrieve(None, all_ids) if all_ids else []
    trace_update(document_count=len(results))
    return results


def recuperar_documentos_tfidf(texto_reclamo, categoria=None, max_docs=3, document_ids=None):
    vectorizer, matrix, metadata = cargar_indice_vectorial()
    if document_ids is None:
        categoria, document_ids = _document_scope(categoria)
    # Select candidate rows BEFORE cosine ranking; fallback cannot silently bypass scope.
    candidates = [idx for idx, frag in enumerate(metadata)
                  if frag["id_documento"] in document_ids
                  and (not categoria or normalizar_texto(frag.get("categoria_asociada") or "")
                       == normalizar_texto(categoria))]
    if not candidates:
        return []
    query_vector = vectorizer.transform([str(texto_reclamo or "")])
    scores = cosine_similarity(query_vector, matrix[candidates]).flatten()
    results = []
    for position in scores.argsort()[::-1]:
        score = float(scores[position])
        if score <= 0:
            continue
        frag = metadata[candidates[position]]
        results.append({
            "id_documento": frag["id_documento"], "id_fragmento": frag["id_fragmento"],
            "titulo": frag["titulo"], "tipo_documento": frag["tipo_documento"],
            "categoria_asociada": frag["categoria_asociada"],
            "contenido": frag["texto_fragmento"], "fragmento": frag["texto_fragmento"],
            "score": round(score, 4), "embedding_id": frag.get("embedding_id"),
            "vector_store": "tfidf",
        })
        if len(results) >= int(max_docs):
            break
    # No arbitrary first-document fallback: zero similarity means no evidence.
    return results


def _generar_respuesta_openai(nombre_cliente, codigo_pedido, descripcion, analisis, documentos, historial=None):
    if not os.getenv("OPENAI_API_KEY"):
        from modules.ai_trace import trace_append
        trace_append("fallback_reasons", "openai_not_configured")
        return None

    try:
        from openai import OpenAI

        contexto = "\n\n".join(
            f"Documento: {doc.get('titulo')}\n"
            f"Categoria: {doc.get('categoria_asociada')}\n"
            f"Fragmento: {doc.get('fragmento') or doc.get('contenido')}"
            for doc in documentos[:5]
        ) or "No hay documentos recuperados."
        conversacion = "\n".join(
            f"{item.get('sender_type')}: {item.get('mensaje')}"
            for item in (historial or [])[-10:]
        ) or "Sin mensajes previos."

        from modules.ai_trace import trace_update
        trace_update(openai_used=True)
        client = OpenAI(timeout=20.0, max_retries=1)
        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=(
                "Eres un asistente de soporte para una empresa digital de delivery. "
                "Genera una respuesta inicial breve, cordial y profesional para que un agente humano la revise. "
                "No prometas reembolsos ni compensaciones definitivas. "
                "No solicites datos sensibles completos de tarjetas. "
                "Los casos de cobro, fraude, tarjeta, pedido no recibido o baja confianza requieren revision humana. "
                "No confirmes responsabilidad de la empresa sin validacion. "
                "No afirmes pagos, entregas, reembolsos o compensaciones ejecutados ni correos automaticos: el sistema no registra esas operaciones. "
                "Usa solo el contexto documental entregado cuando exista. "
                "No incluyas firmas, nombres inventados ni marcadores como [Nombre del agente]; "
                "el sistema agregara la firma del agente autenticado al momento de enviar."
            ),
            input=(
                f"Cliente: {nombre_cliente}\n"
                f"Pedido: {codigo_pedido}\n"
                f"Reclamo: {descripcion}\n"
                f"Categoria detectada: {analisis.get('categoria')}\n"
                f"Prioridad: {analisis.get('prioridad')}\n\n"
                f"Historial de conversación:\n{conversacion}\n\n"
                f"Contexto documental recuperado:\n{contexto}\n\n"
                "Redacta la respuesta sugerida en español, lista para revisión humana."
            ),
        )
        texto = getattr(response, "output_text", None)
        return texto.strip() if texto else None
    except Exception:
        from modules.ai_trace import trace_append
        trace_append("fallback_reasons", "generation_unavailable")
        logger.warning("Generación OpenAI no disponible; se utiliza plantilla local")
        return None

def generar_respuesta_sugerida(nombre_cliente, codigo_pedido, descripcion, analisis, documentos, historial=None):
    """
    Genera una respuesta sugerida fundamentada en fragmentos recuperados.
    No envía automáticamente la respuesta; queda para revisión del agente.
    """
    respuesta_llm = _generar_respuesta_openai(
        nombre_cliente, codigo_pedido, descripcion, analisis, documentos, historial
    )
    if respuesta_llm:
        from modules.ai_trace import trace_update
        trace_update(generation_strategy="openai")
        return respuesta_llm

    from modules.ai_trace import trace_update
    trace_update(generation_strategy="local_template")
    categoria = analisis.get("categoria", "Soporte general")
    prioridad = analisis.get("prioridad", "Media")

    if documentos:
        principal = documentos[0]
        sustento = (
            f"Para sustentar la atención, se consultó el documento interno "
            f"'{principal['titulo']}', específicamente un fragmento asociado a "
            f"'{principal.get('categoria_asociada') or categoria}'."
        )
    else:
        sustento = "No se encontró un documento interno específico, por lo que el caso debe ser revisado manualmente."

    if prioridad in ["Crítica", "Alta"]:
        control = (
            "Debido a la prioridad del caso, la solicitud será revisada por un agente "
            "antes de confirmar una decisión final."
        )
    elif categoria in ["Cobro indebido", "Fraude o seguridad", "Problema con tarjeta"]:
        control = (
            "Por tratarse de un caso sensible, el equipo validará la información antes "
            "de emitir una respuesta definitiva."
        )
    else:
        control = "Nuestro equipo revisará la información registrada y continuará con la atención del caso."

    return (
        f"Estimado/a {nombre_cliente},\n\n"
        f"Hemos recibido su reclamo asociado al pedido {codigo_pedido}. "
        f"Según el análisis inicial, el caso fue clasificado como '{categoria}' "
        f"con prioridad '{prioridad}'.\n\n"
        f"{sustento}\n\n"
        f"{control} Consulte las novedades en la conversación del reclamo dentro de la aplicación.\n\n"
        f"Gracias por comunicarse con el equipo de soporte de SmartClaim AI."
    )

def generar_respuesta_basica(nombre_cliente, codigo_pedido, descripcion, analisis):
    """
    Genera una respuesta sugerida sin consultar documentos RAG.
    Se usa cuando la configuración activa deshabilita la recuperación documental.
    """
    from modules.ai_trace import trace_update
    trace_update(generation_strategy="local_template")
    categoria = analisis.get("categoria", "Soporte general")
    prioridad = analisis.get("prioridad", "Media")

    if prioridad in ["Crítica", "Critica", "Alta"]:
        control = (
            "Por la prioridad del caso, un agente revisará la información antes "
            "de confirmar una decisión final."
        )
    else:
        control = "Nuestro equipo revisará la información registrada y continuará con la atención del caso."

    return (
        f"Estimado/a {nombre_cliente},\n\n"
        f"Hemos recibido su reclamo asociado al pedido {codigo_pedido}. "
        f"Según el análisis inicial, el caso fue clasificado como '{categoria}' "
        f"con prioridad '{prioridad}'.\n\n"
        "Esta respuesta fue generada sin RAG, por lo que no se consultaron documentos "
        "internos de la base documental para sustentar el mensaje.\n\n"
        f"{control} Consulte las novedades en la conversación del reclamo dentro de la aplicación.\n\n"
        "Gracias por comunicarse con el equipo de soporte de SmartClaim AI."
    )

def obtener_resumen_indice():
    construir_indice_vectorial(forzar=False)
    if using_postgres() and _pgvector_habilitado():
        embeddings = contar_embeddings_rag()
        fragmentos = listar_fragmentos_documento()
        documentos = set(f["id_documento"] for f in fragmentos)
        return {
            "fragmentos": len(fragmentos),
            "documentos": len(documentos),
            "vectorizador": embeddings > 0,
            "matriz": embeddings > 0,
            "provider": "supabase_pgvector" if embeddings > 0 else "tfidf_fallback",
            "modelo_embedding": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small") if embeddings > 0 else None,
            "embeddings": embeddings,
        }

    fragmentos = listar_fragmentos_documento()

    if not fragmentos:
        return {
            "fragmentos": 0,
            "documentos": 0,
            "vectorizador": VECTORIZER_PATH.exists(),
            "matriz": MATRIX_PATH.exists(),
            "provider": "tfidf",
            "embeddings": 0,
        }

    documentos = set(f["id_documento"] for f in fragmentos)

    return {
        "fragmentos": len(fragmentos),
        "documentos": len(documentos),
        "vectorizador": VECTORIZER_PATH.exists(),
        "matriz": MATRIX_PATH.exists(),
        "provider": "tfidf",
        "embeddings": 0,
    }
