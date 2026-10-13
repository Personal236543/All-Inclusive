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

from hoteles.dominican.dominican_mapping import hotels, aerolineas 
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
USERNAME = config.get("DOMINICAN_USERNAME")
PASSWORD = config.get("DOMINICAN_PASSWORD")
COMMISSION_RULE = "Dominican Republic Tourism"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_JSONS = os.path.join(BASE_DIR, "json", "bookings.json")
RUTA_DONE = os.path.join(BASE_DIR, "json", "done.json")
RUTA_PENDIENTES = os.path.join(BASE_DIR, "json", "pendientes.json")
RUTA_LOGS = os.path.join(BASE_DIR, "logs", "dominican.log")
RUTA_DRIVER = os.path.abspath(os.path.join(BASE_DIR, "../../chromedriver.exe"))


OVERLAY_COUNTER = 3
HOTELS = hotels
AEROLINEAS = aerolineas
AERO = True


os.makedirs(os.path.dirname(RUTA_JSONS), exist_ok=True)

def login(driver):
    try:
        logging.info("Iniciando sesion...")
        driver.get("https://www.mybookingrewards.com/login")
        time.sleep(SLEEP_TIME)

        # Aceptar cookies
        try:
            allow_cookies_btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.js-cookie-consent-agree")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",allow_cookies_btn)
            time.sleep(0.5)
            safe_click(driver, allow_cookies_btn)
            logging.info("Cookies aceptadas correctamente.")

        except TimeoutException:
            logging.info("No se encontro el banner de cookies, continuando...")

        except Exception as e:
            logging.warning(f"No se pudo aceptar cookies, continuando... Error: {e}")

        # Esperar campos de login
        username_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "email")))
        password_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "password")))

        time.sleep(SLEEP_TIME)

        # Ingresar credenciales
        username_field.send_keys(USERNAME)
        password_field.send_keys(PASSWORD)

        # Clic en el boton de "Iniciar sesion"
        login_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="page"]/div[2]/div[1]/div/div/div[5]/span/button')))
        login_button.click()

        # Esperar elemento que confirme el login exitoso (ajusta esto según el sitio)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '//*[@id="nav-content"]/ul/li[1]/a')))
        logging.info("✅ Inicio de sesion exitoso.")
        return True

    except Exception as e:
        logging.error(f"❌ Error en login: {e}")
        return False

