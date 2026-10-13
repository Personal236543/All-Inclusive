import os
import json
import time
import logging
from hoteles.iberostar.iberostar_mapping import hotels
from utils import mapping, utils
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from datetime import datetime
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
import script_runner as sr
from utils import config

CLICK = True
SLEEP_TIME = 1
TO_PROCESS = 500
HEADLESS = False
LOGGING_LEVEL = logging.INFO
COMMISSION_RULE = "Iberostar StarAgents Rewards"

EJECUTABLE = sr.EJECUTABLE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_JSONS = os.path.join(BASE_DIR, "json", "bookings.json")
RUTA_DONE = os.path.join(BASE_DIR, "json", "done.json")
RUTA_PENDIENTES = os.path.join(BASE_DIR, "json", "pendientes.json")
RUTA_LOGS = os.path.join(BASE_DIR, "logs", "iberostar.log")
RUTA_INVOICES = os.path.join(BASE_DIR, "invoices")
RUTA_DRIVER = os.path.abspath(os.path.join(BASE_DIR, "../../chromedriver.exe"))

os.makedirs(os.path.dirname(RUTA_JSONS), exist_ok=True)
os.makedirs(os.path.dirname(RUTA_LOGS), exist_ok=True)
HOTELS = hotels

# Formato: {"Nombre": {"code": "...", "password": "...", "necesita_puntos": true}}
# Ver hoteles/iberostar/agentes.example.json
AGENTES = config.cargar_json("IBEROSTAR_AGENTES_FILE", os.path.join("hoteles", "iberostar", "agentes.json"))


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


def obtener_agentes_activos(agentes_dict):
    agentes_activos = []

    for nombre, info in agentes_dict.items():
        if info.get("necesita_puntos", False):
            agentes_activos.append({
                "name": nombre,
                "code": info["code"],
                "password": info["password"],
            })

    return agentes_activos


def repartir_bookings(bookings, agentes):
    if not agentes:
        raise ValueError("No hay agentes con necesita_puntos=True.")

    reparto = {agente["name"]: [] for agente in agentes}

    for i, booking in enumerate(bookings):
        agente = agentes[i % len(agentes)]
        reparto[agente["name"]].append(booking)

    return reparto


def guardar_resumen_reparto(reparto, ruta_salida):
    resumen = []

    for username, lista_bookings in reparto.items():
        resumen.append({
            "agent": username,
            "count": len(lista_bookings),
            "booking_numbers": [b.get("Booking Number", "SIN_NUMERO") for b in lista_bookings]
        })

    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(resumen, f, indent=4, ensure_ascii=False)


def login(driver, nombre, code, password):
    try:
        logging.info(f"Iniciando sesión con {nombre}...")
        driver.get("https://www.staragents.com/en/star_agents/new/")
        time.sleep(3)
        decline_cookies = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="decline-cookies"]')))
        decline_cookies.click()
        time.sleep(3)


        login_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/header/div[2]/div/div/li'))
        )
        login_button.click()

        username_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "ibs-email"))
        )
        password_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "ibs-password"))
        )

        time.sleep(SLEEP_TIME)

        username_field.clear()
        username_field.send_keys(code)

        password_field.clear()
        password_field.send_keys(password)
        
        login_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="login-button-cms"]')))
        login_button.click()
        
        time.sleep(7)

        logging.info(f"Sesión iniciada con {nombre}")
        return True

    except Exception as e:
        logging.error(f"❌ Error en login con {nombre}: {e}")
        return False


