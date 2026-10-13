import json
import os
from datetime import datetime
from datetime import timedelta
import platform, time, logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException, StaleElementReferenceException, InvalidElementStateException, ElementNotInteractableException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from hoteles.jamaica.jamaica_mapping import hotels
from hoteles.mybookingrewards.mybookingrewards_mapping import hotels as H
from utils import mapping, register1,utils
import script_runner as sr
from utils import config

EJECUTABLE = sr.EJECUTABLE
CLICK = True

SLEEP_TIME = 2 #No menos de 2
TO_PROCESS = 10000 #No mas de 70
HEADLESS = False
LOGGING_LEVEL = logging.INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
USERNAME = config.get("JAMAICA_USERNAME")
PASSWORD = config.get("JAMAICA_PASSWORD")
COMMISSION_RULE = "Jamaica One Love Rewards Program"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_JSONS = os.path.join(BASE_DIR, "json", "bookings.json")
RUTA_DONE = os.path.join(BASE_DIR, "json", "done.json")
RUTA_PENDIENTES = os.path.join(BASE_DIR, "json", "pendientes.json")
RUTA_LOGS = os.path.join(BASE_DIR, "logs", "jamaica.log")
RUTA_DRIVER = os.path.abspath(os.path.join(BASE_DIR, "../../chromedriver.exe"))


OVERLAY_COUNTER = 3
HOTELS = hotels
#AEROLINEAS = aerolineas
AERO = True


os.makedirs(os.path.dirname(RUTA_JSONS), exist_ok=True)

def configurar_logging():
    logging.basicConfig(
        level=LOGGING_LEVEL,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(RUTA_LOGS, encoding="utf-8"), logging.StreamHandler()],
    )


def crear_driver():
    options = Options()
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--start-maximized")
    if HEADLESS:
        options.add_argument("--headless")

    service = Service(executable_path=RUTA_DRIVER)
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def cargar_bookings(ruta_json, limite=None):
    with open(ruta_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("El JSON debe contener una lista de bookings.")

    if limite is not None:
        return data[:limite]

    return data


def login(driver):
    try:
        logging.info("Iniciando sesión...")
        driver.get("https://www.oneloverewards.com/bookings")
        time.sleep(SLEEP_TIME)
        #decline_cookies = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="decline-cookies"]')))
        #decline_cookies.click()
        #time.sleep(3)

        username_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "UserName")))
        password_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "Password")))

        time.sleep(SLEEP_TIME)

        username_field.clear()
        username_field.send_keys(USERNAME)

        password_field.clear()
        password_field.send_keys(PASSWORD)

        login_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="myForm"]/button')))
        login_button.click()
        
        time.sleep(7)

        logging.info("✅ Inicio de sesion exitoso.")
        return True

    except Exception as e:
        logging.error(f"❌ Error en login: {e}")
        return False


def logout(driver):
    try:
        # Ajusta esto con el selector real de logout
        # logout_button = WebDriverWait(driver, 10).until(
        #     EC.element_to_be_clickable((By.XPATH, "XPATH_LOGOUT"))
        # )
        # logout_button.click()
        time.sleep(SLEEP_TIME)
        return True
    except Exception as e:
        logging.warning(f"No se pudo cerrar sesión correctamente: {e}")
        return False
    
def get_fecha_minima_registro(today=None):
    """
    Regla Jamaica:
    - Del día 1 al 14: se permiten bookings desde el primer día del mes anterior.
    - Desde el día 15: solo se permiten bookings desde el primer día del mes actual.
    """
    if today is None:
        today = datetime.now().date()

    if today.day < 15:
        if today.month == 1:
            return today.replace(year=today.year - 1, month=12, day=1)

        return today.replace(month=today.month - 1, day=1)

    return today.replace(day=1)

def type_field(driver, locator, value, timeout=20, clear=True):
    field = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",field)
    time.sleep(0.3)
    field.click()
    if clear:
        field.clear()
    field.send_keys(value)
    return True
