import os
import json
import time
import logging
import unicodedata
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

SLEEP_TIME = 0.2
TO_PROCESS = 500
HEADLESS = False
DEPARTURE_DATE_FROM = "01/01/2025"
DEPARTURE_DATE_TO = "02/28/2025"
COMMISSION_RULE = "default"
EJECUTABLE = script_runner.EJECUTABLE
LOGGING_LEVEL = logging.INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
USERNAME = config.get("AIO_USERNAME")
PASSWORD = config.get("AIO_PASSWORD")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_JSONS = os.path.join(BASE_DIR, os.pardir, "hoteles", EJECUTABLE, "json", "bookings.json")
RUTA_DONE = os.path.join(BASE_DIR, "json", "done.json")
RUTA_INVOICES = os.path.join(BASE_DIR, os.pardir, "hoteles", EJECUTABLE,"invoices")
RUTA_LOGS = os.path.join(BASE_DIR, "logs", "all_inclusive.log")
RUTA_DRIVER = os.path.join(BASE_DIR, os.pardir, "chromedriver.exe")

os.makedirs(RUTA_INVOICES, exist_ok=True)
os.makedirs(os.path.dirname(RUTA_JSONS), exist_ok=True)


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

        booking_status_dropdown = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="SearchForm"]/div/div/div[1]/div/div[4]/button')
            )
        )
        booking_status_dropdown.click()
        reviewed_option = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    '//*[@id="SearchForm"]/div/div/div[1]/div/div[4]/div/ul/li[3]/a/span[1]',
                )
            )
        )
        reviewed_option.click()
        time.sleep(SLEEP_TIME)

        registered_dropdown = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="SearchForm"]/div/div/div[1]/div/div[5]/button')
            )
        )
        registered_dropdown.click()
        no_option = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    '//*[@id="SearchForm"]/div/div/div[1]/div/div[5]/div/ul/li[3]/a/span[1]',
                )
            )
        )
        no_option.click()
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


def scrap_bookings(driver):
    try:
        logging.info("Iniciando extracción de bookings...")
        booking_table = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="form0"]/table'))
        )
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "tr"))
        )
        rows = booking_table.find_elements(By.TAG_NAME, "tr")
        logging.info(f"Total de bookings a procesar: {len(rows) - 1}")
        i = 0
        while (i < TO_PROCESS + 1) and (i < len(rows)):
            if i == 0:
                i += 1
                continue
            time.sleep(SLEEP_TIME)
            cells = rows[i].find_elements(By.TAG_NAME, "td")
            booking = cells[11].find_element(By.TAG_NAME, "a")
            booking_no = booking.text

            logging.info(f"Procesando booking: {booking_no}")
            driver.execute_script("window.open(arguments[0].href);", booking)
            driver.switch_to.window(driver.window_handles[-1])

            time.sleep(SLEEP_TIME)
            scrapped = process_booking(driver, booking_no)
            (
                logging.info(f"Booking {booking_no} procesado exitosamente.")
                if scrapped
                else logging.warning(f"No se pudo procesar el booking: {booking_no}")
            )

            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            i += 1
        return True
    except Exception as e:
        logging.error(f"Error en scrap_bookings: {e}")
        return False


