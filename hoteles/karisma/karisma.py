import os
import json
import time
import logging
import unicodedata
from hoteles.karisma.karisma_mapping import hotels
from utils import mapping, utils
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from datetime import datetime
import script_runner as sr
from utils import config

# https://googlechromelabs.github.io/chrome-for-testing/
CLICK = True

SLEEP_TIME = 2 #No menos de 2
TO_PROCESS = 100 #No mas de 70
HEADLESS = False
LOGGING_LEVEL = logging.INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
USERNAME = config.get("KARISMA_USERNAME")
PASSWORD = config.get("KARISMA_PASSWORD")
COMMISSION_RULE = "Karisma free nights"

EJECUTABLE = sr.EJECUTABLE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_JSONS = os.path.join(BASE_DIR, "json", "bookings.json")
RUTA_DONE = os.path.join(BASE_DIR, "json", "done.json")
RUTA_PENDIENTES = os.path.join(BASE_DIR, "json", "pendientes.json")
RUTA_LOGS = os.path.join(BASE_DIR, "logs", "karisma.log")
RUTA_DRIVER = os.path.abspath(os.path.join(BASE_DIR, "../../chromedriver.exe"))

OVERLAY_COUNTER = 3
HOTELS = hotels

os.makedirs(os.path.dirname(RUTA_JSONS), exist_ok=True)


def login(driver):
    try:
        logging.info("Iniciando sesion...")
        driver.get("https://www.karismatravelagents.com/en_US/login")
        time.sleep(SLEEP_TIME)
        try:
            cookie_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="cookiesButton"]')))
            cookie_button.click()
            logging.info("Cookies aceptadas.")
        except:
            logging.warning("Boton de cookies no aparecio o no fue clickeable.")
        time.sleep(1)
        username_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="all-container"]/app-login/div/div/form/div/div[1]/input',)))
        password_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "password")))
        time.sleep(SLEEP_TIME)

        username_field.send_keys(USERNAME)
        password_field.send_keys(PASSWORD + Keys.ENTER)

        register_bookings = WebDriverWait(driver, 540).until(EC.presence_of_element_located((By.ID, "bookings-title")))
        logging.info("Inicio de sesion exitoso.")
        time.sleep(SLEEP_TIME)
        return True if register_bookings else False
    except Exception as e:
        logging.error(f"Error en login: {e}")
        return False

def open_register_bookings_form(driver):
    try:
        register_bookings_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "bookings-title")))

        driver.execute_script(
            """
            const viewportHeight = window.innerHeight;
            const targetOffsetTop = arguments[0].getBoundingClientRect().top + window.scrollY;
            window.scrollTo({ top: targetOffsetTop - viewportHeight * 0.25 });
            """,
            register_bookings_btn,
        )

        time.sleep(SLEEP_TIME)
        register_bookings_btn.click()

        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.TAG_NAME, "input")))

        time.sleep(SLEEP_TIME)
        logging.info("Formulario de registro abierto.")
        return True

    except Exception as e:
        logging.error(f"No se pudo abrir el formulario de registro: {e}")
        return False