def logout(driver):
    try:
        logging.info("Iniciando logout...")

        # Limpiar cualquier modal/overlay antes del logout
        cerrar_formulario_y_menu(driver)

        # =========================
        # ABRIR MENÚ PRINCIPAL
        # =========================
        menu = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/header/div[1]/div/ul/li[2]/button')))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});",menu)
        time.sleep(0.5)
        try:
            menu.click()
        except Exception:
            driver.execute_script("arguments[0].click();", menu)

        logging.info("Menú abierto para logout")
        time.sleep(SLEEP_TIME)
        # =========================
        # PRIVATE AREA
        # =========================
        private_area = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "nav-item-my-ib")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});",private_area)
        time.sleep(0.5)
        try:
            private_area.click()
        except Exception:
            driver.execute_script("arguments[0].click();", private_area)
        logging.info("Private area abierto")
        time.sleep(SLEEP_TIME)

        # =========================
        # LOGOUT
        # =========================
        logout_link = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "logout")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});",logout_link)
        time.sleep(0.5)
        try:
            logout_link.click()
        except Exception:
            driver.execute_script("arguments[0].click();", logout_link)
        logging.info("Logout clickeado correctamente")
        # Esperar a que vuelva o cambie de página
        time.sleep(5)
        return True
    except Exception as e:
        logging.warning(f"No se pudo cerrar sesión correctamente: {e}")
        return False


def fecha_a_data_id(fecha_str):
    return datetime.strptime(fecha_str, "%m/%d/%Y").strftime("%d%m%Y")


def obtener_calendario_visible(driver):
    """
    Busca el datepicker visible actual.
    No usa /html/body/div[7], porque ese div puede cambiar.
    """
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".month-wrapper")))

    calendarios = driver.find_elements(By.CSS_SELECTOR, ".month-wrapper")
    calendarios_visibles = [c for c in calendarios if c.is_displayed()]

    if not calendarios_visibles:
        raise Exception("No se encontró ningún calendario visible.")

    return calendarios_visibles[-1]


def seleccionar_rango_fechas_calendario(driver, check_in, check_out):
    """
    Abre el calendario desde check_in y selecciona check_in + check_out.
    Busca los días por data-id dentro del calendario visible.
    Si no encuentra la fecha, se mueve prev/next según corresponda.
    """
    checkin_input = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "check_in"))
    )

    ActionChains(driver).move_to_element(checkin_input).pause(0.2).click().perform()

    calendario = obtener_calendario_visible(driver)

    fecha_check_in = datetime.strptime(check_in, "%m/%d/%Y").date()
    hoy = datetime.today().date()

    if fecha_check_in < hoy:
        direccion = "prev"
    else:
        direccion = "next"

    logging.info(f"Calendario abierto. Dirección de búsqueda: {direccion}")

    for fecha in [check_in, check_out]:
        data_id = fecha_a_data_id(fecha)

        for intento in range(24):
            calendario = obtener_calendario_visible(driver)

            dias = calendario.find_elements(
                By.CSS_SELECTOR,
                f"button.day[data-id='{data_id}']"
            )

            dias_visibles = [d for d in dias if d.is_displayed()]

            logging.info(
                f"Buscando fecha {fecha} -> {data_id}. "
                f"Encontrados visibles: {len(dias_visibles)}. Intento {intento + 1}"
            )

            if dias_visibles:
                dia = dias_visibles[0]

                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                    dia
                )

                driver.execute_script(
                    "arguments[0].style.border='3px solid red';"
                    "arguments[0].style.backgroundColor='yellow';",
                    dia
                )

                time.sleep(0.4)

                try:
                    ActionChains(driver).move_to_element(dia).pause(0.2).click().perform()
                except Exception:
                    driver.execute_script("arguments[0].click();", dia)

                logging.info(f"Fecha seleccionada: {fecha} -> {data_id}")
                time.sleep(0.8)
                break

            if direccion == "prev":
                nav_buttons = calendario.find_elements(By.CSS_SELECTOR, "button.prev")
            else:
                nav_buttons = calendario.find_elements(By.CSS_SELECTOR, "button.next")

            nav_visibles = [b for b in nav_buttons if b.is_displayed()]

            if not nav_visibles:
                raise Exception(f"No se encontró botón {direccion} visible en el calendario.")

            nav_btn = nav_visibles[0]

            try:
                ActionChains(driver).move_to_element(nav_btn).pause(0.2).click().perform()
            except Exception:
                driver.execute_script("arguments[0].click();", nav_btn)

            logging.info(f"Moviendo calendario con {direccion}")
            time.sleep(0.8)

        else:
            raise Exception(f"No se encontró la fecha {fecha} en el calendario.")

    logging.info(f"Rango seleccionado: {check_in} -> {check_out}")
    
