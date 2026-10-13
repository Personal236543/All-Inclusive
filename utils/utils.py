

import json
import os
from utils import register1 as register1
import logging
import unicodedata
import csv
from datetime import datetime
import platform, time, logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (ElementNotInteractableException,StaleElementReferenceException,TimeoutException,InvalidElementStateException,)



def register_pendin(ruta, booking):
    try:
        logging.info(f'Registrando booking pendiente: {booking["Booking Number"]}...')
        register1.register1(ruta, booking["Booking Number"])
        logging.info(f"Booking {booking['Booking Number']} añadido a {ruta}.")
        return True
    except Exception as e:
        logging.error(f"Error en register_pending: {e}")
        return False
    
def register_pending(ruta, booking_no, mensaje):
    """
    Añade al JSON una entrada {booking_no: "mensaje"} usando register().
    El archivo queda como una LISTA de dicts: [{...}, {...}, ...]
    """
    try:
        payload = {str(booking_no): str(mensaje)}
        logging.info(f"Registrando booking pendiente: {booking_no} -> {mensaje}")
        register1.register1(ruta, payload)
        logging.info(f"Booking {booking_no} añadido a {ruta}.")
        return True
    except Exception as e:
        logging.error(f"Error en register_pending: {e}")
        return False

def register_done(ruta,booking):
    try:
        logging.info(f'Registrando booking completado: {booking}...')
        register1.register1(ruta, booking)
        logging.info(f"Booking {booking} añadido a {ruta}.")
        return True
    except Exception as e:
        logging.error(f"Error en register_done: {e}")
        return False

import logging

def check_hotel_durations(booking, ruta_pendientes):
    """
    Verifica que todas las duraciones de los hoteles sean iguales
    SOLO si hay más de un hotel en el booking.

    Retorna:
        True  -> si pasa la verificación (o si hay 0/1 hotel)
        False -> si hay duración inválida o no coinciden (y registra en pendientes)
    """
    hotels = booking.get("Hotels", [])
    # Si hay 0 o 1 hotel, no hay nada que validar
    if len(hotels) <= 1:
        return True

    first_duration = None
    for h in hotels:
        raw = str(h.get("Duration", "")).strip()
        try:
            duration = int(raw)
        except (TypeError, ValueError):
            msg = f"Duration inválida en hotel '{h.get('Hotel Name')}' -> '{raw}'"
            logging.warning(msg)
            # fallar la verificación
            return False

        if first_duration is None:
            first_duration = duration
        elif duration != first_duration:
            msg = f"Duraciones no coinciden en booking {booking.get('Booking Number')} -> {first_duration} vs {duration}"
            logging.warning(msg)
            # fallar la verificación
            return False

    return True

