import decimal
import os
import csv
import json
import re
import time
import logging
from utils import mapping, register1,utils
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import script_runner
from utils import config

# https://googlechromelabs.github.io/chrome-for-testing/
CLICK = True

SLEEP_TIME = 0
TO_PROCESS = 500
HEADLESS = False
DEPARTURE_DATE_FROM = "01/01/2025"
DEPARTURE_DATE_TO = "02/28/2025"
RECEIVE_DATE_FROM = "01/01/2025"
RECEIVE_DATE_TO = "02/28/2025"
COMMISSION_RULE = "Travel Impressons"
EJECUTABLE = script_runner.EJECUTABLE
LOGGING_LEVEL = logging.INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
USERNAME = config.get("AIO_USERNAME")
PASSWORD = config.get("AIO_PASSWORD")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_DONE = os.path.join(BASE_DIR, "json", "done.json")
RUTA_PENDIENTES = os.path.join(BASE_DIR, "json", "pendientes.json")
RUTA_LOGS = os.path.join(BASE_DIR, "logs", "vax.log")
RUTA_DRIVER = os.path.join(BASE_DIR, os.pardir, "chromedriver.exe")
RUTA_CSVS = os.path.join(BASE_DIR, "sumaries")



def iniciar_driver():
    options = Options()
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--start-maximized")

    if HEADLESS:
        options.add_argument("--headless")

    options.add_argument("--kiosk-printing")
    options.add_experimental_option(
        "prefs",
        {
            "printing.print_preview_sticky_settings.appState": (
                '{"recentDestinations":[{"id":"Save as PDF","origin":"local",'
                '"account":"","name":"Save as PDF"}],'
                '"selectedDestinationId":"Save as PDF","version":2}'
            ),
        },
    )

    service = Service(executable_path=RUTA_DRIVER)
    driver = webdriver.Chrome(service=service, options=options)

    return driver

def login(driver):
    try:
        logging.info("Iniciando sesión...")
        driver.get("https://tprofile.allinclusiveoutlet.com/admin/commissionreport")
        time.sleep(SLEEP_TIME)

        username_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "MainContent_txtUsername"))
        )
        password_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "MainContent_txtPassword"))
        )
        login_btn = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="MainContent_cmdLogin"]')
            )
        )

        username_field.send_keys(USERNAME)
        password_field.send_keys(PASSWORD)
        time.sleep(SLEEP_TIME)
        login_btn.click()

        booking_search_bar = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "txtSearchAll"))
        )
        logging.info("Inicio de sesión exitoso.")

        return True if booking_search_bar else False
    except Exception as e:
        logging.error(f"Error en login: {e}")
        return False


def search_bookings(driver):
    try:
        logging.info("Buscando bookings...")

        recived_dropdown = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="SearchForm"]/div/div/div[1]/div/div[1]/button')
            )
        )
        recived_dropdown.click()
        yes_option = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    '//*[@id="SearchForm"]/div/div/div[1]/div/div[1]/div/ul/li[2]/a',
                )
            )
        )
        yes_option.click()
        time.sleep(SLEEP_TIME)

        commission_rule_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "ruleName"))
        )
        commission_rule_field.send_keys(COMMISSION_RULE)
        time.sleep(SLEEP_TIME)

        dept_date_from_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "depDateFrom"))
        )
        dept_date_from_field.send_keys(DEPARTURE_DATE_FROM)
        time.sleep(SLEEP_TIME)
        dept_date_to_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "depDateTo"))
        )
        dept_date_to_field.send_keys(DEPARTURE_DATE_TO)
        time.sleep(SLEEP_TIME)
        
        recive_date_from_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "receivedDateFrom"))
        )
        recive_date_from_field.send_keys(RECEIVE_DATE_FROM)
        time.sleep(SLEEP_TIME)
        recive_date_to_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "receivedDateTo"))
        )
        recive_date_to_field.send_keys(RECEIVE_DATE_TO)
        time.sleep(SLEEP_TIME)

        search_btn = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "SubmitButton"))
        )
        search_btn.click()

        booking_table = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="form0"]/table'))
        )
        logging.info("Búsqueda de bookings exitosa.")
        return True if booking_table else False
    except Exception as e:
        logging.error(f"Error en search_bookings: {e}")
        return False
    