def register_bookings(driver):
    try:
        logging.info("Registrando bookings...")

        # Esperar y hacer clic en el enlace "My Activity"
        my_activity_link = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.LINK_TEXT, "My Activity")))
        my_activity_link.click()
        time.sleep(SLEEP_TIME)

        # Esperar que se cargue algún elemento que indique que la seccion "Activity" está lista
        WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located((By.XPATH, '//*[@id="page"]/div[2]/div/div/div/div[2]/div/table/thead/tr/th[1]/a')))  # ← Ajusta si hay otro tipo de campo
        time.sleep(SLEEP_TIME)     

        # Cargar bookings desde JSON
        with open(RUTA_JSONS, "r", encoding="utf-8") as file:
            bookings = json.load(file)

        today = datetime.now().date()
        cutoff_date = today - timedelta(days=30)  # hoy menos 30 días

        i = 0
        while (i < TO_PROCESS) and (i < len(bookings)):
            booking = bookings[i]
            departure_date_str = booking["Departure Date"]

            try:
                departure_date = datetime.strptime(departure_date_str, "%m/%d/%Y").date()
                logging.debug(f"Fecha de salida del booking {booking['Booking Number']}: {departure_date}")
                logging.debug(f"Fecha límite para registrar: {cutoff_date}")
            except ValueError as e:
                msg = f"Error al convertir la fecha: {departure_date_str} en booking {booking['Booking Number']}: {e}"
                logging.error(msg)
                utils.register_pending(RUTA_PENDIENTES,booking["Booking Number"],msg)
                i += 1
                continue

            # ✅ Nueva condicion: registrar solo si departure_date >= today - 30 días
            if departure_date < cutoff_date:
                msg = f"Booking {booking['Booking Number']} es anterior a {cutoff_date}, se registra como pendiente."
                logging.info(msg)
                utils.register_pending(RUTA_PENDIENTES,booking["Booking Number"], msg)
                i += 1
            #Obtener hotel y tipo de habitacion mapeados
            else:
                if not utils.check_hotel_durations(bookings[i], RUTA_PENDIENTES):
                    i += 1
                    continue
                '''
                mapped_airline = mapping.map_hotel(AEROLINEAS, booking["Airline"])
                
                if mapped_airline is None:
                    msg = f"No se encontro el mapeo para {booking['Airline']}"
                    logging.warning(msg)
                    utils.register_pending(RUTA_PENDIENTES, booking["Booking Number"], msg)
                    i += 1
                    continue'''
                skip_booking = False
                for h in bookings[i]["Hotels"]:
                    
                    # Hacer scroll al hotel definido por COMMISSION_RULE
                    hotel_visible_name = H[COMMISSION_RULE]["name"]
                    logging.info(f"Haciendo scroll al hotel: '{hotel_visible_name}' para booking {booking['Booking Number']}...")
                    hotel_title_element = scroll_to_hotel(driver, hotel_visible_name)

                    if not hotel_title_element:
                        logging.error("❌ No se pudo hacer scroll al hotel del COMMISSION_RULE.")
                        return False
                    hotel, room = mapping.map_pair(HOTELS, h["Hotel Name"], h["Room Type"])
                    if hotel is None:
                        msg = f"No se encontro el mapeo para {h['Hotel Name']}"
                        logging.warning(msg)
                        utils.register_pending(RUTA_PENDIENTES,bookings[i]["Booking Number"], msg)
                        skip_booking = True
                        break
                    
                if skip_booking:
                    i += 1
                    continue
                registered = register_booking(driver, bookings[i])
                # Registrar el booking
                if not registered:
                    msg = f"No se pudo registrar el booking: {bookings[i]['Booking Number']}"
                    logging.warning(msg)
                    i += 1
                    continue

                i += 1


        logging.info("✅ Registro de bookings exitoso.")
        return True

    except Exception as e:
        logging.error(f"❌ Error en register_bookings: {e}")
        return False

    
def register_booking(driver, booking):
    try:
        time.sleep(5)
        logging.info(f"Registrando booking: {booking}...")

        # 1️⃣ Click en el boton "Log a Booking"
        log_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//*[@id='page']/div[2]/div/div/div/div[3]/div[5]/div/div[1]/div[3]/div[1]/div/div[1]/button"
            ))
        )
        log_button.click()
        logging.info(f"✅ Click en 'Log a Booking' para iniciar registro de {booking['Booking Number']}")
        time.sleep(2)

        
        json_hotels = booking["Hotels"]
        json_passengers = booking["Passengers"]
        passegers_per_room = len(json_passengers) // len(json_hotels)
        remaining = len(json_passengers) % len(json_hotels)
        for i, hotel in enumerate(json_hotels):
            start = i * passegers_per_room + min(i, remaining)
            end = start + passegers_per_room + (1 if i < remaining else 0)
            success = enter_booking_data(driver, booking, hotel, start, end, log_button)
            if not success:
                logging.warning(f"No se pudo registrar la habitacion {i + 1} del booking {booking['Booking Number']}")
                return False
        return True
    except Exception as e:
        logging.error(f"Error en register_booking: {e}")
        return False