def handle_after_record_booking(driver, booking_no, timeout=30):
    """
    Después de hacer click en Record Booking:
    - Si aparece error text-danger, lo descarta y vuelve al formulario.
    - Si aparece addBooking, continúa normal.
    Retorna:
    - "success"
    - "duplicate_or_error"
    - False
    """

    ENTER_ANOTHER_BOOKING_BUTTON = (By.ID, "addBooking")
    ENTER_ANOTHER_BOOKING_BUTTON2 = (By.XPATH, '/html/body/section[2]/div/div/div[2]/div/ul/li[1]/a')
    ERROR_MESSAGE = (By.CLASS_NAME, "text-danger")

    end_time = time.time() + timeout

    while time.time() < end_time:
        # Caso 1: error / booking repetido
        error_elements = driver.find_elements(*ERROR_MESSAGE)

        visible_errors = [
            e for e in error_elements
            if e.is_displayed() and e.text.strip()
        ]

        if visible_errors:
            error_text = " | ".join(e.text.strip() for e in visible_errors)

            logging.warning(
                f"Booking {booking_no} descartado por alerta del sistema: {error_text}"
            )

            enter_another_booking = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable(ENTER_ANOTHER_BOOKING_BUTTON2)
            )

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                enter_another_booking
            )

            time.sleep(0.5)
            enter_another_booking.click()

            logging.info(
                f"Formulario reiniciado después de alerta para booking {booking_no}."
            )

            WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.ID, "HotelBooked"))
            )

            return "duplicate_or_error"

        # Caso 2: éxito normal
        add_buttons = driver.find_elements(*ENTER_ANOTHER_BOOKING_BUTTON)

        visible_add_buttons = [
            b for b in add_buttons
            if b.is_displayed() and b.is_enabled()
        ]

        if visible_add_buttons:
            enter_another_button = visible_add_buttons[0]

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                enter_another_button
            )

            time.sleep(0.5)
            enter_another_button.click()

            logging.info(
                "Boton Enter Another Booking clickeado. Formulario listo para el siguiente booking."
            )

            WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.ID, "HotelBooked"))
            )

            return "success"

        time.sleep(0.5)

    logging.error(
        f"No apareció confirmación ni alerta después de Record Booking para {booking_no}."
    )

    return False

def select_field_by_text(driver, locator, visible_text, timeout=20):
    select_el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable(locator)
    )

    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});",
        select_el
    )

    time.sleep(0.3)
    Select(select_el).select_by_visible_text(visible_text)
    return True

def select_gijgo_date_from_calendar(driver, locator, date_value, timeout=20):
    """
    Selecciona una fecha en calendario Gijgo sin usar send_keys.
    date_value debe venir en formato mm/dd/yyyy.
    """

    target_date = datetime.strptime(date_value, "%m/%d/%Y")
    target_day = str(target_date.day)
    target_month = target_date.month - 1  # Gijgo usa meses 0-based
    target_year = target_date.year

    # Abrir calendario
    field = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",field)

    time.sleep(0.3)
    field.click()

    # Calendario visible
    calendar = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((
            By.XPATH,
            '//div[@role="calendar" and not(contains(@style, "display: none"))]'
        ))
    )

    for _ in range(36):  # máximo 3 años de navegación
        calendar = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((
                By.XPATH,
                '//div[@role="calendar" and not(contains(@style, "display: none"))]'
            ))
        )

        current_month = int(calendar.get_attribute("month"))
        current_year = int(calendar.get_attribute("year"))

        if current_month == target_month and current_year == target_year:
            day_cell = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    f'//div[@role="calendar" and not(contains(@style, "display: none"))]'
                    f'//td[@day="{target_day}" and @month="{target_month}" and @year="{target_year}"]'
                ))
            )

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                day_cell
            )

            time.sleep(0.2)
            day_cell.click()

            logging.info(f"Fecha seleccionada en calendario: {date_value}")
            return True

        # Decidir dirección
        if (current_year, current_month) < (target_year, target_month):
            next_btn = calendar.find_element(
                By.XPATH,
                './/div[@role="navigator"]/div[3]'
            )
            next_btn.click()
        else:
            prev_btn = calendar.find_element(
                By.XPATH,
                './/div[@role="navigator"]/div[1]'
            )
            prev_btn.click()

        time.sleep(0.3)

    logging.error(f"No se pudo llegar a la fecha {date_value} en el calendario.")
    return False

