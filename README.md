# All-Inclusive — Automatización de comisiones y rewards hoteleros

Automatización con **Python + Selenium** desarrollada para All Inclusive Outlet, una agencia de viajes. Reemplaza un proceso manual: revisar cada reserva en el panel de comisiones, descargar su factura, marcar la comisión como registrada y volver a capturar la misma reserva en el portal de rewards de cada cadena hotelera (Karisma, Iberostar, Jamaica, Dominican, Palladium, Lomas…).

## Cómo funciona

```
Panel AIO ──scrape──► bookings.json ──► portal del hotel
   │                    │                    │
   ├─ factura PDF       ├─ mapeo hotel/room  ├─ done.json
   └─ REGISTER          └─ validaciones      └─ pendientes.json (con motivo)
```

1. **Extracción** (`all_inclusive/`): inicia sesión en el panel, filtra por regla de comisión y rango de fechas, y extrae pasajeros, hoteles y aerolínea de cada reserva a JSON. También guarda la factura en PDF y registra la comisión.
2. **Registro** (`hoteles/<cadena>/`): cada cadena tiene su propio bot y un archivo de mapeo que traduce los nombres de hotel y habitación de AIO a los del portal. Si una reserva no se puede mapear o ya pasó su fecha, se guarda en `pendientes.json` con el motivo para revisarla a mano.
3. **Conciliación VAX** (`vax/`): cruza los resúmenes semanales de VAX (CSV) con el panel y actualiza su estado.
4. **Limpieza** (`utils/act.py`, `utils/clear_runs.py`): quita de la cola las reservas ya procesadas, con un backup, y deja un registro de cada ejecución.

Algunos detalles técnicos:
- Reparto *round-robin* de reservas entre varias cuentas de agente (Iberostar).
- Escritura carácter por carácter con *debounce* para los campos con autocompletado (`utils.robust_type`).
- Pasajeros repartidos entre varias habitaciones de una misma reserva.
- Notificación opcional por WhatsApp (Twilio) al terminar.

## Uso

```bash
pip install -r requirements.txt
cp .env.example .env        # completar credenciales
python script_runner.py
```

Necesita un `chromedriver` compatible con tu versión de Chrome en la raíz del proyecto ([Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/)). Para elegir el flujo, cambia `EJECUTABLE` en `script_runner.py`. Para hacer una prueba sin enviar nada, pon `ALL_INCLUSIVE_CLICK` y `HOTEL_CLICK` en `False`.

En `examples/` hay datos ficticios que muestran el formato de entrada.

## Nota

Todos los datos de clientes, credenciales y archivos generados en las ejecuciones se quitaron de este repositorio. Los datos de ejemplo son inventados.

## Autoría

- **Sofia Rodriguez** ([@Sofiro11](https://github.com/Sofiro11)): expansión a seis cadenas hoteleras, Iberostar con varios agentes, conciliación VAX, reestructuración del proyecto y operación (2025–2026).
- **Juanes Alvarez** ([@Onstrax](https://github.com/Onstrax)): versión inicial, con el extractor del panel y el bot de Karisma (2024–2025).

Detalle en [docs/PARTICIPACIONES.md](docs/PARTICIPACIONES.md). El aporte a la formación profesional está en [docs/FORMACION_PROFESIONAL.md](docs/FORMACION_PROFESIONAL.md).
