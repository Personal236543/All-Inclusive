import pandas as pd
import json
import os
import json
import csv
import time
import logging
import unicodedata
import script_runner
from datetime import datetime
from lomas.lomas_mapping import hotels
from utils import mapping, register1
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
RUTA_JSONS = os.path.join(BASE_DIR, os.pardir, "json", "bookings.json")
RUTA_DONE = os.path.join(BASE_DIR, os.pardir, "json", "lomas_done.json")
RUTA_PENDIENTES = os.path.join(BASE_DIR, os.pardir, "json", "lomas_pendientes.json")
RUTA_LOGS = os.path.join(BASE_DIR, os.pardir, "logs", "lomas.log")
RUTA_DRIVER = os.path.join(BASE_DIR, os.pardir, "chromedriver.exe")
csv_file_path = os.path.join(BASE_DIR,"lomas.csv")
output_filename = os.path.join(BASE_DIR, "lomas.json")

OVERLAY_COUNTER = 3
HOTELS = hotels

os.makedirs(os.path.dirname(RUTA_JSONS), exist_ok=True)



# Definir los nombres de las columnas según lo proporcionado
column_names = [
    "Booking Number", "Status", "Customer Name", "Customer Email", "Book Date", 
    "Arrival Date", "Departure Date", "Destination Code", "Resort Name", "Room Category", 
    "Nights", "Room Nights", "# Rooms", "Passengers", "Adults", "Children", 
    "Value Add Package 1", "Value Add Package 2", "Karisma Registered", "EMAILED TO PAX?", "Completed"
]

# Cargar el archivo CSV sin encabezados y agregar los títulos
df = pd.read_csv("archivo.csv", header=None, names=column_names)

# Transformar los datos en el formato JSON requerido
json_data = []

for _, row in df.iterrows():
    booking = {
        "Booking Number": row["Booking Number"],
        "Client Name": row["Customer Name"] if pd.notna(row["Customer Name"]) else "Unknown",
        "Date Entered": row["Book Date"],
        "Departure Date": row["Arrival Date"],
        "Supplier": "Travel Impressions",  # Valor fijo según el ejemplo
        "Destination": f"Riviera Maya, Mexico ({row['Destination Code']})",
        "Return Date": row["Departure Date"],
        "Supplier Price": "N/A",  # No está en los datos originales, se puede modificar
        "Passengers": [],
        "Hotels": [
            {
                "Hotel Name": row["Resort Name"],
                "Room Type": row["Room Category"].upper(),
                "Duration": str(row["Nights"])
            }
        ],
        "Airline": "American Airlines"  # Valor fijo según el ejemplo
    }

    # Generar los pasajeros
    for _ in range(int(row["Adults"])):
        booking["Passengers"].append({
            "First Name": "Unknown",
            "Last Name": "Unknown",
            "Age": "Adult",
            "Type": "adult"
        })

    for _ in range(int(row["Children"])):
        booking["Passengers"].append({
            "First Name": "Unknown",
            "Last Name": "Unknown",
            "Age": "Child",
            "Type": "child"
        })

    json_data.append(booking)

# Guardar como archivo JSON
with open("reservas.json", "w") as json_file:
    json.dump(json_data, json_file, indent=4)

print("Transformación completa. Archivo 'reservas.json' generado.")
