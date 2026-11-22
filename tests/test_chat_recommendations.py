from modules import chatbot_service as chat
from types import SimpleNamespace
from unittest.mock import Mock


def test_recommendations_use_available_catalog_and_budget(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setattr(chat, "listar_catalogo", lambda: (
        [{"id_restaurante": 1, "nombre": "Cocina Demo", "categoria": "Criolla"}],
        {1: [
            {"id_producto": 1, "nombre": "Lomo saltado", "descripcion": "Carne y arroz", "precio": 28},
            {"id_producto": 2, "nombre": "Arroz con pollo", "descripcion": "Pollo y arroz", "precio": 18},
        ]},
    ))
    result = chat.answer_chat("Recomiéndame platos por menos de 20 soles")
    assert result["provider"] == "catalog"
    assert [item["productId"] for item in result["recommendations"]] == ["2"]
    assert result["recommendations"][0]["price"] == 18


def test_recommendation_followup_and_no_invented_product(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setattr(chat, "listar_catalogo", lambda: (
        [{"id_restaurante": 1, "nombre": "Cocina Demo", "categoria": "Criolla"}],
        {1: [{"id_producto": 2, "nombre": "Arroz con pollo", "descripcion": "Pollo y arroz", "precio": 18}]},
    ))
    history = [{"role": "user", "text": "Recomiéndame platos"},
               {"role": "bot", "text": "Encontré una opción"}]
    result = chat.answer_chat("¿Y si prefiero pollo?", context={"history": history})
    assert [item["name"] for item in result["recommendations"]] == ["Arroz con pollo"]
    empty = chat.answer_chat("Recomiéndame sushi", context={"history": []})
    assert empty["recommendations"] == []


def test_unknown_order_code_does_not_reveal_another_order():
    intent = chat.detect_chat_intent("Estado de ORD-OTRO-123")
    result = chat.deterministic_response(intent, {
        "last_order": {"codigo_pedido": "ORD-MIO-1", "tienda_nombre": "Demo", "estado": "CREATED"},
    })
    assert "ORD-MIO-1" not in result


def test_general_conversation_uses_optional_openai_without_network(monkeypatch):
    import openai
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
    monkeypatch.setattr(chat, "recuperar_documentos", lambda *args, **kwargs: [])
    create = Mock(return_value=SimpleNamespace(output_text="Respuesta simulada"))
    monkeypatch.setattr(openai, "OpenAI", Mock(return_value=SimpleNamespace(
        responses=SimpleNamespace(create=create))))
    result = chat.answer_chat("Hola, quiero conversar", context={"history": [
        {"role": "bot", "text": "Hola, ¿en qué te ayudo?"}]})
    assert result["provider"] == "openai"
    assert result["message"] == "Respuesta simulada"
    assert "Historial reciente" in create.call_args.kwargs["input"]


def test_general_conversation_falls_back_if_openai_fails(monkeypatch):
    import openai
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
    monkeypatch.setattr(chat, "recuperar_documentos", lambda *args, **kwargs: [])
    monkeypatch.setattr(openai, "OpenAI", Mock(side_effect=RuntimeError("simulated")))
    result = chat.answer_chat("Hola, quiero conversar")
    assert result["provider"] == "local_fallback"
    assert "recomendar platos" in result["message"]
