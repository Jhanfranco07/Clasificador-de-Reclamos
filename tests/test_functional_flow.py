import pytest


@pytest.fixture()
def temp_app(monkeypatch, tmp_path):
    import database.db_connection as db_connection

    monkeypatch.setattr(db_connection, "DB_PATH", tmp_path / "smartclaim_test.db")


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


def test_reindex_corrige_fragmento_cruzado_y_descarta_version_anterior(temp_app):
    from database.db_connection import execute, fetch_all
    from database.repositories import actualizar_documento_base
    from modules.rag_engine import construir_indice_tfidf, recuperar_documentos_tfidf

    title = "FAQ sobre pedido incompleto o productos faltantes"
    construir_indice_tfidf(forzar=True)
    faq = recuperar_documentos_tfidf("productos faltantes en pedido incompleto", "Producto incompleto")[0]
    fraud = recuperar_documentos_tfidf("acceso no reconocido y pedidos no autorizados", "Fraude o seguridad")[0]
    assert faq["titulo"] == title
    assert faq["id_documento"] != fraud["id_documento"]
    execute("UPDATE fragmentos_documento SET texto_fragmento = ? WHERE id_fragmento = ?",
            (fraud["fragmento"], faq["id_fragmento"]))
    assert faq["id_fragmento"] not in {
        row["id_fragmento"] for row in recuperar_documentos_tfidf("acceso no reconocido", "Producto incompleto")
    }

    content = "Faltante de producto por omisión de preparación. Validar el recibo y la entrega parcial."
    actualizar_documento_base(faq["id_documento"], title, "FAQ", "Producto incompleto", content)
    construir_indice_tfidf(forzar=True)
    repaired = recuperar_documentos_tfidf("faltante por omisión de preparación", "Producto incompleto")[0]
    assert (repaired["id_documento"], repaired["titulo"], repaired["categoria_asociada"], repaired["fragmento"]) == (
        faq["id_documento"], title, "Producto incompleto", content,
    )
    assert repaired["orden_fragmento"] == 1
    assert recuperar_documentos_tfidf("zqxvv brrrt", "Producto incompleto") == []
    current_fraud = recuperar_documentos_tfidf("acceso no reconocido y pedidos no autorizados", "Fraude o seguridad")[0]
    for field in ("id_documento", "id_fragmento", "titulo", "categoria_asociada", "fragmento"):
        assert current_fraud[field] == fraud[field]
    assert len(fetch_all("SELECT * FROM fragmentos_documento WHERE id_documento = ?", (faq["id_documento"],))) == 1
    construir_indice_tfidf(forzar=True)
    assert recuperar_documentos_tfidf("faltante por omisión de preparación", "Producto incompleto")[0] == repaired


def test_importador_valida_duplicados_y_no_sobrescribe(temp_app):
    import json
    from pathlib import Path
    from database.db_connection import DB_PATH, fetch_one
    from scripts.import_documents import import_documents

    original = Path("data/documentos_academicos.json")
    catalog = temp_app / "catalog.json"
    doc = json.loads(original.read_text(encoding="utf-8"))[0]
    baseline = fetch_one("SELECT COUNT(*) AS n FROM documentos_base")["n"]

    def write(*rows):
        catalog.write_text(json.dumps(rows), encoding="utf-8")

    write(doc, {**doc, "id": "sc-faltantes-99"})
    assert [row["status"] for row in import_documents(DB_PATH, catalog)] == ["rejected", "rejected"]
    write({**doc, "category": "Desconocida"})
    assert import_documents(DB_PATH, catalog)[0]["status"] == "rejected"
    write(doc)
    assert import_documents(DB_PATH, catalog, dry_run=True)[0]["status"] == "created"
    assert fetch_one("SELECT COUNT(*) AS n FROM documentos_base")["n"] == baseline
    assert import_documents(DB_PATH, catalog)[0]["status"] == "created"
    assert import_documents(DB_PATH, catalog)[0]["status"] == "skipped"
    write({**doc, "title": "Intento de sobrescritura", "version": "2.0"})
    assert import_documents(DB_PATH, catalog)[0]["status"] == "rejected"
    assert fetch_one("SELECT COUNT(*) AS n FROM documentos_base")["n"] == baseline + 1
    assert fetch_one("SELECT titulo FROM documentos_base WHERE titulo = ?", (doc["title"],))


def test_reindex_revierte_los_cambios_si_falla_el_indice(temp_app, monkeypatch):
    from database.db_connection import fetch_all
    from database.repositories import actualizar_documento_base
    from modules import rag_engine

    rag_engine.construir_indice_tfidf(forzar=True)
    before = fetch_all("SELECT * FROM fragmentos_documento ORDER BY id_fragmento")
    actualizar_documento_base(4, "FAQ modificada", "FAQ", "Producto incompleto",
                             "Un documento modificado requiere nuevos fragmentos en el índice.")

    def fail(_corpus, _mode):
        raise RuntimeError("Fallo de indexación simulado")

    monkeypatch.setattr(rag_engine, "_ajustar_tfidf", fail)
    with pytest.raises(RuntimeError, match="Fallo de indexación simulado"):
        rag_engine.construir_indice_tfidf(forzar=True)
    assert fetch_all("SELECT * FROM fragmentos_documento ORDER BY id_fragmento") == before


def test_seed_conserva_ediciones_administrativas(temp_app):
    from database.db_connection import fetch_one, init_db
    from database.repositories import actualizar_documento_base

    actualizar_documento_base(4, "FAQ revisada por administración", "FAQ", "Producto incompleto",
                             "Contenido revisado para comprobar que el seed no sobrescribe ediciones.")
    init_db()
    row = fetch_one("SELECT titulo FROM documentos_base WHERE id_documento = 4")
    assert row["titulo"] == "FAQ revisada por administración"
