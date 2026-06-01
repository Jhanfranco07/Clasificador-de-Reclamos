import re
import unicodedata

STOPWORDS = {"el","la","los","las","un","una","de","del","que","y","a","en","por","con","para","mi","me","no","se","es","al","lo","su","ya","pero","como","tengo","quiero","pedido"}

def normalizar_texto(texto):
    texto = texto.lower().strip()
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto)

def extraer_palabras_clave(texto, max_palabras=8):
    tokens = [t for t in normalizar_texto(texto).split() if len(t) > 3 and t not in STOPWORDS]
    freq = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    return [p for p, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:max_palabras]]

def detectar_sentimiento(texto):
    limpio = normalizar_texto(texto)
    negativas = ["molesto","inaceptable","horrible","pesimo","mal","frustrado","reembolso","demora","fraude","robo","cobro","problema","bloqueada"]
    positivas = ["gracias","bien","rapido","excelente","correcto","solucionado"]
    neg = sum(1 for p in negativas if p in limpio)
    pos = sum(1 for p in positivas if p in limpio)
    return "NEGATIVO" if neg > pos else "POSITIVO" if pos > neg else "NEUTRO"

def detectar_entidades(texto):
    limpio = normalizar_texto(texto)
    patrones = {
        "reembolso": ["reembolso", "devolucion", "devolver"],
        "cobro": ["cobro", "cobraron", "cargo", "monto"],
        "demora": ["demora", "retraso", "tarde", "demorado"],
        "seguridad": ["fraude", "robo", "hack", "cuenta", "desconocido"],
        "tarjeta": ["tarjeta", "pago", "visa", "mastercard"],
        "producto": ["producto", "comida", "hamburguesa", "bebida", "incompleto"]
    }
    return [entidad for entidad, palabras in patrones.items() if any(p in limpio for p in palabras)]
