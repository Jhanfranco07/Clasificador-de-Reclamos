from pathlib import Path
import sys
import random
from datetime import date, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from database.db_connection import init_db
from database.repositories import (
    crear_cliente,
    crear_reclamo,
    guardar_analisis,
    guardar_respuesta,
    get_configuracion_activa,
    actualizar_estado_reclamo,
    actualizar_respuesta_final,
    aprobar_respuesta,
    marcar_respondido,
    escalar_reclamo,
    cerrar_reclamo,
    crear_comentario_agente,
    crear_evaluacion_respuesta,
    registrar_log,
    limpiar_datos_prueba,
    contar_reclamos,
    obtener_ultimo_id_respuesta,
    asignar_responsable
)
from modules.classifier import clasificar_reclamo
from modules.rag_engine import recuperar_documentos, generar_respuesta_sugerida, construir_indice_vectorial

NOMBRES = [
    "Andrea López", "Carlos Ramírez", "Valeria Torres", "Mateo Castillo", "Lucía Flores",
    "Javier Mendoza", "Sofía Vargas", "Diego Salazar", "Camila Rojas", "Renato Aguilar",
    "Mariana Silva", "Sebastián Paredes", "Fernanda Ruiz", "Rodrigo Campos", "Daniela Chávez",
    "Alonso Medina", "Natalia Herrera", "Bruno Peña", "Paula Morales", "Gabriel Núñez",
    "Claudia Benavides", "Martín Vera", "Fiorella León", "Ricardo Soto", "Gabriela Navarro"
]

DOMINIOS = ["gmail.com", "outlook.com", "hotmail.com", "cliente.pe", "correo.com"]
CANALES = ["App móvil", "Web", "WhatsApp", "Marketplace", "Otro"]
RESPONSABLES = ["Ana Torres", "Luis Herrera", "María Salas", "Jorge Paredes", "Lucía Salazar"]

PLANTILLAS = {
    "Retraso de pedido": [
        "Mi pedido está demorado y todavía no llega a mi dirección.",
        "El repartidor se retrasó demasiado y la comida llegó fría.",
        "Han pasado más de 60 minutos y sigo esperando mi pedido.",
        "La aplicación indica que el pedido llegaba en 30 minutos pero ya pasó una hora.",
        "El pedido llegó muy tarde y necesito una solución.",
        "El delivery demoró mucho y quiero saber qué ocurrió.",
        "El tiempo estimado cambió varias veces y el pedido no llegó.",
        "La comida llegó fría por la demora del repartidor.",
        "Estoy esperando mi pedido desde hace mucho tiempo.",
        "El pedido aparece en camino pero nunca llega."
    ],
    "Cobro indebido": [
        "Me cobraron dos veces por el mismo pedido.",
        "Tengo un cargo que no reconozco en mi tarjeta.",
        "El monto cobrado es mayor al precio mostrado en la app.",
        "Solicito devolución porque me hicieron un cobro indebido.",
        "Se realizó un cargo adicional sin autorización.",
        "Me descontaron dinero pero el pedido fue cancelado.",
        "El sistema cobró el pedido aunque no se confirmó la compra.",
        "Aparece un cobro duplicado en mi cuenta bancaria.",
        "El pago se procesó dos veces.",
        "Me hicieron un cargo incorrecto por delivery."
    ],
    "Fraude o seguridad": [
        "Alguien hizo un pedido desde mi cuenta sin permiso.",
        "No reconozco una compra realizada con mi usuario.",
        "Creo que mi cuenta fue hackeada.",
        "Detecté actividad sospechosa en mi cuenta.",
        "Hay pedidos que yo no realicé.",
        "Mi cuenta fue usada por otra persona.",
        "Solicito bloqueo por posible fraude.",
        "Recibí notificaciones de pedidos que no hice.",
        "Alguien ingresó a mi cuenta sin autorización.",
        "Quiero reportar un acceso no reconocido."
    ],
    "Producto incompleto": [
        "Mi pedido llegó incompleto y faltan productos.",
        "No vino la bebida incluida en el combo.",
        "Faltan las papas de mi pedido.",
        "El restaurante no envió todos los productos.",
        "Mi orden llegó sin una parte importante.",
        "Pagamos por tres productos y solo llegaron dos.",
        "El combo llegó incompleto.",
        "No recibí todos los artículos solicitados.",
        "Falta un producto en la bolsa.",
        "Mi comida llegó sin los acompañamientos."
    ],
    "Soporte general": [
        "Quiero cambiar mi dirección de entrega.",
        "Necesito ayuda para actualizar mis datos.",
        "Deseo saber cómo cancelar una orden.",
        "Tengo una consulta sobre promociones.",
        "Quiero cambiar mi correo registrado.",
        "Necesito información sobre el uso de la aplicación.",
        "Cómo puedo contactar al repartidor.",
        "Deseo actualizar mi número de teléfono.",
        "Necesito soporte para configurar mi perfil.",
        "Quiero saber cómo usar un cupón."
    ]
}