def cerrar_formulario_y_menu(driver):
    """
    Limpia la pantalla para que el siguiente booking empiece bien:
    - Presiona ESC.
    - Cierra botones de modal visibles.
    - Hace click en overlays si quedaron.
    - Cierra el menú principal si quedó abierto.
    """

    # =========================
    # INTENTAR ESCAPE PRIMERO
    # =========================
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(1)
        logging.info("ESC enviado para cerrar posibles modales/overlays")
    except Exception as e:
        logging.warning(f"No se pudo enviar ESC: {e}")

    # =========================
    # CERRAR MODALES ABIERTOS
    # =========================
    try:
        close_buttons = driver.find_elements(
            By.CSS_SELECTOR,
            "button.btn-close-round[data-micromodal-close]"
        )

        close_buttons_visibles = [
            btn for btn in close_buttons
            if btn.is_displayed()
        ]

        for btn in close_buttons_visibles:
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                    btn
                )
                time.sleep(0.2)
                driver.execute_script("arguments[0].click();", btn)
                logging.info("Modal/formulario cerrado con botón close")
                time.sleep(1)
            except Exception as e:
                logging.warning(f"No se pudo cerrar un modal visible: {e}")

    except Exception as e:
        logging.warning(f"No se encontraron botones de cierre de modal: {e}")

    # =========================
    # CLICK EN OVERLAY SI SIGUE VISIBLE
    # =========================
    try:
        overlays = driver.find_elements(By.CSS_SELECTOR, ".modal__overlay")

        overlays_visibles = [
            ov for ov in overlays
            if ov.is_displayed()
        ]

        for overlay in overlays_visibles:
            try:
                driver.execute_script("arguments[0].click();", overlay)
                logging.info("Overlay cerrado con click directo")
                time.sleep(1)
            except Exception as e:
                logging.warning(f"No se pudo cerrar overlay con click: {e}")

    except Exception as e:
        logging.warning(f"No se pudieron revisar overlays: {e}")

    # =========================
    # FORZAR OCULTAR OVERLAYS PEGADOS
    # =========================
    try:
        driver.execute_script("""
            document.querySelectorAll('.modal__overlay').forEach(el => {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
                el.style.pointerEvents = 'none';
            });

            document.querySelectorAll('[aria-hidden="false"]').forEach(el => {
                if (el.className && String(el.className).includes('modal')) {
                    el.setAttribute('aria-hidden', 'true');
                    el.style.display = 'none';
                }
            });

            document.body.classList.remove('modal-open');
            document.body.style.overflow = 'auto';
        """)
        logging.info("Overlays/modales forzados a ocultarse por JS")
        time.sleep(1)
    except Exception as e:
        logging.warning(f"No se pudo forzar limpieza de overlays por JS: {e}")

    # =========================
    # ESPERAR A QUE OVERLAY DESAPAREZCA
    # =========================
    try:
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal__overlay"))
        )
        logging.info("Overlay de modal invisible")
    except Exception:
        logging.warning("El overlay no desapareció completamente")

    # =========================
    # CERRAR MENÚ SI ESTÁ ABIERTO
    # =========================
    try:
        menu_buttons = driver.find_elements(
            By.CSS_SELECTOR,
            "button[data-test='main-header__menu-toggle']"
        )

        menu_buttons_visibles = [
            btn for btn in menu_buttons
            if btn.is_displayed()
        ]

        if menu_buttons_visibles:
            menu_btn = menu_buttons_visibles[0]
            aria_expanded = menu_btn.get_attribute("aria-expanded")

            if aria_expanded == "true":
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                    menu_btn
                )
                time.sleep(0.2)
                driver.execute_script("arguments[0].click();", menu_btn)
                logging.info("Menú principal cerrado")
                time.sleep(1)
            else:
                logging.info("Menú principal ya estaba cerrado")

    except Exception as e:
        logging.warning(f"No se pudo cerrar el menú principal: {e}")
        