def register_bookings(driver, bookings):
    
    today = datetime.now().date()
    fecha_minima_registro = get_fecha_minima_registro(today)

    logging.info(f"Fecha actual: {today}")
    logging.info(f"Fecha mínima permitida para registrar: {fecha_minima_registro}")

    total_bookings = min(TO_PROCESS, len(bookings))
    descartados_por_fecha = 0
    registrados = 0
    pendientes = 0
    errores = 0

    i = 0

    while (i < TO_PROCESS) and (i < len(bookings)):
        booking = bookings[i]
        departure_date_str = booking["Departure Date"]
        try:
            logging.warning(f"Procesando booking {booking['Booking Number']}")
            try:
                departure_date = datetime.strptime(departure_date_str, "%m/%d/%Y").date()
                logging.debug(f"Fecha de salida del booking {booking['Booking Number']}: {departure_date}")
                logging.debug(f"Fecha mínima permitida para registrar: {fecha_minima_registro}")
            except ValueError as e:
                msg = f"Error al convertir la fecha: {departure_date_str} en booking {booking['Booking Number']}: {e}"
                logging.error(msg)
                utils.register_pending(RUTA_PENDIENTES,booking["Booking Number"],msg)
                pendientes += 1
                i += 1
                continue

            # Regla Jamaica: antes del 15 permite mes anterior; desde el 15 solo mes actual
            if departure_date < fecha_minima_registro:
                descartados_por_fecha += 1

                logging.info(
                    f"Booking {booking['Booking Number']} descartado por fecha. "
                    f"Departure date: {departure_date}. "
                    f"Fecha mínima permitida: {fecha_minima_registro}."
                )

                i += 1
                continue

            if not utils.check_hotel_durations(bookings[i], RUTA_PENDIENTES):
                i += 1
                continue
            # =========================
            # VALIDAR Y PREPARAR DATOS
            # =========================
            booking_no = booking["Booking Number"]

            # Pasajeros
            pasajeros = booking["Passengers"]
            if not pasajeros:
                msg = f"Booking {booking_no} no tiene pasajeros"
                logging.warning(msg)
                utils.register_pending(RUTA_PENDIENTES, booking_no, msg)
                pendientes += 1
                i += 1
                continue
            pasajero = pasajeros[0]
            client_name = pasajero["First Name"]
            client_surname = pasajero["Last Name"]
            guests_count = str(len(pasajeros))

            if not client_name or not client_surname:
                msg = f"Booking {booking_no} tiene nombre o apellido de pasajero vacío"
                logging.warning(msg)
                utils.register_pending(RUTA_PENDIENTES, booking_no, msg)
                pendientes += 1
                i += 1
                continue

            # Hoteles
            hoteles_booking = booking["Hotels"]
            if not hoteles_booking:
                msg = f"Booking {booking_no} no tiene hoteles"
                logging.warning(msg)
                utils.register_pending(RUTA_PENDIENTES, booking_no, msg)
                pendientes += 1
                i += 1
                continue

            h = hoteles_booking[0]
            json_hotel_name = h["Hotel Name"]
            json_room_name = h["Room Type"]
            hotel_mapped, room_mapped = mapping.map_pair(hotels,json_hotel_name,json_room_name)
            if hotel_mapped is None:
                msg = f"No se encontró el mapeo para hotel: {json_hotel_name}"
                logging.warning(msg)
                utils.register_pending(RUTA_PENDIENTES, booking_no, msg)
                pendientes += 1
                i += 1
                continue

            # Fechas
            booking_date = booking["Date Entered"]
            arrival_date = booking["Departure Date"]
            departure_date = booking["Return Date"]
            fechas_validas = True

            for field_name, date_value in {"Booking Date": booking_date,"Arrival Date": arrival_date,"Departure Date": departure_date,}.items():
                try:
                    datetime.strptime(date_value, "%m/%d/%Y")
                except ValueError:
                    msg = f"Booking {booking_no} tiene {field_name} inválida: '{date_value}'"
                    logging.warning(msg)
                    utils.register_pending(RUTA_PENDIENTES, booking_no, msg)
                    pendientes += 1
                    fechas_validas = False
                    break
            if not fechas_validas:
                i += 1
                continue

            # Otros campos
            tour_operator = booking["Supplier"]
            total_cost = str(booking["Supplier Price"])

            if not tour_operator:
                msg = f"Booking {booking_no} no tiene Supplier / Tour Operator"
                logging.warning(msg)
                utils.register_pending(RUTA_PENDIENTES, booking_no, msg)
                pendientes += 1
                i += 1
                continue


            if not total_cost:
                msg = f"Booking {booking_no} no tiene Supplier Price / Total Cost"
                logging.warning(msg)
                utils.register_pending(RUTA_PENDIENTES, booking_no, msg)
                i += 1
                continue

            logging.info(
                f"Datos listos para {booking_no}: "
                f"hotel={hotel_mapped}, operator={tour_operator}, "
                f"guest={client_name} {client_surname}, guests={guests_count}, "
                f"booking_date={booking_date}, arrival={arrival_date}, "
                f"departure={departure_date}, total={total_cost}"
            )
            
            added = add_booking_data(driver,booking_no,hotel_mapped,tour_operator,client_name,client_surname,guests_count,booking_date,arrival_date,departure_date,total_cost)
            if added == "duplicate_or_error":
                logging.warning(
                    f"Booking {booking_no} descartado porque ya existe o el sistema mostró alerta."
                )
                i += 1
                continue

            if not added:
                msg = f"No se pudo llenar el formulario para booking {booking_no}"
                logging.warning(msg)
                utils.register_pending(RUTA_PENDIENTES, booking_no, msg)
                pendientes += 1
                i += 1
                continue

            registrados += 1
            logging.info(f"Booking {booking_no} registrado correctamente.")
            utils.register_done(RUTA_DONE, booking_no)
            i += 1
        except Exception as e:
            msg = f"Error procesando booking {booking['Booking Number']}: {e}"
            logging.error(msg)
            utils.register_pending(RUTA_PENDIENTES, booking["Booking Number"], msg)
            pendientes += 1
            errores += 1
            i += 1
    logging.warning("========== RESUMEN JAMAICA ==========")
    logging.warning(f"Total evaluados: {total_bookings}")
    logging.warning(f"Registrados correctamente: {registrados}")
    logging.warning(f"Descartados por fecha: {descartados_por_fecha}")
    logging.warning(f"Pendientes guardados: {pendientes}")
    logging.warning(f"Errores: {errores}")
    logging.warning("=====================================")

    return {
        "total": total_bookings,
        "registrados": registrados,
        "descartados_por_fecha": descartados_por_fecha,
        "pendientes": pendientes,
        "errores": errores,
    }
    