def process_booking(driver, booking_no):
    try:
        logging.info("Procesando detalles del booking...")
        tab_list = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "MainTabs"))
        )
        tabs = tab_list.find_elements(By.TAG_NAME, "li")
        tabs[3].click()
        time.sleep(SLEEP_TIME)

        booking = {
            "Booking Number": "default",
            "Client Name": "default",
            "Date Entered": "default",
            "Departure Date": "default",
            "Supplier": "default",
            "Destination": "default",
            "Return Date": "default",
            "Supplier Price": "default",
            "Passengers": [],
            "Hotels": [],
            "Airline": "default",
        }

        booking["Booking Number"] = booking_no

        data_table = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="Bookings"]/table'))
        )
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "tr"))
        )
        data_rows = data_table.find_elements(By.TAG_NAME, "tr")
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "td"))
        )
        index = 0
        while index < len(data_rows):
            time.sleep(SLEEP_TIME)
            if index == 0:
                tds = data_rows[index].find_elements(By.TAG_NAME, "td")
                booking["Client Name"] = tds[1].text.title()
                booking["Supplier"] = (
                    tds[3].text
                    if (utils.normalize_string(tds[3].text) == utils.normalize_string("DestiWorld"))
                    else "Travel Impressions"
                )
                booking["Supplier Price"] = tds[7].text[1::]
            elif index == 3:
                tds = data_rows[index].find_elements(By.TAG_NAME, "td")
                booking["Date Entered"] = tds[1].text.split(" ")[0]
            elif index == 4:
                tds = data_rows[index].find_elements(By.TAG_NAME, "td")
                booking["Destination"] = tds[3].text
            elif index == 5:
                tds = data_rows[index].find_elements(By.TAG_NAME, "td")
                booking["Departure Date"] = tds[1].text
                booking["Return Date"] = tds[3].text
            index += 1

        passengers_table = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="Components"]/table[1]'))
        )
        passengers_rows = passengers_table.find_elements(By.TAG_NAME, "tr")
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "td"))
        )
        index = 1
        while index < len(passengers_rows):
            passenger = {
                "First Name": "default",
                "Last Name": "default",
                "Age": "default",
                "Type": "default",
            }
            time.sleep(SLEEP_TIME)
            ptds = passengers_rows[index].find_elements(By.TAG_NAME, "td")
            passenger["First Name"] = ptds[0].text.title()
            passenger["Last Name"] = ptds[2].text.title()
            passenger["Age"] = ptds[5].text
            passenger["Type"] = ptds[6].text if ptds[6].text != "" else "adult"
            booking["Passengers"].append(passenger)
            index += 1

        hotel_table = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="Components"]/table[2]'))
        )
        time.sleep(SLEEP_TIME)
        hotel_rows = hotel_table.find_elements(By.TAG_NAME, "tr")
        index = 1
        while index < len(hotel_rows):
            hotel = {
                "Hotel Name": "default",
                "Room Type": "default",
                "Duration": "default",
            }
            hotel_data = hotel_rows[1].find_elements(By.TAG_NAME, "td")
            hotel["Hotel Name"] = hotel_data[0].text
            hotel["Room Type"] = hotel_data[1].text
            hotel["Duration"] = hotel_data[5].text
            booking["Hotels"].append(hotel)
            index += 1

        ariline_table = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="Components"]/table[4]'))
        )
        time.sleep(SLEEP_TIME)
        airline_rows = ariline_table.find_elements(By.TAG_NAME, "tr")
        if len(airline_rows) > 1:
            booking["Airline"] = (
                airline_rows[1].find_elements(By.TAG_NAME, "td")[0].text
            )

        saved_json = save_json(booking)
        if not saved_json:
            logging.warning(f"No se pudo guardar el booking {booking_no}.")

        saved_pdf = save_pdf(driver)
        charged = (
            charge_booking(driver, booking)
            if saved_pdf
            else logging.warning(f"No se pudo guardar el PDF del booking {booking_no}.")
        )
        if not charged:
            logging.warning(f"No se pudo cobrar la comisión del booking {booking_no}.")
            return False

        logging.info("Detalles del booking procesados correctamente.")
        return True
    except Exception as e:
        logging.error(f"Error en process_booking: {e}")
        return False


def save_json(booking):
    try:
        register1.register1(RUTA_JSONS, booking)
        logging.info(f"Booking guardado correctamente en el Json")
        return True
    except Exception as e:
        logging.error(f"Error guardando el booking: {e}")
        return False


