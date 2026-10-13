import os
import json
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RUTA_BOOKINGS = os.path.join(BASE_DIR, "json", "bookings.json")
RUTA_DONE = os.path.join(BASE_DIR, "json", "done.json")


def cargar_json_lista(ruta):
    if not os.path.exists(ruta):
        print(f"❌ No existe el archivo: {ruta}")
        return []

    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"El archivo debe contener una lista: {ruta}")

    return data


def obtener_booking_number(item):
    """
    Soporta dos formatos posibles en done.json:

    1. Booking completo:
       {
           "Booking Number": "12345",
           ...
       }

    2. Pendiente/done tipo diccionario simple:
       {
           "12345": "mensaje"
       }
    """

    if isinstance(item, str):
        return item.strip()

    if isinstance(item, dict):
        if "Booking Number" in item:
            return str(item["Booking Number"]).strip()

        if len(item) == 1:
            return str(list(item.keys())[0]).strip()

    return None


def crear_backup(ruta):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = ruta.replace(".json", f"_backup_{timestamp}.json")
    shutil.copy2(ruta, backup_path)
    return backup_path


def main():
    bookings = cargar_json_lista(RUTA_BOOKINGS)
    print(f"📂 Bookings en bookings.json: {len(bookings)}")
    done = cargar_json_lista(RUTA_DONE)
    print(f"📂 Bookings en done.json: {len(done)}")

    done_numbers = set()

    for item in done:
        booking_number = obtener_booking_number(item)

        if booking_number:
            done_numbers.add(booking_number)

    print(f"📌 Bookings originales: {len(bookings)}")
    print(f"✅ Bookings en done.json: {len(done_numbers)}")

    bookings_restantes = []

    for booking in bookings:
        booking_number = str(booking["Booking Number"]).strip()

        if booking_number not in done_numbers:
            bookings_restantes.append(booking)

    removidos = len(bookings) - len(bookings_restantes)

    backup_path = crear_backup(RUTA_BOOKINGS)

    with open(RUTA_BOOKINGS, "w", encoding="utf-8") as f:
        json.dump(bookings_restantes, f, indent=4, ensure_ascii=False)

    print(f"🧾 Backup creado: {backup_path}")
    print(f"🗑️ Bookings removidos de bookings.json: {removidos}")
    print(f"📂 Bookings restantes en bookings.json: {len(bookings_restantes)}")


if __name__ == "__main__":
    main()