def correo_para(nombre, idx):
    base = nombre.lower().replace(" ", ".").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    return f"{base}.{idx}@{random.choice(DOMINIOS)}"

def generar_codigo_pedido(idx):
    return f"ORD-2026-{idx:05d}"

def seleccionar_estado_final(categoria):
    if categoria == "Fraude o seguridad":
        return random.choices(["Escalado", "En revisión", "Cerrado"], weights=[45, 35, 20])[0]
    if categoria == "Cobro indebido":
        return random.choices(["Respondido", "En revisión", "Cerrado", "Escalado"], weights=[35, 30, 25, 10])[0]
    if categoria == "Retraso de pedido":
        return random.choices(["Respondido", "Cerrado", "En revisión"], weights=[45, 35, 20])[0]
    if categoria == "Producto incompleto":
        return random.choices(["Respondido", "Cerrado", "En revisión"], weights=[40, 35, 25])[0]
    return random.choices(["Respondido", "Cerrado", "Nuevo", "En revisión"], weights=[40, 30, 20, 10])[0]

def generar_reclamos(cantidad_por_categoria=50, limpiar=False, seed=42):
    random.seed(seed)
    init_db()
    construir_indice_vectorial(forzar=False)

    if limpiar:
        limpiar_datos_prueba()

    existentes = contar_reclamos()
    if existentes > 0 and not limpiar:
        print(f"Ya existen {existentes} reclamos. Use limpiar=True para regenerar desde cero.")
        return existentes

    config = get_configuracion_activa()
    max_docs = int(config["max_documentos_recuperados"]) if config else 3

    total = 0

    for categoria, textos in PLANTILLAS.items():
        for i in range(cantidad_por_categoria):
            idx = total + 1
            nombre = random.choice(NOMBRES)
            correo = correo_para(nombre, idx)
            canal = random.choice(CANALES)
            fecha_pedido = date.today() - timedelta(days=random.randint(0, 45))
            texto_base = random.choice(textos)
            detalle = f"{texto_base} Código de referencia interno {random.randint(1000, 9999)}."

            id_cliente = crear_cliente(nombre, correo)
            id_reclamo = crear_reclamo(
                id_cliente,
                generar_codigo_pedido(idx),
                canal,
                fecha_pedido,
                detalle,
                responsable_asignado=random.choice(RESPONSABLES)
            )

            analisis = clasificar_reclamo(detalle)
            guardar_analisis(id_reclamo, analisis)

            documentos = recuperar_documentos(detalle, analisis["categoria"], max_docs=max_docs)
            respuesta = generar_respuesta_sugerida(nombre, generar_codigo_pedido(idx), detalle, analisis, documentos)
            guardar_respuesta(id_reclamo, respuesta, documentos)

            id_respuesta = obtener_ultimo_id_respuesta(id_reclamo)

            # Comentarios internos
            crear_comentario_agente(
                id_reclamo,
                f"Caso generado para pruebas. Categoría esperada: {categoria}.",
                "INTERNO"
            )

            # Evaluación de calidad para parte de respuestas
            if id_respuesta and random.random() < 0.65:
                crear_evaluacion_respuesta(
                    id_respuesta,
                    claridad=random.randint(3, 5),
                    utilidad=random.randint(3, 5),
                    tono=random.randint(3, 5),
                    fundamentacion=random.randint(3, 5),
                    requiere_mejora=random.choice([0, 0, 0, 1]),
                    observacion="Evaluación simulada para reportes del prototipo."
                )

            # Estado final simulado
            estado = seleccionar_estado_final(categoria)

            if estado == "Respondido":
                aprobar_respuesta(id_respuesta) if id_respuesta else None
                marcar_respondido(id_reclamo, "Caso simulado marcado como respondido.")
            elif estado == "Cerrado":
                aprobar_respuesta(id_respuesta) if id_respuesta else None
                cerrar_reclamo(id_reclamo, "Cerrado", "Caso simulado cerrado para cálculo de tiempo de atención.")
            elif estado == "Escalado":
                escalar_reclamo(id_reclamo, "Caso simulado escalado por criticidad.")
            elif estado == "En revisión":
                actualizar_estado_reclamo(id_reclamo, "En revisión", "Simulación de estado", "Caso simulado pendiente de revisión.")
            elif estado == "Nuevo":
                actualizar_estado_reclamo(id_reclamo, "Nuevo", "Simulación de estado", "Caso simulado dejado como nuevo.")

            total += 1

    registrar_log(
        "Datos de prueba",
        "Generación de reclamos simulados",
        "INFO",
        f"Se generaron {total} reclamos simulados: {cantidad_por_categoria} por categoría.",
        None
    )

    return total

if __name__ == "__main__":
    total = generar_reclamos(cantidad_por_categoria=50, limpiar=True)
    print("SmartClaim AI - Generador de datos de prueba")
    print("=" * 60)
    print(f"Reclamos simulados generados: {total}")
