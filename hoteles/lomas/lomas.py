import os
import json
import csv
import time
import logging
import unicodedata
import script_runner
from datetime import datetime
from hoteles.lomas.lomas_mapping import hotels
from utils import mapping, register1, utils
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import config

#NO EDITAR
CLICK = script_runner.HOTEL_CLICK

SLEEP_TIME = 0 #No menos de 2
TO_PROCESS = 500 #No mas de 70
HEADLESS = False
LOGGING_LEVEL = logging.INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
USERNAME = config.get("LOMAS_USERNAME")
PASSWORD = config.get("LOMAS_PASSWORD")
COMMISSION_RULE = "Lomas"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_JSONS = os.path.join(BASE_DIR, "json", "bookings.json")
RUTA_DONE = os.path.join(BASE_DIR, "json", "done.json")
RUTA_PENDIENTES = os.path.join(BASE_DIR, "json", "pendientes.json")
RUTA_LOGS = os.path.join(BASE_DIR, "logs", "lomas.log")
RUTA_DRIVER = os.path.join(BASE_DIR, os.pardir, "chromedriver.exe")

csv_file_path = os.path.join(BASE_DIR,"lomas.csv")
output_filename = os.path.join(BASE_DIR, "lomas.json")

OVERLAY_COUNTER = 3
HOTELS = hotels

os.makedirs(os.path.dirname(RUTA_JSONS), exist_ok=True)


with open(RUTA_JSONS, "r", encoding="utf-8") as file:
    bookings = json.load(file)

hotels_data = {}


def reformat_date(date_str):
    return datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")
                               
def json_to_csv(bookings, csv_file):
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        # Write headers
        headers = [
            "Reservation Number", "Resevation Date", "Reservation Chanel", "Hotel", "Room Type",
            "Special Ocation", "Guest Name 1", "Guest Name 2", "Adults", "Children",
            "Rooms", "Arival Date", "Arival Time", "Departure Date", "Departure Time","Coments"
        ]
        writer.writerow(headers)

        for booking in bookings:
            try:
                booking_number = booking["Booking Number"]

                campos_obligatorios = [
                    "Booking Number",
                    "Client Name",
                    "Date Entered",
                    "Departure Date",
                    "Supplier",
                    "Destination",
                    "Return Date",
                    "Supplier Price",
                ]

                campos_vacios = [
                    campo for campo in campos_obligatorios
                    if not str(booking[campo] or "").strip()
                ]

                if campos_vacios:
                    msg = (
                        f"Booking {booking_number} tiene campos obligatorios vacíos: "
                        + ", ".join(campos_vacios)
                    )
                    logging.warning(msg)
                    utils.register_pending(RUTA_PENDIENTES, booking["Booking Number"], msg)
                    continue

                if not booking["Passengers"]:
                    msg = f"Booking {booking_number} no tiene pasajeros."
                    logging.warning(msg)
                    utils.register_pending(RUTA_PENDIENTES, booking["Booking Number"], msg)
                    continue

                if not booking["Hotels"]:
                    msg = f"Booking {booking_number} no tiene hoteles."
                    logging.warning(msg)
                    utils.register_pending(RUTA_PENDIENTES, booking["Booking Number"], msg)
                    continue

            except KeyError as e:
                booking_number = booking["Booking Number"] if "Booking Number" in booking else "UNKNOWN"
                msg = f"Booking {booking_number} no tiene la llave obligatoria: {e}"
                logging.warning(msg)
                utils.register_pending(RUTA_PENDIENTES, booking["Booking Number"], msg)
                continue
            hotel = booking["Hotels"][0]
            len_hotels = len(booking["Hotels"])
            guest_1 = booking["Passengers"][0]
            name_2 = ""
            guest_2 = None
            if len(booking["Passengers"]) > 1:
                guest_2 = booking["Passengers"][1]
                name_2 = guest_2["First Name"]+" "+guest_2["Last Name"]
            len_hotels = len(booking["Hotels"])
            num_adults = sum(1 for p in booking['Passengers'] if p['Type'] == 'adult')
            num_children = sum(1 for p in booking['Passengers'] if p['Type'] == 'child')
            json_hotel_name = hotel["Hotel Name"]
            json_room_name = hotel["Room Type"]
            hotel_name, room_name = mapping.map_pair(HOTELS, json_hotel_name, json_room_name)
            if room_name is None:
                msg = f"No se encontró el mapeo para {json_hotel_name} - {json_room_name}"
                logging.warning(msg)
                utils.register_pending(RUTA_PENDIENTES, booking["Booking Number"], msg)
            writer.writerow([
                booking["Booking Number"],
                reformat_date(booking["Date Entered"]),
                "All Inclusive Outlet",
                hotel_name,
                room_name,
                "Vacation",
                guest_1["First Name"]+" "+guest_1["Last Name"],
                name_2,
                num_adults,
                num_children,
                len_hotels,
                reformat_date(booking["Departure Date"]),
                "13:00",
                reformat_date(booking["Return Date"]),
                "15:00",
                "No additional comments"
                
                
            ])
            for hotel in booking.get("Hotels", []):
                hotel_name = hotel["Hotel Name"]
                room_type = hotel["Room Type"]
                if hotel_name not in hotels_data:
                    hotels_data[hotel_name] = []
                if room_type not in hotels_data[hotel_name]:
                    hotels_data[hotel_name].append(room_type)

def main():
    try:
        utils.eliminar_reservas_repetidas_csv(csv_file_path)
        utils.filtrar_bookings_realizados(RUTA_JSONS, RUTA_DONE)
        logging.info("Iniciando convercion a archivo csv...")
        json_to_csv(bookings, csv_file_path)
    except Exception as e:
        logging.critical(f"Algo salió mal :( \nError: {e}")
    
    finally:
        with open(output_filename, "w", encoding="utf-8") as file:
            json.dump(hotels_data, file, indent=4, ensure_ascii=False)
        print(f"CSV file has been saved to {csv_file_path}")
 


if __name__ == "__main__":
    main()