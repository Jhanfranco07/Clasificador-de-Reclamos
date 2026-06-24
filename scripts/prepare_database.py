from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from database.db_connection import init_db
from database.repositories import (
    asegurar_pedidos_demo_base,
    asegurar_usuarios_auth_base,
    importar_dataset_entrenamiento_desde_csv,
    obtener_metricas_bd,
    registrar_log,
)

def main():
    init_db()
    asegurar_usuarios_auth_base()
    asegurar_pedidos_demo_base()
    total_dataset = importar_dataset_entrenamiento_desde_csv()
    registrar_log("Base de datos", "Migración ejecutada", "INFO", "Se ejecutó la preparación de base de datos fortalecida.", None)

    print("SmartClaim AI - Preparación de base de datos fortalecida")
    print("=" * 70)
    print(f"Dataset de entrenamiento en SQLite: {total_dataset} registros")
    print("")
    print("Registros por tabla:")
    for item in obtener_metricas_bd():
        print(f"- {item['tabla']}: {item['registros']}")

if __name__ == "__main__":
    main()