def register_bookings(driver):
    try:
        logging.info("Registrando bookings...")

        if not open_register_bookings_form(driver):
            return False

        bookings = []
        with open(RUTA_JSONS, "r", encoding="utf-8") as file:
            bookings = json.load(file)

        today = datetime.now().date()
        i = 0
        while (i < TO_PROCESS) and (i < len(bookings)):
            booking = bookings[i]
            departure_date_str = booking["Departure Date"]
            try:
                departure_date = datetime.strptime(departure_date_str, "%m/%d/%Y").date()
                logging.debug(f"Fecha de salida del booking {booking['Booking Number']}: {departure_date}")
                logging.debug(f"Fecha actual: {today}")
            except ValueError as e:
                msg = f"Error al convertir la fecha de salida: {departure_date_str} en el booking {booking['Booking Number']}: {e}"
                logging.error(msg)
                utils.register_pending(RUTA_PENDIENTES,booking['Booking Number'],msg)
                i += 1
                logging.debug(f"Incrementando i a {i} después de error de fecha.")
                continue

            if today >= departure_date:
                msg = f"La fecha de hoy ({today}) es posterior a la fecha de salida ({departure_date}) para el booking {booking['Booking Number']}. Registrando como pendiente."
                logging.info(msg)
                utils.register_pending(RUTA_PENDIENTES,booking['Booking Number'],msg)
                i += 1
                logging.debug(f"Incrementando i a {i} después de registrar como pendiente.")
                continue
            else:
                skip_booking = False
                for h in bookings[i]["Hotels"]:
                    hotel, room = mapping.map_pair(HOTELS, h["Hotel Name"], h["Room Type"])
                    if hotel is None or room is None:
                        msg = f"No se encontro el mapeo para {h['Hotel Name']} - {h['Room Type']}"
                        logging.warning(msg)
                        utils.register_pending(RUTA_PENDIENTES,bookings[i]['Booking Number'],msg)
                        skip_booking = True
                        break
                if skip_booking:
                    open_register_bookings_form(driver)
                    i += 1
                    continue
                
                registered = register_booking(driver, bookings[i])
                if not registered:
                    msg = f"No se pudo registrar el booking: {bookings[i]}"
                    logging.warning(msg)
                    utils.register_pending(RUTA_PENDIENTES,bookings[i]['Booking Number'],msg )
                    open_register_bookings_form(driver)
                    i += 1
                    continue
                i += 1

        logging.info("Registro de bookings exitoso.")
        return True
    except Exception as e:
        logging.error(f"Error en register_bookings: {e}")
        return False


def register_booking(driver, booking):
    try:
        logging.info(f"Registrando booking: {booking}...")

        json_hotels = booking["Hotels"]
        json_passengers = booking["Passengers"]
        passegers_per_room = len(json_passengers) // len(json_hotels)
        remaining = len(json_passengers) % len(json_hotels)
        for i, hotel in enumerate(json_hotels):
            start = i * passegers_per_room + min(i, remaining)
            end = start + passegers_per_room + (1 if i < remaining else 0)

            success = enter_booking_data(driver, booking, hotel, start, end)

            if not success:
                logging.warning(
                    f"No se pudo registrar la habitacion {i + 1} del booking {booking['Booking Number']}"
                )
                return False

        return True
    except Exception as e:
        logging.error(f"Error en register_booking: {e}")
        return False


