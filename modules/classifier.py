from pathlib import Path
import math
import joblib
import pandas as pd

from modules.text_processing import (
    normalizar_texto,
    extraer_palabras_clave,
    detectar_sentimiento,
    detectar_entidades
)

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "claim_classifier.joblib"
DATASET_PATH = BASE_DIR / "data" / "reclamos_entrenamiento.csv"

CATEGORY_RULES = {
    "Fraude o seguridad": [
        "fraude", "robo", "hack", "hackeada", "hackearon", "no reconozco",
        "cuenta", "sin permiso", "desconocido", "seguridad", "sospechosa",
        "no autorizado", "acceso", "bloqueo"
    ],
    "Cobro indebido": [
        "doble cobro", "cobro", "cobraron", "cargo", "monto incorrecto",
        "reembolso", "devolucion", "devolución", "descontaron", "pago duplicado",
        "cargo adicional", "banco", "tarifa"
    ],
    "Retraso de pedido": [
        "retraso", "demora", "tarde", "no llega", "demorado", "esperando",
        "tiempo", "fria", "fría", "entrega", "delivery", "repartidor"
    ],
    "Producto incompleto": [
        "incompleto", "faltante", "falto", "faltó", "no vino", "sin bebida",
        "sin papas", "faltan", "no incluyeron", "menos productos", "acompañamientos"
    ],
    "Producto incorrecto": [
        "incorrecto", "equivocado", "otro producto", "no pedi", "no pedí",
        "diferente", "cambiado", "no corresponde", "otra comida", "otro combo"
    ],
    "Problema con tarjeta": [
        "tarjeta", "pago rechazado", "no puedo pagar", "saldo", "visa",
        "mastercard", "metodo de pago", "método de pago", "transaccion",
        "transacción", "validar", "registrar tarjeta"
    ],
    "Soporte general": [
        "direccion", "dirección", "consulta", "ayuda", "informacion",
        "información", "cambiar", "actualizar", "cupon", "cupón",
        "perfil", "telefono", "teléfono", "correo"
    ]
}

CRITICAL_WORDS = [
    "fraude", "robo", "hack", "hackeada", "no reconozco", "sin permiso",
    "cobro", "reembolso", "devolucion", "devolución", "bloqueada",
    "no autorizado", "actividad sospechosa", "cargo desconocido"
]

HIGH_WORDS = [
    "demora", "retraso", "inaceptable", "molesto", "molesta", "urgente",
    "pedido no llega", "fria", "fría", "nunca llega", "muy tarde"
]

NEGATIVE_WORDS = [
    "molesto", "molesta", "inaceptable", "horrible", "pesimo", "pésimo",
    "mal", "frustrado", "frustrada", "reembolso", "demora", "fraude",
    "robo", "cobro", "problema", "bloqueada", "reclamo", "queja"
]

def _train_model_if_needed():
    if MODEL_PATH.exists():
        return

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline

        df = pd.read_csv(DATASET_PATH)
        X = df["texto"].astype(str)
        y = df["categoria"].astype(str)

        model = Pipeline([
            ("tfidf", TfidfVectorizer(
                lowercase=True,
                strip_accents="unicode",
                ngram_range=(1, 2),
                min_df=1
            )),
            ("clf", LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                solver="lbfgs"
            ))
        ])

        model.fit(X, y)
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_PATH)
    except Exception:
        # Si no existe scikit-learn o falla el entrenamiento, el sistema usa reglas.
        pass

def _predict_with_ml(texto):
    try:
        _train_model_if_needed()
        if not MODEL_PATH.exists():
            return None

        model = joblib.load(MODEL_PATH)
        categoria = model.predict([texto])[0]

        confianza = 0.70
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba([texto])[0]
            confianza = float(max(proba))

        return categoria, confianza
    except Exception:
        return None

def _rule_scores(texto):
    limpio = normalizar_texto(texto)
    puntajes = {}
    for categoria, palabras in CATEGORY_RULES.items():
        score = 0
        for palabra in palabras:
            palabra_norm = normalizar_texto(palabra)
            if palabra_norm in limpio:
                score += 1
        puntajes[categoria] = score
    return puntajes

def _predict_with_rules(texto):
    puntajes = _rule_scores(texto)
    categoria = max(puntajes, key=puntajes.get)
    max_score = puntajes[categoria]

    if max_score == 0:
        return "Soporte general", 0.55

    total = sum(puntajes.values())
    confianza = 0.58 + min(max_score * 0.10, 0.32)

    if total > 0:
        confianza += min((max_score / total) * 0.08, 0.08)

    return categoria, round(min(confianza, 0.94), 2)

def _calcular_prioridad(texto, categoria, confianza, sentimiento):
    limpio = normalizar_texto(texto)

    if categoria == "Fraude o seguridad":
        return "Crítica"

    if categoria == "Cobro indebido" and any(normalizar_texto(p) in limpio for p in CRITICAL_WORDS):
        return "Crítica"

    if any(normalizar_texto(p) in limpio for p in CRITICAL_WORDS):
        return "Alta"

    if categoria in ["Problema con tarjeta", "Cobro indebido"]:
        return "Alta"

    if any(normalizar_texto(p) in limpio for p in HIGH_WORDS):
        return "Alta"

    if sentimiento == "NEGATIVO" and categoria in ["Retraso de pedido", "Producto incorrecto", "Producto incompleto"]:
        return "Alta"

    if confianza < 0.65:
        return "Media"

    if categoria in ["Producto incorrecto", "Producto incompleto"]:
        return "Media"

    return "Baja"

def _fusionar_predicciones(texto):
    ml_result = _predict_with_ml(texto)
    rule_categoria, rule_conf = _predict_with_rules(texto)

    if ml_result:
        ml_categoria, ml_conf = ml_result

        # Si ML y reglas coinciden, se refuerza la confianza.
        if ml_categoria == rule_categoria:
            confianza = min(max(ml_conf, rule_conf) + 0.10, 0.98)
            return ml_categoria, round(confianza, 2), "modelo_ml_tfidf_logistic_regression"

        # Si el modelo ML tiene alta confianza, se prioriza ML.
        if ml_conf >= 0.62:
            return ml_categoria, round(ml_conf, 2), "modelo_ml_tfidf_logistic_regression"

        # Si ML duda, se usa regla.
        return rule_categoria, rule_conf, "modelo_hibrido_ml_reglas"

    return rule_categoria, rule_conf, "modelo_reglas_mejorado"

def clasificar_reclamo(texto):
    categoria, confianza, modelo_usado = _fusionar_predicciones(texto)

    sentimiento = detectar_sentimiento(texto)
    palabras_clave = extraer_palabras_clave(texto, max_palabras=10)
    entidades = detectar_entidades(texto)
    prioridad = _calcular_prioridad(texto, categoria, confianza, sentimiento)

    if prioridad in ["Crítica", "Alta"]:
        recomendacion = "Enviar a revisión humana antes de responder al cliente por tratarse de un caso sensible o de alta prioridad."
    elif confianza < 0.70:
        recomendacion = "Revisar manualmente porque la confianza del modelo es moderada."
    elif confianza < 0.85:
        recomendacion = "Validar respuesta sugerida antes de enviarla al cliente."
    else:
        recomendacion = "Puede prepararse una respuesta sugerida para aprobación del agente."

    return {
        "categoria": categoria,
        "prioridad": prioridad,
        "confianza": round(float(confianza), 2),
        "sentimiento": sentimiento,
        "palabras_clave": palabras_clave,
        "entidades": entidades,
        "recomendacion": recomendacion,
        "modelo_usado": modelo_usado
    }