def save_pdf(driver):
    try:
        logging.info("Guardando PDF...")
        ul = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "ulBookings"))
        )
        invoices = ul.find_elements(By.TAG_NAME, "li")[3]
        invoices.click()
        time.sleep(SLEEP_TIME)

        invoice_table = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    '//*[@id="MainContent_EnquiryBookings_ucFinancials_upFinancials"]/table',
                )
            )
        )
        invoice_rows = invoice_table.find_elements(By.TAG_NAME, "tr")
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "td"))
        )
        index = 0
        while index < len(invoice_rows):
            if index == 0:
                index += 1
                continue
            time.sleep(SLEEP_TIME)
            itds = invoice_rows[index].find_elements(By.TAG_NAME, "td")
            satatus_box = itds[3].find_element(By.TAG_NAME, "div")
            status = satatus_box.text
            if utils.normalize_string(status) == utils.normalize_string("Live"):
                view_btn = itds[6].find_element(By.TAG_NAME, "a")
                view_btn.click()
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(SLEEP_TIME)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.ID, "img1"))
                )
                driver.execute_script("window.print();")
                time.sleep(SLEEP_TIME)
                logging.info("PDF guardado correctamente.")
                driver.close()
                time.sleep(SLEEP_TIME)
                driver.switch_to.window(driver.window_handles[1])
            index += 1
        logging.info("Termina el proceso de guardar el PDF.")
        return True
    except IndexError:
        logging.info("Parece no afectar nada.")
        return True
    except Exception as e:
        logging.error(f"Error en save_pdf: {e}")
        return False


def charge_booking(driver, booking):
    try:
        logging.info("Cobrando la comisión...")
        ul = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "ulBookings"))
        )
        commissions = ul.find_elements(By.TAG_NAME, "li")[2]
        commissions.click()
        time.sleep(SLEEP_TIME)
        
        commission_table = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.ID, 'MainContent_EnquiryBookings_Commission1_gvRules')
            )
        )
        commission_rows = commission_table.find_elements(By.TAG_NAME, 'tr')
        for row in commission_rows[1:]:
            time.sleep(SLEEP_TIME)
            commission_data = row.find_elements(By.TAG_NAME, 'td')
            if utils.normalize_string(commission_data[12].text) == utils.normalize_string(COMMISSION_RULE):
                time.sleep(SLEEP_TIME)
                buttons = commission_data[0].find_elements(By.TAG_NAME, 'div')
                for b in buttons:
                    if utils.normalize_string(b.text) == utils.normalize_string('REGISTER') and CLICK:
                        #DESCOMENTAR
                        driver.execute_script("arguments[0].click()", b)
                        utils.register_done(booking,RUTA_DONE)

        logging.info("Termina el proceso de cobrar la comisión.")
        return True
    except Exception as e:
        logging.error(f"Error en charge_boking: {e}")
        return False
    
    
def register_done(booking):
    try:
        logging.info(f'Registrando booking completado: {booking["Booking Number"]}...')
        register1.register1(RUTA_DONE, booking["Booking Number"])
        logging.info(f"Booking {booking['Booking Number']} añadido a {RUTA_DONE}.")
        return True
    except Exception as e:
        logging.error(f"Error en register_done: {e}")
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
        options = Options()
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--start-maximized")
        if HEADLESS:
            options.add_argument("--headless")
        options.add_argument("--kiosk-printing")
        options.add_experimental_option(
            "prefs",
            {
                "savefile.default_directory": RUTA_INVOICES,
                "printing.print_preview_sticky_settings.appState": '{"recentDestinations":[{"id":"Save as PDF","origin":"local","account":"","name":"Save as PDF"}],"selectedDestinationId":"Save as PDF","version":2}',
            },
        )

        logging.basicConfig(
            level=LOGGING_LEVEL,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(RUTA_LOGS), logging.StreamHandler()],
        )

        logging.info("Iniciando driver...")
        service = Service(executable_path=RUTA_DRIVER)
        driver = webdriver.Chrome(service=service, options=options)
        logged = login(driver)
        ready_to_search = (
            search_bookings(driver)
            if logged
            else logging.error("No se pudo iniciar sesión.")
        )
        scrapped = (
            scrap_bookings(driver)
            if ready_to_search
            else logging.error("No se pudo obtener los bookings")
        )
        (
            logging.info("Extracción completada con éxito.")
            if scrapped
            else logging.warning("No se pudo procesar todos los bookings.")
        )
        logging.info("Cerrando sesión...")
        logedout = logout(driver)
        (
            logging.info("Sesión cerrada.")
            if logedout
            else logging.error("No se pudo cerrar sesión.")
        )
    except Exception as e:
        logging.critical(f"Algo salió mal :( \nError: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