def validar_booking_antes_de_modal(booking, ruta_pendientes):
    """
    Valida todo lo que se puede revisar SIN abrir el modal ni tocar Selenium.

    Retorna:
        True, datos, None  -> si el booking está listo para ingresar.
        False, None, msg   -> si debe ir a pendientes.
    """

    booking_number = booking["Booking Number"]

    # =========================
    # DURACIONES
    # =========================
    if not utils.check_hotel_durations(booking, ruta_pendientes):
        msg = f"Booking {booking_number} omitido por duración inválida"
        return False, None, msg

    # =========================
    # PASAJEROS
    # =========================
    pasajeros = booking["Passengers"]

    if not pasajeros:
        msg = f"Booking {booking_number} no tiene pasajeros"
        return False, None, msg

    pasajero = pasajeros[0]

    client_name = pasajero["First Name"].strip()
    client_surname = pasajero["Last Name"].strip()

    if not client_name or not client_surname:
        msg = f"Booking {booking_number} no tiene nombre o apellido de pasajero"
        return False, None, msg

    # =========================
    # FECHAS
    # =========================
    check_in = booking["Departure Date"].strip()
    check_out = booking["Return Date"].strip()

    if not check_in or not check_out:
        msg = f"Booking {booking_number} no tiene Departure Date o Return Date"
        return False, None, msg

    try:
        check_in_date = datetime.strptime(check_in, "%m/%d/%Y").date()
        check_out_date = datetime.strptime(check_out, "%m/%d/%Y").date()
    except ValueError:
        msg = f"Booking {booking_number} tiene fechas inválidas: {check_in} -> {check_out}"
        return False, None, msg

    fecha_minima = datetime.strptime("10/01/2025", "%m/%d/%Y").date()

    if check_in_date < fecha_minima:
        msg = f"Booking {booking_number} tiene Departure Date anterior a octubre 2025: {check_in}"
        return False, None, msg

    # =========================
    # HOTELES
    # =========================
    booking_hotels = booking["Hotels"]

    if not booking_hotels:
        msg = f"Booking {booking_number} no tiene hoteles"
        return False, None, msg

    h = booking_hotels[0]

    hotel_name = h["Hotel Name"].strip()
    room_type = h["Room Type"].strip()

    if not hotel_name:
        msg = f"Booking {booking_number} tiene hotel sin nombre"
        return False, None, msg

    # Solo usamos el hotel para el formulario
    hotel_mapped, room_mapped = mapping.map_pair(hotels,hotel_name,room_type)

    if hotel_mapped is None or not hotel_mapped.strip():
        msg = f"No se encontró el mapeo para {hotel_name} - {room_type}"
        return False, None, msg

    # =========================
    # INVOICE
    # =========================
    invoice_path = os.path.abspath(
        os.path.join(RUTA_INVOICES, f"Invoice {booking_number}.pdf")
    )

    if not os.path.isfile(invoice_path):
        msg = f"No existe invoice para booking {booking_number}: {invoice_path}"
        return False, None, msg

    # =========================
    # DATOS LISTOS PARA SELENIUM
    # =========================
    datos = {
        "booking_number": booking_number,
        "booking_no": booking_number,
        "client_name": client_name,
        "client_surname": client_surname,
        "check_in": check_in,
        "check_out": check_out,
        "rooms_count": str(len(booking_hotels)),
        "hotel_mapped": hotel_mapped,
        "invoice_path": invoice_path,
    }

    return True, datos, None

def refrescar_y_esperar_menu(driver):
    driver.refresh()
    time.sleep(5)

    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (By.XPATH, '/html/body/div[1]/header/div[1]/div/ul/li[2]/button')
        )
    )

    logging.info("Página refrescada y menú disponible")
    
