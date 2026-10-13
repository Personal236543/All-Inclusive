import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
RUTA_ENV = os.path.join(PROJECT_DIR, ".env")


def cargar_env(ruta=RUTA_ENV):
    """Carga variables KEY=VALUE desde .env sin sobrescribir las ya definidas en el entorno."""
    if not os.path.exists(ruta):
        return
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            key, value = linea.split("=", 1)
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)


def get(nombre, default=None):
    return os.environ.get(nombre, default)


def cargar_json(nombre_env, ruta_default):
    """Carga un JSON cuya ruta viene de la variable nombre_env (o ruta_default)."""
    ruta = get(nombre_env, ruta_default)
    if not os.path.isabs(ruta):
        ruta = os.path.join(PROJECT_DIR, ruta)
    if not os.path.exists(ruta):
        return {}
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


cargar_env()
