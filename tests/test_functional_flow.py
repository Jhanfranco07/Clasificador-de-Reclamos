import pytest


@pytest.fixture()
def temp_app(monkeypatch, tmp_path):
    import database.db_connection as db_connection
    import modules.rag_engine as rag_engine

    monkeypatch.setattr(db_connection, "DB_PATH", tmp_path / "smartclaim_test.db")

    vector_dir = tmp_path / "vector_store"
    monkeypatch.setattr(rag_engine, "VECTOR_DIR", vector_dir)
    monkeypatch.setattr(rag_engine, "VECTORIZER_PATH", vector_dir / "rag_tfidf_vectorizer.joblib")
    monkeypatch.setattr(rag_engine, "MATRIX_PATH", vector_dir / "rag_tfidf_matrix.joblib")
    monkeypatch.setattr(rag_engine, "METADATA_PATH", vector_dir / "rag_metadata.joblib")

    db_connection.init_db()
    return tmp_path


def test_crear_cliente_y_reclamo(temp_app):
    from database.repositories import crear_cliente, crear_reclamo, obtener_detalle_reclamo

    id_cliente = crear_cliente("Cliente Prueba", "cliente.prueba@example.com", "999999999")
    id_reclamo = crear_reclamo(
        id_cliente,
        "ORD-TEST-001",
        "Web",
        "2026-06-01",
        "Mi pedido llego tarde y la comida estaba fria.",
    )

    reclamo, analisis, respuesta, documentos, historial = obtener_detalle_reclamo(id_reclamo)

    assert reclamo["cliente"] == "Cliente Prueba"
    assert reclamo["codigo_pedido"] == "ORD-TEST-001"
    assert reclamo["estado"] == "Nuevo"
    assert analisis is None
    assert respuesta is None
    assert documentos == []
    assert len(historial) == 1


def test_clasificar_reclamo():
    from modules.classifier import clasificar_reclamo

    resultado = clasificar_reclamo("Me cobraron dos veces por el mismo pedido y necesito devolucion.")

    assert resultado["categoria"]
    assert resultado["prioridad"] in {"Baja", "Media", "Alta", "Crítica", "Critica"}
    assert 0 <= resultado["confianza"] <= 1
    assert resultado["modelo_usado"]


def test_rag_activo_recupera_documentos_y_genera_respuesta(temp_app):
    from modules.rag_engine import construir_indice_vectorial, recuperar_documentos, generar_respuesta_sugerida

    construir_indice_vectorial(forzar=True)
    analisis = {"categoria": "Cobro indebido", "prioridad": "Alta"}
    documentos = recuperar_documentos("Me cobraron dos veces por el pedido.", "Cobro indebido", max_docs=2)
    respuesta = generar_respuesta_sugerida("Cliente Prueba", "ORD-TEST-002", "Cobro duplicado.", analisis, documentos)

    assert len(documentos) >= 1
    assert "documento interno" in respuesta
    assert "ORD-TEST-002" in respuesta


def test_respuesta_basica_sin_rag():
    from modules.rag_engine import generar_respuesta_basica

    analisis = {"categoria": "Soporte general", "prioridad": "Media"}
    respuesta = generar_respuesta_basica("Cliente Prueba", "ORD-TEST-003", "Consulta general.", analisis)

    assert "sin RAG" in respuesta
    assert "no se consultaron documentos" in respuesta
    assert "ORD-TEST-003" in respuesta


def test_openai_embeddings_disabled_uses_safe_empty_result(monkeypatch, tmp_path):
    import modules.openai_embeddings as embeddings

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(embeddings, "INDEX_PATH", tmp_path / "openai_embeddings.json")
    assert embeddings.enabled() is False
    assert embeddings.search("pedido demorado") == []


def test_guardar_analisis_respuesta_estado_e_historial(temp_app):
    from database.repositories import (
        crear_cliente,
        crear_reclamo,
        guardar_analisis,
        guardar_respuesta,
        obtener_detalle_reclamo,
        actualizar_estado_reclamo,
    )
    from modules.classifier import clasificar_reclamo
    from modules.rag_engine import construir_indice_vectorial, recuperar_documentos, generar_respuesta_sugerida

    id_cliente = crear_cliente("Cliente Flujo", "cliente.flujo@example.com")
    id_reclamo = crear_reclamo(
        id_cliente,
        "ORD-TEST-004",
        "App móvil",
        "2026-06-01",
        "Me cobraron dos veces por el mismo pedido y necesito devolucion urgente.",
    )

    analisis = clasificar_reclamo("Me cobraron dos veces por el mismo pedido y necesito devolucion urgente.")
    guardar_analisis(id_reclamo, analisis)

    construir_indice_vectorial(forzar=True)
    documentos = recuperar_documentos("Me cobraron dos veces por el mismo pedido.", analisis["categoria"], max_docs=2)
    respuesta = generar_respuesta_sugerida("Cliente Flujo", "ORD-TEST-004", "Cobro duplicado.", analisis, documentos)
    id_respuesta = guardar_respuesta(id_reclamo, respuesta, documentos, accion="Generación de respuesta con RAG")

    actualizar_estado_reclamo(id_reclamo, "Escalado", "Prueba de escalamiento", "Caso sensible.")

    reclamo, analisis_db, respuesta_db, documentos_db, historial = obtener_detalle_reclamo(id_reclamo)

    assert id_respuesta > 0
    assert reclamo["estado"] == "Escalado"
    assert analisis_db["categoria_detectada"]
    assert respuesta_db["respuesta_generada"]
    assert len(documentos_db) >= 1
    assert len(historial) >= 4


def test_guardar_respuesta_sin_rag_no_registra_documentos(temp_app):
    from database.repositories import crear_cliente, crear_reclamo, guardar_respuesta, obtener_detalle_reclamo
    from modules.rag_engine import generar_respuesta_basica

    id_cliente = crear_cliente("Cliente Sin Rag", "cliente.sinrag@example.com")
    id_reclamo = crear_reclamo(
        id_cliente,
        "ORD-TEST-005",
        "Web",
        "2026-06-01",
        "Necesito ayuda para actualizar mis datos de perfil.",
    )
    analisis = {"categoria": "Soporte general", "prioridad": "Baja"}
    respuesta = generar_respuesta_basica("Cliente Sin Rag", "ORD-TEST-005", "Consulta general.", analisis)

    guardar_respuesta(id_reclamo, respuesta, [], accion="Generación de respuesta sin RAG")
    reclamo, analisis_db, respuesta_db, documentos, historial = obtener_detalle_reclamo(id_reclamo)

    assert respuesta_db["respuesta_generada"] == respuesta
    assert documentos == []
    assert any("sin consulta RAG" in h["comentario"] for h in historial if h["comentario"])