def cerrar_modal_confirmacion_o_refrescar(driver, booking_number):
    """
    Cierra el modal de confirmación después de Save.
    Si no se puede cerrar, refresca la página.
    No debe lanzar error hacia register_bookings, porque el booking ya fue enviado.
    """

    try:
        close_success_modal = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="claim-points-form-sent"]/div/div/header/button')
            )
        )

        time.sleep(0.5)

        try:
            close_success_modal.click()
        except Exception:
            driver.execute_script("arguments[0].click();", close_success_modal)

        WebDriverWait(driver, 20).until(
            EC.invisibility_of_element_located((By.ID, "claim-points-form-sent"))
        )

        logging.info(f"Modal de confirmación cerrado para booking {booking_number}")
        time.sleep(2)
        return True

    except Exception as e:
        logging.warning(
            f"No se pudo cerrar modal de confirmación para booking {booking_number}: {e}"
        )

        try:
            driver.refresh()
            time.sleep(5)

            WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '/html/body/div[1]/header/div[1]/div/ul/li[2]/button')
                )
            )

            logging.info(
                f"Página refrescada después de no cerrar modal de confirmación para booking {booking_number}"
            )

        except Exception as refresh_error:
            logging.warning(
                f"No se pudo refrescar después del modal de confirmación para booking {booking_number}: {refresh_error}"
            )

        return False
    
def cerrar_todo_despues_error_fechas(driver, booking_number):
    """
    Limpia la pantalla cuando falla la selección de fechas.
    Intenta cerrar datepicker, modal de confirmación y modal principal.
    Luego refresca para dejar la página lista para el siguiente booking.
    """

    logging.info(f"Limpiando pantalla después de error en fechas para booking {booking_number}")

    # =========================
    # 1. CERRAR DATEPICKER / CALENDARIO
    # =========================
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(1)
        logging.info("ESC enviado para cerrar calendario/date picker")
    except Exception as e:
        logging.warning(f"No se pudo cerrar calendario con ESC: {e}")

    # =========================
    # 2. CERRAR MODAL DE CONFIRMACIÓN SI EXISTE
    # =========================
    try:
        close_success_buttons = driver.find_elements(
            By.XPATH,
            '//*[@id="claim-points-form-sent"]/div/div/header/button'
        )

        close_success_buttons_visibles = [
            btn for btn in close_success_buttons
            if btn.is_displayed()
        ]

        for btn in close_success_buttons_visibles:
            try:
                driver.execute_script("arguments[0].click();", btn)
                logging.info("Modal de confirmación cerrado después de error en fechas")
                time.sleep(1)
            except Exception as e:
                logging.warning(f"No se pudo cerrar modal de confirmación: {e}")

    except Exception as e:
        logging.warning(f"No se pudo revisar modal de confirmación: {e}")

    # =========================
    # 3. CERRAR MODAL PRINCIPAL / FORMULARIO
    # =========================
    try:
        close_buttons = driver.find_elements(
            By.CSS_SELECTOR,
            "button.btn-close-round[data-micromodal-close]"
        )

        close_buttons_visibles = [
            btn for btn in close_buttons
            if btn.is_displayed()
        ]

        for btn in close_buttons_visibles:
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                    btn
                )
                time.sleep(0.2)
                driver.execute_script("arguments[0].click();", btn)
                logging.info("Modal/formulario cerrado después de error en fechas")
                time.sleep(1)
            except Exception as e:
                logging.warning(f"No se pudo cerrar modal/formulario: {e}")

    except Exception as e:
        logging.warning(f"No se encontraron botones de cierre de formulario: {e}")

    # =========================
    # 4. CERRAR OVERLAYS QUE QUEDEN
    # =========================
    try:
        overlays = driver.find_elements(By.CSS_SELECTOR, ".modal__overlay")

        overlays_visibles = [
            ov for ov in overlays
            if ov.is_displayed()
        ]

        for overlay in overlays_visibles:
            try:
                driver.execute_script("arguments[0].click();", overlay)
                logging.info("Overlay cerrado después de error en fechas")
                time.sleep(1)
            except Exception as e:
                logging.warning(f"No se pudo cerrar overlay: {e}")

    except Exception as e:
        logging.warning(f"No se pudieron revisar overlays: {e}")

    # =========================
    # 5. REFRESH FINAL
    # =========================
    try:
        driver.refresh()
        time.sleep(5)

        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, '/html/body/div[1]/header/div[1]/div/ul/li[2]/button')
            )
        )

        logging.info("Página refrescada y menú disponible después de error en fechas")

    except Exception as refresh_error:
        logging.warning(f"No se pudo refrescar después de error en fechas: {refresh_error}")
        raise
    