def guardar_csvs_actualizados(csv_data):
    """
    Reescribe los CSV con las filas actualizadas en memoria.
    """
    for ruta_archivo, data in csv_data.items():
        fieldnames = data["fieldnames"]
        rows = data["rows"]

        with open(ruta_archivo, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                delimiter=";",
                extrasaction="ignore"
            )

            writer.writeheader()
            writer.writerows(rows)

        logging.info(f"[CSV SAVE] Archivo actualizado: {ruta_archivo}")  
'''    
def cargar_idx_ref_desde_csvs(RUTA_CSVS):
    """
    Lee todos los CSV y devuelve:

    idx_ref:
        {
            booking_no: {
                "commission": commission_str,
                "row": fila_original,
                "archivo": ruta_archivo
            }
        }

    csv_data:
        {
            ruta_archivo: {
                "fieldnames": columnas,
                "rows": filas
            }
        }

    Omite Status == 'd' y 'Sum Total'.
    """

    idx_ref = {}
    csv_data = {}

    def norm(s):
        return (s or "").replace("\xa0", " ").strip()

    for nombre in os.listdir(RUTA_CSVS):
        if not nombre.lower().endswith(".csv"):
            continue

        ruta_archivo = os.path.join(RUTA_CSVS, nombre)

        with open(ruta_archivo, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")

            if not reader.fieldnames:
                continue

            fieldnames = [(h or "").strip() for h in reader.fieldnames]

            if "Status" not in fieldnames:
                fieldnames.append("Status")

            rows = []

            for reader_row in reader:
                row = {}

                for key, value in reader_row.items():
                    if key is not None:
                        row[key.strip()] = value

                res = norm(row.get("Reservation", ""))
                com = norm(row.get("Commission", ""))
                status = norm(row.get("Status", "")).lower()

                # --- SKIPs ---
                if not res or res == "Sum Total":
                    rows.append(row)
                    continue

                if res.lower() == "reservation" or com.lower() == "commission":
                    rows.append(row)
                    continue

                if status == "d":
                    rows.append(row)
                    continue
                # ---------------

                idx_ref[res] = {
                    "commission": com,
                    "row": row,
                    "archivo": ruta_archivo,
                }

                rows.append(row)

            csv_data[ruta_archivo] = {
                "fieldnames": fieldnames,
                "rows": rows,
            }

    return idx_ref, csv_data
'''

def guardar_csv_actualizado(ruta_archivo, fieldnames, rows):
    """
    Reescribe un solo CSV con sus filas actualizadas.
    """

    with open(ruta_archivo, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter=";",
            extrasaction="ignore"
        )

        writer.writeheader()
        writer.writerows(rows)

    logging.info(f"[CSV SAVE] Archivo actualizado: {ruta_archivo}")
    
    
