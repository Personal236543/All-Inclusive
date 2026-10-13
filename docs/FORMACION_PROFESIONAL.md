# Aporte a la formación profesional

Este proyecto fue software usado en la operación real de una agencia de viajes, no un ejercicio académico. Este documento resume las competencias que se aplicaron y los problemas que se resolvieron, con referencias al código.

## Contexto

- **Cliente:** All Inclusive Outlet, agencia de viajes.
- **Problema:** cada reserva había que revisarla en el panel de comisiones, descargar su factura, marcar la comisión y volver a capturarla a mano en el portal de rewards de cada cadena hotelera. Cada portal tiene su propia interfaz y sus propios nombres de hotel y habitación.
- **Rol:** desarrollo y mantenimiento de la herramienta durante aproximadamente 17 meses (abr 2025 – sep 2026), después de una primera versión hecha en equipo (ver [PARTICIPACIONES.md](PARTICIPACIONES.md)).

## Competencias técnicas

| Área | Evidencia en el repositorio |
|---|---|
| Automatización web con Selenium | Seis bots para portales distintos, cada uno con su login, formularios, calendarios (`select_gijgo_date_from_calendar`, `seleccionar_rango_fechas_calendario`), modales y overlays |
| Manejo de interfaces inestables | Esperas explícitas (`WebDriverWait`), reintentos, `robust_type` con *debounce* para autocompletados y recuperación tras errores (`cerrar_modal_confirmacion_o_refrescar`, `cerrar_todo_despues_error_fechas`) |
| Integración y normalización de datos | Mapeo entre catálogos de distintos sistemas (`*_mapping.py`), normalización Unicode para comparar textos y conciliación de CSV contra el panel (`vax/`) |
| Diseño modular | Contrato común por hotel (`COMMISSION_RULE`, `main()`, `hotels`) y un orquestador único (`script_runner.py`) que carga cada módulo dinámicamente con `importlib` |
| Trazabilidad y operación | Logs por flujo, registro de reservas hechas y pendientes con su motivo, backups antes de modificar la cola y registro de cada ejecución |
| Lógica de negocio | Reparto de pasajeros entre habitaciones, validación de fechas y duraciones, reparto de reservas entre agentes y reglas de comisión por cadena |
| Seguridad y manejo de datos | Antes de publicar: auditoría de secretos y datos personales, configuración por variables de entorno y un historial nuevo para no exponer información de clientes |

## Retos y aprendizajes

- **Mantener software en producción:** los portales cambian sin aviso. Los selectores por posición y por XPath absoluto se rompen fácilmente, y eso obliga a diseñar pensando en las fallas: cada reserva que falla queda en `pendientes.json` con su motivo en lugar de detener la ejecución.
- **Crecer de un hotel a seis:** pasar de un script a un paquete con estructura común (reestructuración de ago 2025) fue lo que permitió agregar cadenas nuevas sin duplicar la lógica del panel.
- **Calidad de datos antes que automatización:** la mayor parte del trabajo de cada nuevo hotel estuvo en el mapeo de nombres, no en el bot. Más de 2.000 líneas de mapeo muestran que la integración entre sistemas es sobre todo un problema de datos.
- **Hacer el proceso seguro de ejecutar:** banderas como `CLICK` (probar sin enviar nada), `TO_PROCESS` (límite por lote) y `SLEEP_TIME` (ritmo por portal) permiten correr el proceso de forma controlada sobre sistemas reales.
- **Higiene de credenciales:** tener las credenciales escritas en el código fue una deuda que se pagó al publicar. Desde el inicio deben venir de la configuración.
- **Trabajo colaborativo:** continuar y ampliar una base de código escrita por otra persona.

## Tecnologías

Python 3.11 · Selenium WebDriver (Chrome) · JSON/CSV · Twilio API · Git/GitHub
