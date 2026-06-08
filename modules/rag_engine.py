from pathlib import Path
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
    if using_postgres() and _pgvector_habilitado():
        try:
            return construir_indice_pgvector(forzar=forzar)
        except Exception as exc:
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

def recuperar_documentos(texto_reclamo, categoria, max_docs=3):
    """
    Recupera fragmentos relevantes.
    En PostgreSQL usa pgvector con embeddings neuronales; en SQLite usa TF-IDF.
    Devuelve una estructura compatible con el resto del sistema.
    """
    try:
        from modules.openai_embeddings import search
        semantic = search(
            " ".join([str(categoria or ""), str(texto_reclamo or "")]),
            top_k=int(os.getenv("RAG_TOP_K", str(max_docs))),
            threshold=float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.70")),
        )
        if semantic:
            return semantic[: int(max_docs)]
    except Exception:
        pass

    if using_postgres() and _pgvector_habilitado():
        try:
            if contar_embeddings_rag() == 0:
                return recuperar_documentos_tfidf(texto_reclamo, categoria, max_docs)

            consulta = " ".join([str(categoria or ""), str(texto_reclamo or "")])
            from modules.openai_embeddings import create_embeddings
            embedding = create_embeddings([consulta])[0]
            filas = buscar_embeddings_rag(embedding, max_docs=max_docs)

            resultados = []
            for fila in filas:
                score = float(fila.get("score") or 0)
                resultados.append({
                    "id_documento": fila["id_documento"],
                    "id_fragmento": fila["id_fragmento"],
                    "titulo": fila["titulo"],
                    "tipo_documento": fila["tipo_documento"],
                    "categoria_asociada": fila["categoria_asociada"],
                    "contenido": fila["texto_fragmento"],
                    "fragmento": fila["texto_fragmento"],
                    "score": round(score, 4),
                    "embedding_id": f"pgvector_{fila['id_fragmento']}",
                    "modelo_embedding": fila.get("modelo_embedding"),
                    "vector_store": "supabase_pgvector",
                })
            if resultados:
                return resultados
        except Exception:
            pass

    return recuperar_documentos_tfidf(texto_reclamo, categoria, max_docs)

def recuperar_documentos_tfidf(texto_reclamo, categoria, max_docs=3):
    vectorizer, matrix, metadata = cargar_indice_vectorial()

    consulta = " ".join([
        str(categoria or ""),
        str(texto_reclamo or "")
    ])

    consulta_vector = vectorizer.transform([consulta])
    scores = cosine_similarity(consulta_vector, matrix).flatten()

    resultados = []
    usados = set()

    for idx in scores.argsort()[::-1]:
        frag = metadata[idx]
        score = float(scores[idx])

        if score <= 0:
            continue

        clave = (frag["id_documento"], frag["id_fragmento"])
        if clave in usados:
            continue

        usados.add(clave)

        resultados.append({
            "id_documento": frag["id_documento"],
            "id_fragmento": frag["id_fragmento"],
            "titulo": frag["titulo"],
            "tipo_documento": frag["tipo_documento"],
            "categoria_asociada": frag["categoria_asociada"],
            "contenido": frag["texto_fragmento"],
            "fragmento": frag["texto_fragmento"],
            "score": round(score, 4),
            "embedding_id": frag.get("embedding_id")
        })

        if len(resultados) >= int(max_docs):
            break

    # Respaldo si la consulta no encontró similitud suficiente
    if not resultados:
        documentos = listar_documentos()
        for doc in documentos[:int(max_docs)]:
            resultados.append({
                "id_documento": doc["id_documento"],
                "id_fragmento": None,
                "titulo": doc["titulo"],
                "tipo_documento": doc["tipo_documento"],
                "categoria_asociada": doc["categoria_asociada"],
                "contenido": doc["contenido"][:450],
                "fragmento": doc["contenido"][:450],
                "score": 0.01,
                "embedding_id": None
            })

    return resultados

def _generar_respuesta_openai(nombre_cliente, codigo_pedido, descripcion, analisis, documentos, historial=None):
    if not os.getenv("OPENAI_API_KEY"):
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
        return respuesta_llm

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
        f"{control} Le recomendamos mantenerse atento/a al correo registrado, "
        f"donde se le informará el avance de la solicitud.\n\n"
        f"Gracias por comunicarse con el equipo de soporte de SmartClaim AI."
    )

def generar_respuesta_basica(nombre_cliente, codigo_pedido, descripcion, analisis):
    """
    Genera una respuesta sugerida sin consultar documentos RAG.
    Se usa cuando la configuración activa deshabilita la recuperación documental.
    """
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
        f"{control} Le recomendamos mantenerse atento/a al correo registrado, "
        "donde se le informará el avance de la solicitud.\n\n"
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
