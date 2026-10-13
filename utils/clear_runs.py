import os
import script_runner as sr

EJECUTABLE = sr.EJECUTABLE
CLEAR_JSONS = False
CLEAR_LOGS = True

ALL_INCLUSIVE_CLEAR_JSONS = True
ALL_INCLUSIVE_CLEAR_LOGS = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir))

RUTA_JSONS_HOTEL= os.path.join(PROJECT_DIR,"hoteles",EJECUTABLE,"json")
RUTA_LOGS_HOTEL = os.path.join(PROJECT_DIR,"hoteles",EJECUTABLE,"logs")
RUTA_INVOICES_HOTEL = os.path.join(PROJECT_DIR,"hoteles",EJECUTABLE,"invoices")
RUTA_JSONS_ALL_INCLUSIVE = os.path.join(PROJECT_DIR,"all_inclusive","json")
RUTA_LOGS_ALL_INCLUSIVE = os.path.join(PROJECT_DIR,"all_inclusive","logs")

def clear_file(archivo):
    try:
        with open(archivo, "w", encoding="utf-8") as f:
            pass

        print(f"   ✅ Archivo vaciado: {os.path.basename(archivo)}")
        return True

    except Exception as e:
        print(f"   ❌ Error al borrar el contenido de {archivo}: {e}")
        return False


def clear_files(ruta_directorio):
    try:
        print(f"📂 Ruta: {ruta_directorio}")

        if not os.path.exists(ruta_directorio):
            print(f"⚠️ El directorio {ruta_directorio} no existe.")
            return 0

        archivos = os.listdir(ruta_directorio)
        print(f"📌 Archivos encontrados: {len(archivos)}")

        if len(archivos) == 0:
            print("⚠️ No hay archivos para limpiar.")
            return 0

        limpiados = 0
        omitidos = 0

        for archivo in archivos:
            ruta_archivo = os.path.join(ruta_directorio, archivo)

            if os.path.isfile(ruta_archivo):
                if clear_file(ruta_archivo):
                    limpiados += 1
            else:
                print(f"   ⚠️ Omitido porque no es archivo: {archivo}")
                omitidos += 1

        print(f"✅ Archivos vaciados: {limpiados}")
        print(f"⚠️ Archivos omitidos: {omitidos}")

        return limpiados

    except Exception as e:
        print(f"❌ Error al borrar los archivos: {e}")
        return 0


def clear_dir(ruta_directorio):
    try:
        print(f"📂 Ruta: {ruta_directorio}")

        if not os.path.exists(ruta_directorio):
            print(f"⚠️ El directorio {ruta_directorio} no existe.")
            return 0

        archivos = os.listdir(ruta_directorio)
        print(f"📌 Archivos encontrados: {len(archivos)}")

        if len(archivos) == 0:
            print("⚠️ No hay archivos para eliminar.")
            return 0

        eliminados = 0
        errores = 0

        for archivo in archivos:
            ruta_archivo = os.path.join(ruta_directorio, archivo)

            try:
                os.remove(ruta_archivo)
                print(f"   ✅ Archivo eliminado: {archivo}")
                eliminados += 1

            except Exception as e:
                print(f"   ❌ Error eliminando {archivo}: {e}")
                errores += 1

        print(f"✅ Archivos eliminados: {eliminados}")
        print(f"❌ Errores: {errores}")

        return eliminados

    except Exception as e:
        print(f"❌ Error al borrar los archivos: {e}")
        return 0


def main():
    print("")
    print("========== LIMPIEZA DE ARCHIVOS ==========")
    print(f"🏨 Hotel seleccionado: {EJECUTABLE}")

    print("")
    print("⚙️ Configuración:")
    print(f"   CLEAR_JSONS: {CLEAR_JSONS}")
    print(f"   CLEAR_LOGS: {CLEAR_LOGS}")
    print(f"   CLEAR_INVOICES: {globals().get('CLEAR_INVOICES', False)}")
    print(f"   ALL_INCLUSIVE_CLEAR_JSONS: {ALL_INCLUSIVE_CLEAR_JSONS}")
    print(f"   ALL_INCLUSIVE_CLEAR_LOGS: {ALL_INCLUSIVE_CLEAR_LOGS}")

    total_limpiados = 0

    print("")
    if CLEAR_JSONS:
        print("🧹 Limpiando JSONS del hotel...")
        total_limpiados += clear_files(RUTA_JSONS_HOTEL)
    else:
        print("⏭️ JSONS del hotel omitidos.")

    print("")
    if CLEAR_LOGS:
        print("🧹 Limpiando LOGS del hotel...")
        total_limpiados += clear_files(RUTA_LOGS_HOTEL)
    else:
        print("⏭️ LOGS del hotel omitidos.")

    print("")
    if globals().get("CLEAR_INVOICES", False):
        print("🗑️ Limpiando INVOICES del hotel...")
        total_limpiados += clear_dir(RUTA_INVOICES_HOTEL)
    else:
        print("⏭️ INVOICES del hotel omitidos.")

    print("")
    if ALL_INCLUSIVE_CLEAR_JSONS:
        print("🧹 Limpiando JSONS de all_inclusive...")
        total_limpiados += clear_files(RUTA_JSONS_ALL_INCLUSIVE)
    else:
        print("⏭️ JSONS de all_inclusive omitidos.")

    print("")
    if ALL_INCLUSIVE_CLEAR_LOGS:
        print("🧹 Limpiando LOGS de all_inclusive...")
        total_limpiados += clear_files(RUTA_LOGS_ALL_INCLUSIVE)
    else:
        print("⏭️ LOGS de all_inclusive omitidos.")

    print("")
    print("========== RESUMEN LIMPIEZA ==========")
    print(f"🏨 Hotel: {EJECUTABLE}")
    print(f"📄 Total archivos procesados: {total_limpiados}")
    print("✅ Todo limpio :).")
    print("======================================")