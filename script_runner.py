# from karisma import karisma
import csv
import datetime
import importlib
import os


EJECUTABLE = "karisma"
#CSVMODE = True

try:
    import all_inclusive.all_inclusive as all_inclusive
except ModuleNotFoundError:
    import all_inclusive as all_inclusive
import vax.vax as vax
import vax.vax2 as vax2
import utils.clear_runs as clear_runs
import utils.act as act
from utils import config


# https://googlechromelabs.github.io/chrome-for-testing/

EJECUTABLE_CLEAR_JSONS = False
EJECUTABLE_CLEAR_LOGS = True
EJECUTABLE_CLEAR_INVOICES = True

LIMPIAR_BOOKINGS_PROCESADOS = True
SOLO_LIMPIAR_BOOKINGS_PROCESADOS = True
HOTEL_A_LIMPIAR = EJECUTABLE

SEND_CONFIRMATION = False
CORRER_EJECUTABLE = False

ALL_INCLUSIVE_CLEAR_JSONS = False
ALL_INCLUSIVE_CLEAR_LOGS = False

ALL_INCLUSIVE_CLICK = True
ALL_INCLUSIVE_SLEEP_TIME = 0
ALL_INCLUSIVE_TO_PROCESS = 10000
ALL_INCLUSIVE_DEPARTURE_DATE_FROM = "06/30/2026"
ALL_INCLUSIVE_DEPARTURE_DATE_TO = "07/31/2026"
VAX_RECEIVE_DATE_FROM = "05/06/2026"
VAX_RECEIVE_DATE_TO = "05/08/2026"
ALL_INCLUSIVE_COMMISSION_RULE = "default"
ALL_INCLUSIVE_USERNAME = config.get("AIO_USERNAME")
ALL_INCLUSIVE_PASSWORD = config.get("AIO_PASSWORD")

HOTEL_CLICK = True
HOTEL_SLEEP_TIME = 2 #No menos de 2
HOTEL_TO_PROCESS = 0 #No mas de 70


LOG_CSV_FILE = "script_execution_log.csv"