def add_booking_data(driver,booking_no,hotel_mapped,tour_operator,client_name,client_surname,guests_count,booking_date,arrival_date,departure_date,total_cost):
    try:
        logging.info(f"Llenando formulario para booking {booking_no}...")

        # =========================
        # LOCATORS - COMPLETAR
        # =========================

        HOTEL_BOOKED = (By.ID, "HotelBooked")
        TOUR_OPERATOR = (By.ID, "NameOfTourOperator")
        CONFIRMATION_NUMBER = (By.ID, "ConfirmationNumber")
        CLIENT_FIRST_NAME = (By.ID, "ClientFirstName")
        CLIENT_LAST_NAME = (By.ID, "ClientLastName")
        NUMBER_OF_GUESTS = (By.ID, "NumberOfGuests")
        BOOKING_DATE = (By.ID, "BookingDate")
        ARRIVAL_DATE = (By.ID, "ArrivalDate")
        DEPARTURE_DATE = (By.ID, "DepartureDate")
        TOTAL_COST = (By.ID, "TotalCostFormatted")
        VALID_BOOKING_CHECKBOX = (By.ID, "isValidBooking")
        RECORD_BOOKING_BUTTON = (By.XPATH, '//button[@type="submit" and normalize-space(.)="Record Booking"]')
        ENTER_ANOTHER_BOOKING_BUTTON = (By.ID, "addBooking")
        ENTER_ANOTHER_BOOKING_BUTTON2 = (By.XPATH, '/html/body/section[2]/div/div/div[2]/div/ul/li[1]/a')
        # =========================
        # HOTEL BOOKED
        # =========================
        hotel_select = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(HOTEL_BOOKED))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",hotel_select)
        Select(hotel_select).select_by_visible_text(hotel_mapped)
        logging.info(f"Hotel Booked listo: {hotel_mapped}")

        # TEXT FIELDS
        type_field(driver, TOUR_OPERATOR, tour_operator)
        logging.info(f"Tour Operator listo: {tour_operator}")

        type_field(driver, CONFIRMATION_NUMBER, booking_no)
        logging.info(f"Confirmation Number listo: {booking_no}")

        type_field(driver, CLIENT_FIRST_NAME, client_name)
        logging.info(f"Client First Name listo: {client_name}")

        type_field(driver, CLIENT_LAST_NAME, client_surname)
        logging.info(f"Client Last Name listo: {client_surname}")

        type_field(driver, NUMBER_OF_GUESTS, guests_count)
        logging.info(f"Number of Guests listo: {guests_count}")

        if not select_gijgo_date_from_calendar(driver, BOOKING_DATE, booking_date):
            return False
        logging.info(f"Booking Date listo: {booking_date}")

        if not select_gijgo_date_from_calendar(driver, ARRIVAL_DATE, arrival_date):
            return False
        logging.info(f"Arrival Date listo: {arrival_date}")

        if not select_gijgo_date_from_calendar(driver, DEPARTURE_DATE, departure_date):
            return False
        logging.info(f"Departure Date listo: {departure_date}")

        # TOTAL COST
        total_cost_el = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(TOTAL_COST))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",total_cost_el)

        time.sleep(0.3)
        total_cost_el.click()
        total_cost_el.send_keys(Keys.CONTROL, "a")
        total_cost_el.send_keys(Keys.BACKSPACE)
        total_cost_el.send_keys(total_cost)

        logging.info(f"Total Cost listo: {total_cost}")
        
        # CHECKBOX VALID BOOKING
        valid_checkbox = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(VALID_BOOKING_CHECKBOX))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",valid_checkbox)
        time.sleep(0.3)
        if not valid_checkbox.is_selected():
            valid_checkbox.click()
        logging.info("Checkbox IsValidBooking marcado.")

        # BOTON RECORD BOOKING
        record_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(RECORD_BOOKING_BUTTON))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",record_button)
        time.sleep(0.5)
        if CLICK:
            record_button.click()
            logging.info(f"Boton Record Booking clickeado para {booking_no}")

            result = handle_after_record_booking(driver, booking_no)

            if not result:
                return False

            return result

        else:
            logging.info(f"CLICK=False. No se envio el booking {booking_no}.")
            return "success"
        
    except Exception as e:
        logging.error(f"Error llenando formulario para booking {booking_no}: {e}")
        return False
    
def guardar_json(ruta, data):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def main():
    driver = None
    all_done = []
    all_pendientes = []

    try:
        configurar_logging()

        bookings = cargar_bookings(RUTA_JSONS, TO_PROCESS)
        total_bookings = len(bookings)

        if total_bookings == 0:
            logging.warning("No hay bookings para procesar.")
            return


        logging.warning(f"Total de bookings: {total_bookings}")

        
        driver = crear_driver()

        try:
            logged = login(driver)

            if not logged:
                logging.error(f"No se pudo iniciar sesión")
            bookings = cargar_bookings(RUTA_JSONS, TO_PROCESS)
            resumen = register_bookings(driver, bookings)
            logging.warning(f"Resumen final: {resumen}")

        except Exception as e:
            logging.critical(f"Fallo : {e}")

        finally:
            try:
                logout(driver)
            except:
                pass

            try:
                driver.quit()
            except:
                pass

            driver = None

        logging.warning(f"Proceso terminado. DONE: {len(all_done)} | PENDIENTES: {len(all_pendientes)}")

    except Exception as e:
        logging.critical(f"Algo salió mal :( \nError: {e}")

    finally:
        if driver is not None:
            try:
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    main()