def enter_booking_data(driver, booking, hotel, start, end, log_button):
    try:
        logging.info(f'Ingresando datos del booking: {booking["Booking Number"]}...')
        # 2️⃣ Esperar a que aparezca el input #hotel
        hotel_field = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "hotel"))
            )
        logging.info("✅ Input #hotel visible")
        
        # 3️⃣ Escribir el nombre completo del hotel desde el mapping
        safe_click(driver, hotel_field)
        hotel_field.clear()
        json_hotel_name = hotel["Hotel Name"]
        json_room_name = hotel["Room Type"]
        hotel_name, room_name = mapping.map_pair(HOTELS, json_hotel_name, json_room_name)
        hotel_field.send_keys(hotel_name)
        time.sleep(SLEEP_TIME)
        logging.info(f"✅ Escribio el nombre completo del hotel: '{hotel_name}'")

        # 4️⃣ Esperar a que aparezca el dropdown con los hoteles
        listbox = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#select-hotel [role='listbox']")))
        logging.info("✅ Dropdown de hoteles visible")

        # 5️⃣ Oprimir el primer elemento del dropdown
        first_option = WebDriverWait(listbox, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[aria-label]")))
        first_option.click()
        logging.info("✅ Primer hotel seleccionado del dropdown (Dominican)")
        time.sleep(1)
        
        # 6️⃣ Verificar si hay dropdown de room_type (algunos hoteles no lo tienen)
        room_fields = driver.find_elements(By.ID, "room_type")
        if room_fields:
            logging.info("Dropdown de room_type detectado para este hotel.")
            if room_name is None:
                msg = (f"Se requiere el mapeo para la habitacion {json_room_name} del hotel {json_hotel_name} y no se encontro.")
                logging.warning(msg)
                utils.register_pending(RUTA_PENDIENTES, booking["Booking Number"], msg)
                log_button.click()  # Volver a hacer clic en "Log a Booking" para resetear el formulario
                logging.info(f"Log_button click - no se encontro mapeo de habitacion. Registro fallido para {booking['Booking Number']} - {json_hotel_name} - {json_room_name}")
                return False
            
            room_select_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "room_type")))
            room_select_element.click()  
            time.sleep(1)
            select_room = Select(room_select_element)
            try:
                select_room.select_by_visible_text(room_name)
                logging.info(f"Room Type seleccionado: {room_name}")

            except NoSuchElementException:
                available_rooms = [
                    option.text.strip()
                    for option in select_room.options
                    if option.text.strip() and "Room Type" not in option.text.strip()
                ]
                msg = (
                    f"La habitacion mapeada '{room_name}' del hotel {json_hotel_name} no existe en el dropdown . "
                    f"Habitacion original: '{json_room_name}'. "
                    f"Opciones disponibles: {available_rooms}"
                )
                logging.warning(msg)
                utils.register_pending(RUTA_PENDIENTES, booking["Booking Number"], msg)
                return False
            finally:
                logging.info("Volviendo al hotel antes de continuar con el siguiente booking...")

                hotel_visible_name = H[COMMISSION_RULE]["name"]
                hotel_title_element = scroll_to_hotel(driver, hotel_visible_name)
                log_button.click()
                logging.info(f"Log_button click - habitacion con dropdown. Registro fallido para {booking['Booking Number']} - {json_hotel_name} - {json_room_name}")

                if not hotel_title_element:
                    logging.error("❌ No se pudo hacer scroll al hotel del COMMISSION_RULE después del intento de registro.")
                    return False

            logging.info(f"Room Type seleccionado: {room_name}")
        else:
            logging.info("Este hotel no muestra dropdown de habitaciones. Continuando normal.")


        # 6️⃣ Esperar a que aparezca el input #booking_reference (formulario listo)
        booking_ref_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "booking_reference"))
        )
        logging.info("✅ Formulario listo, input #booking_reference visible")
        safe_click(driver, booking_ref_input)
        booking_ref_input.clear()
        booking_ref_input.send_keys(booking["Booking Number"])
        
        
        entered_passengers = enter_passengers_and_room_data(driver, booking, start, end)
        
        tour_operator_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "tour_operator")))
        safe_click(driver, tour_operator_field)
        tour_operator_field.clear()
        if booking["Supplier"] == "DestiWorld":
            tour_operator_field.send_keys("DESTIWORLD")
        else:
            tour_operator_field.send_keys(booking["Supplier"])
        time.sleep(SLEEP_TIME)
        
        arrival_date_month, arrival_date_day, arrival_date_year = booking["Departure Date"].split("/")
        arrival_date = f"{arrival_date_month}/{arrival_date_day}/{arrival_date_year}"
        arrival_date_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="log-a-booking-form"]/div[1]/div[6]/div/div/input[2]')))
        safe_click(driver, arrival_date_field)
        arrival_date_field.clear()
        arrival_date_field.send_keys(arrival_date)
        time.sleep(3)
        
        booking_date_month, booking_date_day, booking_date_year = booking["Date Entered"].split("/")
        booking_date = f"{booking_date_month}/{booking_date_day}/{booking_date_year}"
        booking_date_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="log-a-booking-form"]/div[1]/div[12]/div/div/input[2]')))
        safe_click(driver, booking_date_field)
        booking_date_field.clear()
        booking_date_field.send_keys(booking_date)
        time.sleep(3)
        
        no_of_rooms_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "no_of_rooms")))
        safe_click(driver, no_of_rooms_field)
        no_of_rooms_field.clear()
        no_of_rooms_field.send_keys(len(booking["Hotels"]))
        time.sleep(SLEEP_TIME)
    
        # Click en el día seleccionado del calendario abierto
        safe_click(driver, arrival_date_field)
        time.sleep(0.5)
        selected_day = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR,".flatpickr-calendar.open .flatpickr-day.selected")))
        safe_click(driver, selected_day)
        logging.info(f"Arrival date confirmado con click en el día seleccionado: {arrival_date}")
        time.sleep(1)
        
        safe_click(driver, booking_date_field)
        time.sleep(0.5)
        selected_day = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR,".flatpickr-calendar.open .flatpickr-day.selected")))
        safe_click(driver, selected_day)
        logging.info(f"Booking date confirmado con click en el día seleccionado: {booking_date}")
        time.sleep(1)
        
        no_of_nights_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "no_of_nights")))
        safe_click(driver, no_of_nights_field)
        no_of_nights_field.clear()
        no_of_nights_field.send_keys(booking["Hotels"][0]["Duration"])
        time.sleep(SLEEP_TIME)
        
        # Click en el día seleccionado del calendario abierto
        
        
        package_cost_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "package_cost")))
        safe_click(driver, package_cost_field)
        package_cost_field.clear()
        package_cost_field.send_keys(booking["Supplier Price"]) 
        time.sleep(SLEEP_TIME)
        
        no_of_pax_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "no_of_pax")))
        safe_click(driver, no_of_pax_field)
        no_of_pax_field.clear()
        no_of_pax_field.send_keys(len(booking["Passengers"]))
        time.sleep(SLEEP_TIME)

        # Abrir dropdown de airline
        airline_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="log-a-booking-form"]/div[1]/div[11]/div/div/span/div')))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",airline_button)
        time.sleep(0.5)
        safe_click(driver, airline_button)
        logging.info("[Airline] Dropdown abierto")
        # Esperar el listbox abierto
        airline_listbox = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//ul[@role="listbox" and .//li[@id="airlineOption** Not Applicable **"]]')))
        logging.info("[Airline] Listbox visible")

        # Seleccionar siempre ** Not Applicable **
        not_applicable_option = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH,'//li[@id="airlineOption** Not Applicable **" and @role="option"]')))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});",not_applicable_option)
        time.sleep(0.3)
        safe_click(driver, not_applicable_option)
        logging.info("[Airline] Seleccionada opcion ** Not Applicable **")   
        time.sleep(3)        #BOTON REGISTRAR
        register_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="log-a-booking-form"]/div[3]/button')))
        # 🔽 Hacer scroll al boton antes de hacer clic
        driver.execute_script("arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });", register_btn)
        time.sleep(2)

        if CLICK:
            safe_click(driver, register_btn)
            logging.info(f"Boton 'Register' clickeado para {booking['Booking Number']}")
            time.sleep(2)
            registro_exitoso = False
            try:
                confirmation_msg = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH,'//*[@id="booking-progress"]')))
                logging.info(f"Mensaje de confirmacion detectado para booking {booking['Booking Number']}")
                logging.info("Registro exitoso.")

                utils.register_done(RUTA_DONE, booking["Booking Number"])
                registro_exitoso = True

            except TimeoutException:
                msg = f"No se detecto mensaje de confirmacion para booking {booking['Booking Number']}."
                logging.error(msg)
                utils.register_pending(RUTA_PENDIENTES, booking["Booking Number"], msg)
                registro_exitoso = False
                

            finally:
                # ✅ Esto se ejecuta SIEMPRE:
                logging.info("Volviendo al hotel antes de continuar con el siguiente booking...")

                hotel_visible_name = H[COMMISSION_RULE]["name"]
                
                if registro_exitoso:
                    hotel_title_element = scroll_to_hotel(driver, hotel_visible_name)
                else:
                    hotel_title_element = scroll_to_hotel(driver, hotel_visible_name)
                    log_button.click()
                    f"Log_button click - no se vio mensaje de confirmacion."

                if not hotel_title_element:
                    logging.error("❌ No se pudo hacer scroll al hotel del COMMISSION_RULE después del intento de registro.")
                    return False

            return registro_exitoso
        
        logging.info(f"Datos del booking {booking['Booking Number']} ingresados correctamente.")
    except Exception as e:
        logging.error(f"Error en enter_booking_data: {e}")
        return False
    