def cargar_idx_ref_desde_csv(ruta_archivo):
    """
    Lee un solo CSV y devuelve:
    - idx_ref: booking -> {"commission": ..., "row": ...}
    - fieldnames: columnas del CSV
    - rows: filas del CSV
    """

    idx_ref = {}

    def norm(s):
        return (s or "").replace("\xa0", " ").strip()

    with open(ruta_archivo, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")

        if not reader.fieldnames:
            return {}, [], []

        fieldnames = [(h or "").strip() for h in reader.fieldnames]

        if "Status" not in fieldnames:
            fieldnames.append("Status")

        rows = []

        for reader_row in reader:
            row = {}

            for key, value in reader_row.items():
                if key is not None:
                    row[key.strip()] = value
            
            if "Status" not in row:
                row["Status"] = ""

            res = norm(row.get("Reservation", ""))
            com = norm(row.get("Commission", ""))
            status = norm(row.get("Status", "")).lower()

            # Mantener la fila en memoria aunque no se procese
            rows.append(row)

            # Saltos
            if not res or res == "Sum Total":
                continue

            if res.lower() == "reservation" or com.lower() == "commission":
                continue

            if status == "d":
                continue

            idx_ref[res] = {
                "commission": com,
                "row": row,
            }

    return idx_ref, fieldnames, rows

'''
def cargar_idx_ref_desde_csvs(RUTA_CSVS):
    """
    Devuelve dict: { booking_no: commission_str }
    Omite Status == 'd' y 'Sum Total'.
    Si un booking aparece repetido, la última aparición sobrescribe.
    """
    idx = {}
    reg = {}
    def norm(s): return (s or "").replace("\xa0", " ").strip()
    for nombre in os.listdir(RUTA_CSVS):
        if not nombre.lower().endswith(".csv"):
            continue
        with open(os.path.join(RUTA_CSVS, nombre), "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            if not reader.fieldnames:
                continue
            # mapa case-insensitive de encabezados a su nombre real (stripped)
            headers_real = [(h or "").strip() for h in reader.fieldnames]
            hmap = {h.lower(): h for h in headers_real}
            def get_ci(row, col):
                real = hmap.get(col.lower())
                return norm(row.get(real, "")) if real else ""
            for reader_row in reader:
                res = get_ci(reader_row, "Reservation")
                com = get_ci(reader_row, "Commission")
                date = get_ci(reader_row, "Date")
                contact = get_ci(reader_row, "Contact")
                traveler = get_ci(reader_row, "Traveler Name")
                status = get_ci(reader_row, "Status").lower()
                # --- SKIPs ---
                # filas vacías o totales
                if not res or res == "Sum Total":
                    continue
                # cabecera intermedia (con o sin espacio final en Commission)
                if res.lower() == "reservation" or com.lower() == "commission":
                    continue
                # marcadas como 'done'
                if status == "d":
                    continue
                # ---------------
                idx[res] = com  # sobrescribe si repetido
                reg[res] = [res, com, date, contact, traveler, status]

    return idx, reg

'''

def procesar_csvs_uno_por_uno():
    """
    Recorre cada CSV de RUTA_CSVS.
    Para cada archivo:
    - abre un driver nuevo
    - hace login
    - busca bookings
    - procesa solo ese CSV
    - guarda ese CSV
    - cierra el driver
    """

    for nombre_archivo in os.listdir(RUTA_CSVS):
        if not nombre_archivo.lower().endswith(".csv"):
            continue

        ruta_archivo = os.path.join(RUTA_CSVS, nombre_archivo)

        logging.info(f"[CSV START] Procesando archivo: {nombre_archivo}")

        driver = None

        try:
            idx_ref, fieldnames, rows = cargar_idx_ref_desde_csv(ruta_archivo)

            if not idx_ref:
                logging.info(f"[CSV SKIP] No hay bookings pendientes en {nombre_archivo}")
                continue

            logging.info("[DRIVER] Iniciando driver desde cero...")
            driver = iniciar_driver()

            logged = login(driver)

            if not logged:
                logging.error(f"[CSV ERROR] No se pudo iniciar sesión para {nombre_archivo}")
                continue

            ready_to_search = search_bookings(driver)

            if not ready_to_search:
                logging.error(f"[CSV ERROR] No se pudo buscar bookings para {nombre_archivo}")
                continue

            scrapped = comparar_vax(driver, idx_ref)

            if scrapped:
                guardar_csv_actualizado(ruta_archivo, fieldnames, rows)
                logging.info(f"[CSV DONE] Archivo terminado: {nombre_archivo}")
            else:
                logging.warning(f"[CSV WARNING] No se terminó correctamente: {nombre_archivo}")

            logout(driver)

        except PermissionError:
            logging.error(
                f"[CSV ERROR] No se pudo leer/escribir {nombre_archivo}. "
                f"Cierra el archivo en Excel o espera a que OneDrive lo libere."
            )

        except Exception as e:
            logging.error(f"[CSV ERROR] Error procesando {nombre_archivo}: {repr(e)}")

        finally:
            if driver is not None:
                try:
                    driver.quit()
                    logging.info("[DRIVER] Driver cerrado correctamente.")
                except Exception as e:
                    logging.warning(f"[DRIVER] No se pudo cerrar el driver: {repr(e)}")

def comparar_vax(driver, idx_ref):
    """
    Recorre la tabla web filtrada por Received = Yes.

    Si encuentra un booking del CSV en la tabla web y la comisión coincide,
    marca Status = 'd' en la fila del CSV.

    No hace click en checkbox.
    No hace click en btnReceive.
    No modifica nada en la página.
    """
    try:
        logging.info("Iniciando comparación de bookings ya recibidos...")

        booking_table = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="form0"]/table'))
        )

        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "tr"))
        )

        rows = booking_table.find_elements(By.TAG_NAME, "tr")
        total_rows = len(rows) - 1

        logging.info(f"Total de filas en tabla web: {total_rows}")
        logging.info(f"Total de bookings pendientes en CSV: {len(idx_ref)}")

        i = 1
        procesados = 0
        encontrados_en_web = 0
        marcados_d = 0
        mismatches = 0
        errores_decimal = 0

        bookings_encontrados = set()

        while i < len(rows) and procesados < TO_PROCESS:
            row = rows[i]
            time.sleep(SLEEP_TIME)

            cells = row.find_elements(By.TAG_NAME, "td")

            if not cells:
                i += 1
                continue

            try:
                booking_link = cells[11].find_element(By.TAG_NAME, "a")
                booking_no = (
                    booking_link.text or ""
                ).replace("\xa0", " ").strip()
            except Exception:
                booking_no = ""

            if not booking_no:
                i += 1
                procesados += 1
                continue

            try:
                commission_input = row.find_element(
                    By.CSS_SELECTOR,
                    "input[id^='CommissionItems_'][id$='__Amount']"
                )

                commission_str_web = (
                    commission_input.get_attribute("value") or ""
                ).replace("\xa0", " ").strip()

            except Exception as e:
                logging.warning(
                    f"[SKIP] No se pudo leer comisión web para booking={booking_no}: {repr(e)}"
                )
                i += 1
                procesados += 1
                continue

            logging.info(
                f"Fila {i}: booking={booking_no} | commission_web='{commission_str_web}'"
            )

            if booking_no in idx_ref:
                encontrados_en_web += 1
                bookings_encontrados.add(booking_no)

                commission_ref = idx_ref[booking_no]["commission"]

                logging.info(
                    f"[FOUND] booking={booking_no} encontrado en web y CSV. "
                    f"commission_web={commission_str_web} | commission_ref={commission_ref}"
                )

                try:
                    commission_web_decimal = decimal.Decimal(
                        commission_str_web.replace(",", ".")
                    )

                    commission_ref_decimal = decimal.Decimal(
                        commission_ref.replace(",", ".")
                    )

                    if commission_web_decimal == commission_ref_decimal:
                        idx_ref[booking_no]["row"]["Status"] = "d"
                        marcados_d += 1

                        logging.info(
                            f"[DONE CSV] booking={booking_no} marcado como Status='d'"
                        )

                    else:
                        mismatches += 1
                        msg = (
                            f"[MISMATCH] booking={booking_no} "
                            f"commission_web={commission_str_web} != commission_ref={commission_ref}"
                        )
                        logging.warning(msg)
                        #utils.register_pending(RUTA_PENDIENTES, booking_no, msg)

                except decimal.InvalidOperation as e:
                    errores_decimal += 1
                    msg = (
                        f"[DECIMAL ERROR] booking={booking_no} "
                        f"commission_web={commission_str_web} "
                        f"commission_ref={commission_ref} "
                        f"error={repr(e)}"
                    )
                    logging.warning(msg)
                    #utils.register_pending(RUTA_PENDIENTES, booking_no, msg)

            i += 1
            procesados += 1

        no_encontrados = set(idx_ref.keys()) - bookings_encontrados

        logging.info("========== RESUMEN COMPARACIÓN ==========")
        logging.info(f"Bookings pendientes en CSV: {len(idx_ref)}")
        logging.info(f"Filas procesadas de la tabla web: {procesados}")
        logging.info(f"Bookings del CSV encontrados en web: {encontrados_en_web}")
        logging.info(f"Bookings marcados con Status='d': {marcados_d}")
        logging.info(f"Mismatches de comisión: {mismatches}")
        logging.info(f"Errores de conversión decimal: {errores_decimal}")
        logging.info(f"Bookings del CSV no encontrados en web: {len(no_encontrados)}")

        if no_encontrados:
            logging.info(
                "[NO ENCONTRADOS] "
                + ", ".join(sorted(no_encontrados))
            )

        logging.info("=========================================")

        return True

    except Exception as e:
        logging.error(f"Error en comparar_vax: {e}")
        return False


def logout(driver):
    try:
        logging.info("Cerrando sesión...")
        logout_btn = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, "/html/body/div[2]/div/div[2]/ul/li[6]/a")
            )
        )
        time.sleep(SLEEP_TIME)
        logout_btn.click()
        logging.info("Sesión cerrada correctamente.")
        time.sleep(SLEEP_TIME)
        return True
    except Exception as e:
        logging.error(f"Error en logout: {e}")
        return False
    
def main():
    try:
        logging.basicConfig(
            level=LOGGING_LEVEL,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(RUTA_LOGS), logging.StreamHandler()],
        )

        logging.info("Iniciando procesamiento de CSVs...")
        procesar_csvs_uno_por_uno()
        logging.info("Procesamiento completado.")

    except Exception as e:
        logging.critical(f"Algo salió mal :( \nError: {e}")


if __name__ == "__main__":
    main()