def register_bookings(driver, bookings_del_agente):
    """
    Esta función debe registrar SOLO los bookings asignados a ese agente.
    Aquí dejas tu lógica actual de Selenium para recorrer booking por booking.
    """
    driver.refresh()
    time.sleep(1)
    menu = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/header/div[1]/div/ul/li[2]/button')))
    i = 0

    while (i < TO_PROCESS) and (i < len(bookings_del_agente)):
        booking = bookings_del_agente[i]
        booking_number = booking["Booking Number"]

        try:
            logging.warning(f"Procesando booking {booking_number}")

            # ==================================================
            # VALIDACIONES ANTES DE ABRIR MODAL
            # ==================================================
            es_valido, datos, msg = validar_booking_antes_de_modal(booking,RUTA_PENDIENTES)

            if not es_valido:
                logging.warning(msg)
                utils.register_pending(RUTA_PENDIENTES, booking_number, utils.limpiar_mensaje_pendiente(msg))
                i += 1
                continue

            # Datos ya validados
            booking_no = datos["booking_no"]
            client_name = datos["client_name"]
            client_surname = datos["client_surname"]
            check_in = datos["check_in"]
            check_out = datos["check_out"]
            rooms_count = datos["rooms_count"]
            hotel_mapped = datos["hotel_mapped"]
            invoice_path = datos["invoice_path"]

            # ==================================================
            # SOLO SI PASÓ VALIDACIONES, ABRIR MODAL
            # ==================================================
            menu = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/header/div[1]/div/ul/li[2]/button')))
            menu.click()
            logging.info("Menú abierto")
            time.sleep(SLEEP_TIME)
            
            mypoints = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="nav-item-3"]')))
            mypoints.click()
            logging.info("Sección de puntos abierta")
            time.sleep(SLEEP_TIME)
            try:
                boton = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="panel-for-item-3912"]/div/div/nav/ul/li[1]/a')))
                driver.execute_script("""arguments[0].setAttribute('aria-expanded', 'true');arguments[0].click();""", boton)

                logging.info("Formulario de registro abierto")
                time.sleep(7)
                next_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="points-modal-nav-content"]/div/div[1]/button')))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});",next_btn)
                time.sleep(0.5)
                try:
                    next_btn.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", next_btn)
            except Exception as e:
                logging.error(f"No se pudo abrir el formulario Earn Points: {e}")
            
            # =========================
            # HOTEL
            # =========================
            hotel_select = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "hotel")))
            Select(hotel_select).select_by_visible_text(hotel_mapped)
            logging.info(f"Hotel seleccionado: {hotel_mapped}")
            time.sleep(SLEEP_TIME)

            # =========================
            # BOOKING NO
            # =========================
            utils.robust_type(driver, (By.ID, "reservation_locator"), booking_no)
            logging.info(f"Booking No escrito: {booking_no}")

            # =========================
            # CHECK-IN Y CHECK-OUT
            # =========================
            try:
                seleccionar_rango_fechas_calendario(driver, check_in, check_out)
                logging.info(f"Check-in y Check-out seleccionados: {check_in} -> {check_out}")

            except Exception as e:
                msg = f"Error seleccionando fechas para booking {booking_number}: {e}"
                logging.error(msg)

                utils.register_pending(RUTA_PENDIENTES,booking_number,utils.limpiar_mensaje_pendiente(msg))
                i += 1

                try:
                    cerrar_todo_despues_error_fechas(driver, booking_number)
                except Exception as refresh_error:
                    logging.warning(f"No se pudo refrescar después de error en fechas: {refresh_error}")
                    return False

                continue
            # =========================
            # CLIENT NAME
            # =========================
            utils.robust_type(driver, (By.ID, "name"), client_name)
            logging.info(f"Client name escrito: {client_name}")

            # =========================
            # CLIENT SURNAME
            # =========================
            utils.robust_type(driver, (By.ID, "last_name"), client_surname)
            logging.info(f"Client surname escrito: {client_surname}")

            # =========================
            # NUMBER OF ROOMS
            # =========================
            rooms_el = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "number_of_rooms")))
            Select(rooms_el).select_by_value(rooms_count)
            logging.info(f"Number of rooms seleccionado: {rooms_count}")

            
            # =========================
            # UPLOAD CONFIRMATION
            # =========================
            logging.info(f"Buscando invoice en: {invoice_path}")
            upload_input = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//input[@type='file' and @name='file']")))
            driver.execute_script("arguments[0].style.display = 'block';""arguments[0].style.visibility = 'visible';""arguments[0].style.opacity = 1;",upload_input)
            upload_input.send_keys(invoice_path)

            logging.info(f"Invoice subido: {invoice_path}")
            time.sleep(2)

            # =========================
            # SUBMIT
            # =========================
            if CLICK:
                submit_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='commit' and @value='Save']")))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});",submit_btn)
                time.sleep(0.5)
                submit_btn.click()

                logging.info(f"Booking {booking_number} enviado con Save")

                # =========================
                # CERRAR MODAL DE CONFIRMACIÓN
                # =========================
                cerrar_modal_confirmacion_o_refrescar(driver, booking_number)

            else:
                logging.info(f"CLICK=False, booking {booking_number} no enviado")
                
            
            utils.register_done(RUTA_DONE, booking_number)

            logging.info(f"Booking {booking_number} procesado correctamente")
            i += 1

        except Exception as e:
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(1)
            except:
                pass
            cerrar_formulario_y_menu(driver)
            msg = f"Error procesando booking {booking_number}: {e}"
            logging.error(msg)
            utils.register_pending(RUTA_PENDIENTES, booking_number, utils.limpiar_mensaje_pendiente(msg))
            i += 1
            try:
                driver.refresh()
                time.sleep(5)
                WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/header/div[1]/div/ul/li[2]/button')))
                logging.info("Página refrescada y menú disponible después del error")
            except Exception as refresh_error:
                logging.warning(f"No se pudo refrescar correctamente después del error: {refresh_error}")
    return True