def enter_booking_data(driver, booking, hotel, start, end):
    try:
        global OVERLAY_COUNTER
        logging.info(f'Ingresando datos del booking: {booking["Booking Number"]}...')
        confirmation_no_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="sbooking-step1-holder"]/form/div[1]/div[4]/input')))
        confirmation_no_field.send_keys(booking["Booking Number"])
        booking_date_month, booking_date_day, booking_date_year = booking["Date Entered"].split("/")
        booking_date = f"{booking_date_year}/{booking_date_month}/{booking_date_day}"
        booking_date_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="sbooking-step1-holder"]/form/div[1]/div[3]/nz-date-picker/nz-picker/span/input',)))
        booking_date_field.click()
        booking_date_input = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,f'//*[@id="cdk-overlay-{OVERLAY_COUNTER}"]/div/date-range-popup/div/div/div/calendar-input/div/div/input',)))
        OVERLAY_COUNTER += 1
        booking_date_input.send_keys(booking_date)

        arrival_date_month, arrival_date_day, arrival_date_year = booking["Departure Date"].split("/")
        arrival_date = f"{arrival_date_year}/{arrival_date_month}/{arrival_date_day}"
        arrival_date_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="sbooking-step1-holder"]/form/div[1]/div[1]/nz-date-picker/nz-picker/span/input',)))
        arrival_date_field.click()
        arrival_date_input = WebDriverWait(driver, 20).until( EC.presence_of_element_located((By.XPATH,f'//*[@id="cdk-overlay-{OVERLAY_COUNTER}"]/div/date-range-popup/div/div/div/calendar-input/div/div/input',)))
        OVERLAY_COUNTER += 1
        arrival_date_input.send_keys(arrival_date)

        departure_date_month, departure_date_day, departure_date_year = booking["Return Date"].split("/")
        return_date = (f"{departure_date_year}/{departure_date_month}/{departure_date_day}")
        departure_date_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="sbooking-step1-holder"]/form/div[1]/div[2]/nz-date-picker/nz-picker/span/input',)))
        departure_date_field.click()
        departure_date_input = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,f'//*[@id="cdk-overlay-{OVERLAY_COUNTER}"]/div/date-range-popup/div/div/div/calendar-input/div/div/input',)))
        OVERLAY_COUNTER += 4
        departure_date_input.clear()
        departure_date_input.send_keys(return_date)

        tour_operator_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="sbooking-step1-holder"]/form/div[2]/div[1]/nz-select/div/div/div[2]/div/input',)))
        # tour_operator_field.send_keys("  " + Keys.BACK_SPACE + Keys.BACK_SPACE + booking["Supplier"] + Keys.ENTER)
        cadena = "  " + Keys.BACK_SPACE + booking["Supplier"] + Keys.ENTER
        for letter in cadena:
            tour_operator_field.send_keys(letter)
            time.sleep(0.1)
        time.sleep(SLEEP_TIME)

        hotel_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="sbooking-step1-holder"]/form/div[2]/div[2]/nz-select/div/div/div[2]/div/input',)))
        room_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="sbooking-step1-holder"]/form/div[2]/div[3]/nz-select/div/div/div[2]/div/input',)))
        
        json_hotel_name = hotel["Hotel Name"]
        json_room_name = hotel["Room Type"]
        hotel_name, room_name = mapping.map_pair(HOTELS, json_hotel_name, json_room_name)
        if room_name is None:
            msg =  f"No se encontro el mapeo para {json_hotel_name} - {json_room_name}"
            logging.warning(msg)
            utils.register_pending(RUTA_PENDIENTES,booking['Booking Number'],msg)
            return False
        hotel_field.send_keys("  " + Keys.BACK_SPACE + hotel_name + Keys.ENTER)
        time.sleep(SLEEP_TIME)
        room_field.send_keys("  " + Keys.BACK_SPACE + room_name + Keys.ENTER)
        time.sleep(SLEEP_TIME)

        first_next_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="card"]/div[2]/app-register-single-booking/div/div[2]/div/button',)))
        driver.execute_script("arguments[0].click()", first_next_btn)
        # first_next_btn.click()
        logging.info(f'Datos del booking: {booking["Booking Number"]} ingresados correctamente.')

        entered_passengers = enter_passengers_data(driver, booking, start, end)

        return True if entered_passengers else False
    except Exception as e:
        logging.error(f"Error en enter_booking_data: {e}")
        try:
            open_register_bookings_form(driver)
        except Exception as form_error:
            logging.error(f"No se pudo reabrir formulario después del error: {form_error}")
        return False