def enter_passengers_and_room_data(driver, booking, start, end):
    try:
        logging.info(f'Ingresando pasajeros del booking: {booking["Booking Number"]}...')

        guest_1 = booking["Passengers"][start]

        # 🔹 SI HAY MÁS DE UNA HABITACIoN → TODOS LOS PASAJEROS
        if len(booking["Hotels"]) > 1:
            guests_for_notes = [
                f"{p['First Name']} {p['Last Name']}"
                for p in booking["Passengers"]
            ]
        else:
            # 🔹 UNA SOLA HABITACIoN → SOLO EL RANGO
            guests_for_notes = [
                f"{booking['Passengers'][i]['First Name']} {booking['Passengers'][i]['Last Name']}"
                for i in range(start, end)
            ]

        # Ingresar Lead Guest
        g1_first_name_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "guest_first_name")))
        g1_last_name_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "guest_last_name")))

        safe_click(driver, g1_first_name_field)
        g1_first_name_field.clear()
        g1_first_name_field.send_keys(guest_1["First Name"])
        time.sleep(SLEEP_TIME)

        safe_click(driver, g1_last_name_field)
        g1_last_name_field.clear()
        g1_last_name_field.send_keys(guest_1["Last Name"])
        time.sleep(SLEEP_TIME)

        # 🔹 Enviar TODOS los pasajeros a Notes si hay múltiples habitaciones
        if len(booking["Hotels"]) > 1:
            notes_text = "\n".join(guests_for_notes)
            notes_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "notes")))
            safe_click(driver, notes_field)
            notes_field.clear()
            notes_field.send_keys(notes_text)
            time.sleep(SLEEP_TIME)

            logging.info(f"Notas enviadas:\n{notes_text}")

        logging.info(f'Pasajeros del booking {booking["Booking Number"]} ingresados correctamente.')
        return True

    except Exception as e:
        logging.error(f"Error en enter_passengers_and_room_data: {e}")
        return False




