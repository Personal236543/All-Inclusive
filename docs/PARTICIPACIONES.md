# Participaciones

El proyecto se desarrolló entre diciembre de 2024 y septiembre de 2026 en un repositorio privado. Esta versión pública arranca con un historial nuevo para no exponer credenciales ni datos de clientes; lo que sigue reconstruye quién hizo qué a partir del historial original (46 commits).

| Persona | GitHub | Periodo | Commits |
|---|---|---|---|
| Sofia Rodriguez | [@Sofiro11](https://github.com/Sofiro11) | abr 2025 – sep 2026 | 28 |
| Juanes Alvarez | [@Onstrax](https://github.com/Onstrax) | dic 2024 – ene 2025 | 18 |

## Juanes Alvarez — base del proyecto (dic 2024 – ene 2025)

Construyó la primera versión funcional con un solo hotel:

- **Extractor del panel de All Inclusive Outlet** (`all_inclusive/all_inclusive.py`): login, filtros de búsqueda, extracción de cada reserva a JSON, impresión de la factura en PDF y registro de la comisión.
- **Primer bot de hotel: Karisma** (`hoteles/karisma/karisma.py`, `karisma_mapping.py`): login, formulario de registro, calendarios y botones de navegación del portal.
- **Utilidades base**: `utils/mapping.py` (mapeo de hotel y habitación), el registro en JSON (`register`) y `clear_runs.py` (limpieza entre ejecuciones).
- **Modularización inicial y `script_runner.py`** como punto de entrada único (ene 2025).

## Sofia Rodriguez — expansión, mantenimiento y operación (abr 2025 – sep 2026)

Convirtió el prototipo de un solo hotel en una herramienta para varias cadenas y la mantuvo en producción:

- **Nuevos bots de hotel**
  - *Lomas* y *Dominican Republic Tourism* (abr 2025)
  - *Jamaica One Love*, *Iberostar StarAgents* y *Palladium Connect* (jul 2025)
  - Mapeo de *MyBookingRewards* (ago 2025)
- **Archivos de mapeo**: más de 2.000 líneas que traducen nombres de hotel y habitación de AIO a cada portal (Dominican, Jamaica, Iberostar, Lomas, Karisma).
- **Iberostar con varios agentes** (`hoteles/iberostar/iberostar.py`): reparto *round-robin* de reservas entre cuentas de agente, login y logout por agente, selección de rangos en el calendario y recuperación ante errores de modales.
- **Conciliación VAX** (`vax/vax.py`, `vax/vax2.py`, oct 2025 – may 2026): cruce de los resúmenes semanales de VAX con el panel de AIO y actualización de los CSV.
- **Reestructuración del repositorio** a `hoteles/<cadena>/` con un contrato común por módulo (ago 2025).
- **Utilidades de robustez** (`utils/utils.py`):
  - `robust_type`, para campos con autocompletado
  - normalización de texto
  - registro de pendientes con su motivo
  - validación de duraciones y filtrado de reservas pasadas o repetidas
- **Operación**:
  - `utils/act.py`, que quita de la cola las reservas procesadas y guarda un backup
  - limpieza por hotel ampliada en `clear_runs.py`
  - orquestación de flujos en `script_runner.py`, con registro de ejecuciones y notificación por WhatsApp (Twilio)
- **Publicación** (oct 2026):
  - credenciales movidas a `.env` (`utils/config.py`)
  - quitados los datos de clientes y los archivos generados en las ejecuciones
  - datos de ejemplo y documentación