def main():
    execution_date = datetime.datetime.now().strftime("%Y-%m-%d")
    start_time = datetime.datetime.now().strftime("%H:%M:%S")

    all_inclusive_bookings = 0
    hotel_bookings = 0
    if EJECUTABLE == "vax":
        executable_module = importlib.import_module(f"{EJECUTABLE}.{EJECUTABLE}")
        vax.CLICK = ALL_INCLUSIVE_CLICK
        vax.SLEEP_TIME = ALL_INCLUSIVE_SLEEP_TIME
        vax.TO_PROCESS = ALL_INCLUSIVE_TO_PROCESS
        vax.DEPARTURE_DATE_FROM = ALL_INCLUSIVE_DEPARTURE_DATE_FROM
        vax.DEPARTURE_DATE_TO = ALL_INCLUSIVE_DEPARTURE_DATE_TO
        vax.main()
    elif EJECUTABLE == "vax2":
        executable_module = importlib.import_module(f"vax.{EJECUTABLE}")
        vax2.CLICK = ALL_INCLUSIVE_CLICK
        vax2.SLEEP_TIME = ALL_INCLUSIVE_SLEEP_TIME
        vax2.TO_PROCESS = ALL_INCLUSIVE_TO_PROCESS
        vax2.DEPARTURE_DATE_FROM = ALL_INCLUSIVE_DEPARTURE_DATE_FROM
        vax2.DEPARTURE_DATE_TO = ALL_INCLUSIVE_DEPARTURE_DATE_TO
        vax2.RECEIVE_DATE_FROM = VAX_RECEIVE_DATE_FROM
        vax2.RECEIVE_DATE_TO = VAX_RECEIVE_DATE_TO
        vax2.main()
    else: 
        executable_module = importlib.import_module(f"hoteles.{EJECUTABLE}.{EJECUTABLE}")
        ALL_INCLUSIVE_COMMISSION_RULE = executable_module.COMMISSION_RULE
        clear_runs.EJECUTABLE = EJECUTABLE
        clear_runs.ALL_INCLUSIVE_CLEAR_JSONS = ALL_INCLUSIVE_CLEAR_JSONS
        clear_runs.ALL_INCLUSIVE_CLEAR_LOGS = ALL_INCLUSIVE_CLEAR_LOGS
        
        clear_runs.CLEAR_JSONS = EJECUTABLE_CLEAR_JSONS
        clear_runs.CLEAR_LOGS = EJECUTABLE_CLEAR_LOGS
        clear_runs.CLEAR_INVOICES = EJECUTABLE_CLEAR_INVOICES
        clear_runs.main()
        
        #all_inclusive.EJECUTABLE = EJECUTABLE
        all_inclusive.CLICK = ALL_INCLUSIVE_CLICK
        all_inclusive.SLEEP_TIME = ALL_INCLUSIVE_SLEEP_TIME
        all_inclusive.TO_PROCESS = ALL_INCLUSIVE_TO_PROCESS
        all_inclusive.DEPARTURE_DATE_FROM = ALL_INCLUSIVE_DEPARTURE_DATE_FROM
        all_inclusive.DEPARTURE_DATE_TO = ALL_INCLUSIVE_DEPARTURE_DATE_TO
        all_inclusive.COMMISSION_RULE = ALL_INCLUSIVE_COMMISSION_RULE
     
    #all_inclusive.USERNAME = ALL_INCLUSIVE_USERNAME
    #all_inclusive.PASSWORD = ALL_INCLUSIVE_PASSWORD
    if EJECUTABLE != "vax":
        all_inclusive.main()
     
     
        executable_module.CLICK = HOTEL_CLICK
        executable_module.SLEEP_TIME = HOTEL_SLEEP_TIME
        executable_module.TO_PROCESS = HOTEL_TO_PROCESS
    #executable_module.USERNAME = HOTEL_USERNAME
    #executable_module.PASSWORD = HOTEL_PASSWORD
    if CORRER_EJECUTABLE == True:
        if hasattr(executable_module, "main"):
            
            #hotel_bookings = executable_module.main()
            executable_module.main()
    if SEND_CONFIRMATION == True:    
          send_whatsapp()
    if LIMPIAR_BOOKINGS_PROCESADOS:
        act.EJECUTABLE = EJECUTABLE
        act.main()
    # Registrar hora de finalización
    end_time = datetime.datetime.now().strftime("%H:%M:%S")
     
    # Total de bookings procesados
    total_bookings = all_inclusive_bookings + hotel_bookings
     
    # Guardar el registro en CSV
    log_execution(execution_date, start_time, end_time, total_bookings)


def send_whatsapp():
     TWILIO_SID = config.get("TWILIO_SID")
     TWILIO_AUTH_TOKEN = config.get("TWILIO_AUTH_TOKEN")
     WHATSAPP_FROM = config.get("WHATSAPP_FROM")  # Número de Twilio para WhatsApp
     WHATSAPP_TO = config.get("WHATSAPP_TO")
     MSG = "Ejecucición completada 👍"

     from twilio.rest import Client
     client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
     client.messages.create(from_=WHATSAPP_FROM, body=MSG, to=f"whatsapp:{WHATSAPP_TO}")


def log_execution(execution_date, start_time, end_time, total_bookings):
    """
    Guarda los detalles de la ejecución en un archivo CSV
    """
    file_exists = os.path.isfile(LOG_CSV_FILE)
    
    with open(LOG_CSV_FILE, 'a', newline='') as csvfile:
        fieldnames = ['Fecha', 'Hora_Inicio', 'Hora_Fin', 'Bookings_Procesados','Hotel_Processado', 'Fecha_inicio_ejecucion', 'Fecha_fin_ejecucion']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Escribir encabezados si el archivo no existe
        if not file_exists:
            writer.writeheader()
        
        # Escribir los datos de esta ejecución
        writer.writerow({
            'Fecha': execution_date,
            'Hora_Inicio': start_time,
            'Hora_Fin': end_time,
            'Bookings_Procesados': total_bookings,
            'Hotel_Processado': EJECUTABLE,
            'Fecha_inicio_ejecucion': ALL_INCLUSIVE_DEPARTURE_DATE_FROM,
            'Fecha_fin_ejecucion': ALL_INCLUSIVE_DEPARTURE_DATE_TO
        })
    
    print(f"Registro guardado en {LOG_CSV_FILE}")

     
if __name__ == "__main__":
    main()