def main():
    driver = None

    try:
        configurar_logging()

        bookings = cargar_bookings(RUTA_JSONS, TO_PROCESS)
        total_bookings = len(bookings)

        agentes_activos = obtener_agentes_activos(AGENTES)
        total_agentes = len(agentes_activos)

        if total_bookings == 0:
            logging.warning("No hay bookings para procesar.")
            return

        if total_agentes == 0:
            logging.error("No hay agentes activos que necesiten puntos.")
            return

        reparto = repartir_bookings(bookings, agentes_activos)

        logging.warning(f"Total de bookings: {total_bookings}")
        logging.warning(f"Agentes activos: {total_agentes}")

        for agente in agentes_activos:
            nombre = agente["name"]
            code = agente["code"]
            password = agente["password"]
            mis_bookings = reparto[nombre]

            logging.warning(f"{nombre} ({code}) -> {len(mis_bookings)} bookings asignados")
        
        ruta_reparto = os.path.join(BASE_DIR, "json", "reparto_agentes.json")
        guardar_resumen_reparto(reparto, ruta_reparto)

        for agente in agentes_activos:
            nombre = agente["name"]
            code = agente["code"]
            password = agente["password"]
            mis_bookings = reparto[nombre]

            if not mis_bookings:
                logging.info(f"{nombre} no tiene bookings asignados. Se omite.")
                continue

            logging.warning(f"=== Procesando agente: {nombre} ({code}) ===")
            driver = crear_driver()

            try:
                logged = login(driver, nombre, code, password)

                if not logged:
                    msg = f"No se pudo iniciar sesión con {nombre}"
                    logging.error(msg)
                    for booking in mis_bookings:
                        utils.register_pending(RUTA_PENDIENTES,booking["Booking Number"],utils.limpiar_mensaje_pendiente(msg))
                    continue

                register_bookings(driver, mis_bookings)

            except Exception as e:
                msg = f"Fallo con el agente {nombre}: {e}"
                logging.critical(msg)
                for booking in mis_bookings:utils.register_pending(RUTA_PENDIENTES,booking["Booking Number"],utils.limpiar_mensaje_pendiente(msg))

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
        logging.warning("Proceso terminado.")

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