def normalize_string(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii")

def robust_type(driver, locator, text, per_char_delay=0.06, debounce_ms=1000):
    """
    Escribe texto en un <input> de forma robusta:
    - Scroll + focus
    - Limpiar con Ctrl/⌘ + A, Backspace (con chord)
    - Reintentos si el elemento se vuelve stale
    - Fallback final: JS value + dispatch de 'input' y 'change'
    """
    wait = WebDriverWait(driver, 15)
    ctrl_key = Keys.COMMAND if platform.system().lower() == "darwin" else Keys.CONTROL
    chord_sel_all = [ctrl_key, "a"]

    def reacquire():
        return wait.until(EC.visibility_of_element_located(locator))

    el = wait.until(EC.element_to_be_clickable(locator))

    # Asegurar que sea visible y enfocado
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        driver.execute_script("arguments[0].focus();", el)
        try:
            el.click()
        except Exception:
            driver.execute_script("arguments[0].click();", el)
    except StaleElementReferenceException:
        el = reacquire()

    # Limpiar con selección total + backspace (más fiable que .clear())
    try:
        for key in chord_sel_all:
            el.send_keys(key)
        el.send_keys(Keys.BACKSPACE)
    except (ElementNotInteractableException, InvalidElementStateException, StaleElementReferenceException):
        # Reintenta una vez
        try:
            el = reacquire()
            driver.execute_script("arguments[0].focus();", el)
            el.send_keys(chord_sel_all)
            el.send_keys(Keys.BACKSPACE)
        except Exception as e:
            logging.warning(f"Ctrl/⌘+A falló ({type(e).__name__}). Intentando limpiar por JS…")
            try:
                driver.execute_script("arguments[0].value = '';", el)
                # Disparar eventos para Alpine x-model
                driver.execute_script("""
                    const el = arguments[0];
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                """, el)
            except StaleElementReferenceException:
                el = reacquire()
                driver.execute_script("arguments[0].value = '';", el)

    # Escribir letra por letra con tolerancia a stale
    for ch in text:
        try:
            el.send_keys(ch)
        except StaleElementReferenceException:
            el = reacquire()
            el.send_keys(ch)
        time.sleep(per_char_delay)

    # Esperar al debounce del x-model (1000 ms en tu HTML)
    time.sleep((debounce_ms / 1000.0) + 0.15)

    # Validación ligera del value (no todas las UIs reflejan el value de inmediato)
    try:
        val = (el.get_attribute("value") or "").strip()
        if not val:
            # Fuerza eventos por si la UI depende de ellos
            driver.execute_script("""
                const el = arguments[0];
                el.dispatchEvent(new Event('input', {bubbles:true}));
                el.dispatchEvent(new Event('change', {bubbles:true}));
            """, el)
    except StaleElementReferenceException:
        pass

    return el



def obtener_bookings_ordenados(nombre_csv):
    """
    Lee un archivo CSV en el directorio actual y devuelve una lista de Booking Numbers
    ordenados por Arrival Date (del más cercano al más lejano).
    """
    datos = []

    with open(nombre_csv, mode='r', encoding='utf-8-sig', newline='') as f:
        lector = csv.DictReader(f)
        for fila in lector:
            fecha_raw = fila.get("Arrival Date", "").strip()
            booking = fila.get("Booking Number", "").strip()

            if not fecha_raw or not booking:
                continue

            try:
                fecha = datetime.strptime(fecha_raw, "%d-%b-%y")
            except:
                continue

            datos.append((fecha, booking))

    datos.sort(key=lambda x: x[0])
    return [b[1] for b in datos]

def filtrar_bookings_realizados(ruta_bookings: str, ruta_done: str):
    with open(ruta_done, "r") as f:
        done_list = json.load(f)

    with open(ruta_bookings, "r") as f:
        all_bookings = json.load(f)

    bookings_filtrados = [
        booking for booking in all_bookings
        if booking.get("Booking Number") not in done_list
    ]

    with open(ruta_bookings, "w") as f:
        json.dump(bookings_filtrados, f, indent=4)
        
def eliminar_bookings_pasados(ruta_pendientes, ruta_bookings):
    try:
        # Cargar pendientes
        with open(ruta_pendientes, "r", encoding="utf-8") as f:
            pendientes = json.load(f)

        # Obtener los booking numbers que están "pasados de fecha"
        bookings_pasados = set()
        for entry in pendientes:
            for booking_number, mensaje in entry.items():
                if "es anterior a" in mensaje:
                    bookings_pasados.add(booking_number)

        logging.info(f"Bookings pasados detectados: {bookings_pasados}")

        # Cargar bookings actuales
        with open(ruta_bookings, "r", encoding="utf-8") as f:
            bookings = json.load(f)

        # Filtrar los que NO estén en bookings_pasados
        bookings_filtrados = [
            b for b in bookings
            if b.get("Booking Number") not in bookings_pasados
        ]

        # Guardar el archivo actualizado
        with open(ruta_bookings, "w", encoding="utf-8") as f:
            json.dump(bookings_filtrados, f, indent=4)

        logging.info(f"{len(bookings) - len(bookings_filtrados)} bookings eliminados de {ruta_bookings}")

    except Exception as e:
        logging.error(f"Error en eliminar_bookings_pasados: {e}")
        
def eliminar_reservas_repetidas_csv(ruta_csv):
    try:
        with open(ruta_csv, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames

        seen = set()
        rows_filtradas = []

        for row in rows:
            reservation_number = row.get("Reservation Number")
            if reservation_number not in seen:
                seen.add(reservation_number)
                rows_filtradas.append(row)

        with open(ruta_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_filtradas)

        logging.info(
            f"CSV depurado: {len(rows) - len(rows_filtradas)} registros duplicados eliminados."
        )

    except Exception as e:
        logging.error(f"Error al limpiar duplicados del CSV: {e}")
        
def limpiar_mensaje_pendiente(error):
    """
    Convierte errores largos de Selenium en razones cortas para pendientes.json.
    El log completo se sigue guardando con logging.error(...).
    """

    texto = str(error)

    if "no tiene Client Name" in texto:
        return "No tiene Client Name"

    if "Could not locate element with visible text" in texto:
        return "No se encontró una opción en un select"

    if "element click intercepted" in texto:
        return "Click bloqueado por modal/overlay"

    if "element not interactable" in texto:
        return "Elemento no interactuable"

    if "NoSuchElementException" in texto or "no such element" in texto:
        return "No se encontró un elemento en la página"

    if "TimeoutException" in texto or "timed out" in texto:
        return "Timeout esperando elemento"

    if "stale element reference" in texto:
        return "Elemento desactualizado en la página"

    if "Fallo con el agente" in texto:
        return "Falló el procesamiento del agente"

    if "No existe invoice" in texto:
        return texto

    if "No se encontró el mapeo" in texto:
        return texto

    if "fechas inválidas" in texto:
        return texto

    if "no tiene pasajeros" in texto:
        return texto

    if "no tiene hoteles" in texto:
        return texto
    if "Departure Date anterior a octubre 2025" in texto:
        return texto

    # Fallback: primera línea limpia
    return texto.splitlines()[0][:200]