def scroll_to_hotel(driver, hotel_visible_name):
    try:
        logging.info(f"🔍 Buscando hotel visible: '{hotel_visible_name}'")

        titulos = driver.find_elements(By.XPATH, "//h3[contains(@class, 'text-2xl')]")

        for titulo in titulos:
            texto = titulo.text.strip().lower()
            if hotel_visible_name in texto or texto in hotel_visible_name:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", titulo)
                logging.info(f"✅ Scroll realizado al hotel: '{titulo.text.strip()}'")
                time.sleep(1)
                return titulo

        logging.warning(f"❌ No se encontro el hotel '{hotel_visible_name}' en la página.")
        return None

    except Exception as e:
        logging.error(f"❌ Error al hacer scroll al hotel '{hotel_visible_name}': {e}")
        return None
def wait_loader_invisible(driver, timeout=20):
    try:
        WebDriverWait(driver, timeout).until(EC.invisibility_of_element_located((By.ID, "full-screen-loader")))
    except TimeoutException:
        # si nunca desaparece, seguimos pero intentaremos JS click
        pass

def safe_click(driver, element, timeout=20):
    wait_loader_invisible(driver, timeout)
    try:
        element.click()
    except ElementClickInterceptedException:
        # último recurso: scroll + JS click
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        wait_loader_invisible(driver, 5)
        driver.execute_script("arguments[0].click();", element)
        
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
        #utils.eliminar_bookings_pasados(RUTA_PENDIENTES, RUTA_JSONS)
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
        driver = webdriver.Chrome(options=options)
        logged = login(driver)
        registered_bookings = (
            register_bookings(driver)
            if logged
            else logging.error("No se pudo iniciar sesion.")
        )
        if not registered_bookings:
            logging.error("No se pudo registrar todos los bookings.")
    except Exception as e:
        logging.critical(f"Algo salio mal :( \nError: {e}")
    
    finally:
        
        logging.info("Cerrando sesion...")
        
        logedout = False
        #logout(driver)
        (
            logging.info("Sesion cerrada.")
            if logedout
            else logging.error("No se pudo cerrar sesion.")
        )
        driver.quit()
        


if __name__ == "__main__":
    main()