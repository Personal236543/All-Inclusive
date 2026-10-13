import os
import json
import time
import logging
import unicodedata
from iberostar.iberostar_mapping import hotels
from utils import mapping, register1
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from utils import config


CLICK = True

SLEEP_TIME = 1 #No menos de 2
TO_PROCESS = 500 #No mas de 70
HEADLESS = False
LOGGING_LEVEL = logging.WARNING  # DEBUG, INFO, WARNING, ERROR, CRITICAL
USERNAME = config.get("PALLADIUM_USERNAME")
PASSWORD = config.get("PALLADIUM_PASSWORD")
COMMISSION_RULE = "Palladium Connect"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_JSONS = os.path.join(BASE_DIR, "json", "bookings.json")
RUTA_DONE = os.path.join(BASE_DIR, "json", "done.json")
RUTA_PENDIENTES = os.path.join(BASE_DIR, "json", "pendientes.json")
RUTA_LOGS = os.path.join(BASE_DIR, os.pardir, "logs", "palladium.log")
RUTA_DRIVER = os.path.join(BASE_DIR, os.pardir, "chromedriver.exe")

OVERLAY_COUNTER = 3
HOTELS = hotels

os.makedirs(os.path.dirname(RUTA_JSONS), exist_ok=True)