def enter_passengers_data(driver, booking, start, end):
    try:
        logging.info(
            f'Ingresando pasajeros del booking: {booking["Booking Number"]}...'
        )
        global OVERLAY_COUNTER
        num_adults = 0
        num_children = 0
        guest_1 = None
        guest_2 = None
        i = start
        while i < end:
            if i == start:
                guest_1 = booking["Passengers"][i]
            elif i == end - 1:
                guest_2 = booking["Passengers"][i]
            if utils.normalize_string(booking["Passengers"][i]["Age"]) == utils.normalize_string(
                "Adult"
            ):
                num_adults += 1
            else:
                num_children += 1
            i += 1

        g1_first_name_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="sbooking-step2-holder"]/form/div/div[1]/div[1]/div[1]/div/input',)))
        g1_last_name_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="sbooking-step2-holder"]/form/div/div[1]/div[1]/div[2]/div/input',)))
        
        g2_first_name_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="sbooking-step2-holder"]/form/div/div[1]/div[2]/div[1]/div/input',)))
        g2_last_name_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="sbooking-step2-holder"]/form/div/div[1]/div[2]/div[2]/div/input',)))

        g1_first_name_field.send_keys(guest_1["First Name"])
        time.sleep(SLEEP_TIME)
        g1_last_name_field.send_keys(guest_1["Last Name"])
        time.sleep(SLEEP_TIME)
        if guest_2 is not None:
            g2_first_name_field.send_keys(guest_2["First Name"])
            time.sleep(SLEEP_TIME)
            g2_last_name_field.send_keys(guest_2["Last Name"])
            time.sleep(SLEEP_TIME)

        num_adults_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="sbooking-step2-holder"]/form/div/div[2]/div/div[1]/div[2]/nz-select',)))
        num_adults_field.click()
        time.sleep(SLEEP_TIME)
        ul_menu = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, f'//*[@id="cdk-overlay-{OVERLAY_COUNTER}"]/div/div/ul')))
        OVERLAY_COUNTER += 1
        li_options = ul_menu.find_elements(By.TAG_NAME, "li")
        for li in li_options:
            if int(li.text) == num_adults:
                li.click()
                time.sleep(SLEEP_TIME)
                break

        num_children_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="sbooking-step2-holder"]/form/div/div[2]/div/div[2]/div[2]/nz-select',)))
        num_children_field.click()
        time.sleep(SLEEP_TIME)
        ul_menu = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, f'//*[@id="cdk-overlay-{OVERLAY_COUNTER}"]/div/div/ul')))
        OVERLAY_COUNTER += 1
        li_options = ul_menu.find_elements(By.TAG_NAME, "li")
        for li in li_options:
            if int(li.text) == num_children:
                li.click()
                time.sleep(SLEEP_TIME)
                break
        next_btn = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH,'//button[.//p[normalize-space()="next"]]')))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",next_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", next_btn)
        logging.info(f"Botón next clickeado para {booking['Booking Number']}")
        time.sleep(SLEEP_TIME)
        
        register_btn = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH,'//button[.//p[normalize-space()="Register"]]')))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",register_btn)
        time.sleep(0.5)
        if CLICK:
            driver.execute_script("arguments[0].click();", register_btn)
            logging.info(f"Botón Register clickeado para {booking['Booking Number']}")

            WebDriverWait(driver, 60).until(lambda d: len(d.window_handles) == 2)
            driver.switch_to.window(driver.window_handles[-1])
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'myprofile-title')))
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            utils.register_done(RUTA_DONE, booking['Booking Number'])


        time.sleep(SLEEP_TIME)                                                 

        logging.info(f'Pasajeros del booking: {booking["Booking Number"]} ingresados correctamente.')
        
        register_bookings = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "bookings-title")))
        register_bookings.click()
        logging.info(f'Listo para un nuevo registro')

        return True
    except Exception as e:
        logging.error(f"Error en enter_passengers_data: {e}")
        return False


def logout(driver):
    try:
        logging.info("Cerrando sesion...")
        logout_btn = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="rightNav"]/ul/li/a')))
        time.sleep(SLEEP_TIME)
        logout_btn.click()
        logging.info("Sesion cerrada correctamente.")
        time.sleep(SLEEP_TIME)
        return True
    except Exception as e:
        logging.error(f"Error en logout: {e}")
        return False


def main():
    try:
        utils.filtrar_bookings_realizados(RUTA_JSONS, RUTA_DONE)
        options = Options()
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--start-maximized")
        if HEADLESS:
            options.add_argument("--headless")

        logging.basicConfig(
            level=LOGGING_LEVEL,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(RUTA_LOGS), logging.StreamHandler()],
        )

        logging.info("Iniciando driver...")
        service = Service(executable_path=RUTA_DRIVER)
        driver = webdriver.Chrome(service=service, options=options)
        logged = login(driver)
        registered_bookings = (
            register_bookings(driver)
            if logged
            else logging.error("No se pudo iniciar sesion."))
        if not registered_bookings:
            logging.error("No se pudo registrar todos los bookings.")
    except Exception as e:
        logging.critical(f"Algo salio mal :( \nError: {e}")
    finally:
        logging.info("Cerrando sesion...")
        logedout = logout(driver)
        (
            logging.info("Sesion cerrada.")
            if logedout
            else logging.error("No se pudo cerrar sesion.")
        )
        driver.quit()


if __name__ == "__main__":
    main()
