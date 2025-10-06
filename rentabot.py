# rentabot_playwright.py

import os
import time
import pandas as pd
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
from pathlib import Path

# ==============================================================================
# FUNCIÓN PARA PROCESAR EL ARCHIVO EXCEL (sin cambios)
# ==============================================================================
def procesar_excel_rentas(ruta_archivo):
    try:
        print("\n--- INICIANDO PROCESAMIENTO DEL ARCHIVO EXCEL ---")
        df = pd.read_excel(ruta_archivo, decimal=',', thousands='.')
        df.columns = [col.strip() for col in df.columns]

        totales = {'PERCEPCIÓN': 0.0, 'RETENCIÓN': 0.0}

        def clasificar_por_columna(row):
            if pd.notna(row.get('ALÍC.')): return 'PERCEPCIÓN'
            elif pd.notna(row.get('COEF.')): return 'RETENCIÓN'
            else: return 'OTRO'
            
        df['TIPO'] = df.apply(clasificar_por_columna, axis=1)
        
        resultados = df.groupby('TIPO').agg({'TOTAL': 'sum'}).reset_index()
        
        if resultados.empty:
            print("No se encontraron datos para procesar.")
            return None

        print("\n✅ RESUMEN EXTRAÍDO DEL ARCHIVO:")
        for index, fila in resultados.iterrows():
            tipo = fila['TIPO']
            total_monto = fila['TOTAL']
            if tipo in totales:
                totales[tipo] = total_monto
            print(f"Total {tipo}: {total_monto:,.2f}")
        
        print("-" * 40)
        print("\n--- PROCESAMIENTO FINALIZADO ---")
        return totales

    except Exception as e:
        print(f"Error inesperado al procesar el archivo Excel: {e}")
        return None

# ==============================================================================
# FUNCIÓN PRINCIPAL CON PLAYWRIGHT (clic en código "472120" post-búsqueda)
# ==============================================================================
def run_rentabot(ruta_archivo):
    """
    Automatiza el proceso de obtención de datos de rentas y presentación de DDJJ con Playwright.

    Args:
        ruta_archivo (str): Ruta al archivo Excel de rentas (opcional; si no, descarga primero).

    Returns:
        tuple: (status, output, error)
               status (str): 'Success' o 'Failed'.
               output (str): Mensajes de éxito o información.
               error (str): Mensajes de error si la ejecución falla.
    """
    output_messages = []
    error_messages = []
    status = 'Failed'

    # Valor fijo para base imponible (para test; después lo sacamos de la página o Excel)
    base_imponible = "1000.00"

    # Configuración de descargas (igual que original)
    directorio_descargas = os.path.join(os.getcwd(), "descargas_rentas")
    os.makedirs(directorio_descargas, exist_ok=True)
    output_messages.append(f"Los archivos se guardarán en: {directorio_descargas}")

    # Puerto debug para conexión a sesión activa (igual que tu debuggerAddress)
    debug_port = "http://127.0.0.1:9222"

    try:
        with sync_playwright() as p:
            print("Conectando al navegador Edge en modo debug...")
            browser = p.chromium.connect_over_cdp(debug_port)
            context = browser.contexts[0]  # Usa el contexto existente (con sesión logueada)
            page = context.pages[0] if context.pages else context.new_page()  # Usa página activa o crea nueva
            
            output_messages.append("¡Conexión exitosa!")

            # --- FASE 1: OBTENCIÓN DE DATOS DE RENTAS ---
            output_messages.append("\n--- INICIANDO FASE 1: OBTENCIÓN DE DATOS DE RENTAS ---")
            page.goto("https://extranet.atm.misiones.gob.ar/Extranet/Aplicaciones/consultas_ret_perc.php")
            
            mes_a_declarar = datetime.today().replace(day=1) - timedelta(days=1)
            periodo_consulta = mes_a_declarar.strftime("%Y/%m")
            output_messages.append(f"Calculando período a consultar: {periodo_consulta}")
            
            # Ingreso de período
            page.fill("#periodo_desde", periodo_consulta)
            page.fill("#periodo_hasta", periodo_consulta)
            output_messages.append("Período ingresado.")

            # Limpieza de archivos antiguos
            for f in os.listdir(directorio_descargas):
                if f.endswith(('.xlsx', '.xls')):
                    os.remove(os.path.join(directorio_descargas, f))

            # Click en GENERAR EXCEL y espera descarga
            with page.expect_download(timeout=60000) as download_info:  # 60s timeout
                page.click("#btn_excel")
            download = download_info.value
            output_messages.append("Haciendo clic en 'GENERAR EXCEL'... Esperando la descarga...")

            # Renombrar archivo descargado
            nombre_nuevo = os.path.join(directorio_descargas, f"Rentas_{periodo_consulta.replace('/', '-')}.xlsx")
            download.save_as(nombre_nuevo)
            archivo_descargado = nombre_nuevo
            output_messages.append(f"¡Archivo descargado y renombrado!: {archivo_descargado}")

            datos_ddjj = None
            if archivo_descargado and os.path.exists(archivo_descargado):
                datos_ddjj = procesar_excel_rentas(archivo_descargado)
                if datos_ddjj:
                    output_messages.append(f"Datos a declarar recuperados: Retenciones={datos_ddjj.get('RETENCIÓN', 0):,.2f}, Percepciones={datos_ddjj.get('PERCEPCIÓN', 0):,.2f}")
            else:
                error_messages.append("ATENCIÓN: El archivo de Rentas no se descargó. No se puede continuar.")

            # --- FASE 2: NAVEGACIÓN Y PRESENTACIÓN DE DDJJ ---
            if datos_ddjj is not None:
                output_messages.append("\n--- INICIANDO FASE 2: PRESENTACIÓN DE DDJJ ---")
                
                # Paso 1: Abrir menú hamburger
                page.click(".menu-toggler")
                output_messages.append("Abriendo el menú lateral (clic en el 'hamburger')...")
                page.wait_for_timeout(2000)  # Wait extra para que el menú se estabilice
                
                # Paso 2: Clic directo en "Ingresos Brutos"
                ingresos_brutos_locator = page.get_by_text("Ingresos Brutos")
                ingresos_brutos_locator.wait_for(state="visible", timeout=5000)
                ingresos_brutos_locator.click()
                output_messages.append("Clic en 'Ingresos Brutos' para expandir...")
                page.wait_for_timeout(1000)  # Pequeño delay para expansión JS
                
                # Paso 3: Clic en submenú "Presentación DDJJ (IIBB Directo)"
                ddjj_locator = page.get_by_text("Presentación DDJJ (IIBB Directo)")
                ddjj_locator.wait_for(state="visible", timeout=5000)
                ddjj_locator.click()
                output_messages.append("Haciendo clic en 'Presentación DDJJ (IIBB Directo)'...")
                output_messages.append("✅ Navegación a Presentación DDJJ completada.")
                
                # Poner fecha/período
                periodo_mes = mes_a_declarar.strftime("%m")
                periodo_anio = mes_a_declarar.strftime("%Y")
                output_messages.append(f"Seleccionando Período: Mes {periodo_mes}, Año {periodo_anio}")
                
                page.select_option("#mes_pos_fiscal", periodo_mes)
                page.fill('[name="anio_pos_fiscal"]', periodo_anio)
                
                # Click en Buscar
                page.click("#btn_buscar")
                output_messages.append("Haciendo clic en 'Buscar'...")
                page.wait_for_load_state("networkidle")  # Espera que la tabla cargue post-búsqueda
                
                # Espera y clic en la celda <td> específica con "0,00"
                td_selector = 'td[role="gridcell"][aria-describedby="obligaciones_grid_i_impuesto_det"][title="0,00"]'
                td_locator = page.locator(td_selector)
                td_locator.wait_for(state="visible", timeout=20000)  # Espera que aparezca en la grid
                td_locator.click()
                output_messages.append('Clic en celda "0,00" de la grid...')
                
                # Click en botón Editar
                editar_locator = page.locator("#btn_editar")
                editar_locator.wait_for(state="visible", timeout=5000)  # Espera que se active post-selección
                editar_locator.click()
                output_messages.append("Haciendo clic en 'Editar'...")
                page.wait_for_load_state("networkidle")  # Espera que cargue el form de detalles
                output_messages.append("✅ Obligación editada/abierto form correctamente.")
                
                # --- AGREGANDO RUBRO Y LLENANDO FORM (clic en código "472120" post-búsqueda) ---
                output_messages.append("\n--- AGREGANDO RUBRO Y LLENANDO FORM ---")
                
                # Clic en "Agregar Rubro"
                add_rubro_locator = page.locator("#add_rubro_a_grid")
                add_rubro_locator.wait_for(state="visible", timeout=10000)
                add_rubro_locator.click()
                output_messages.append("Clic en 'Agregar Rubro'...")
                page.wait_for_selector("#d_actividad_lupa", timeout=10000)
                page.wait_for_timeout(2000)  # Delay para modal
                
                # Doble clic en lupa Actividad
                actividad_lupa_locator = page.locator("#d_actividad_lupa")
                actividad_lupa_locator.wait_for(state="visible", timeout=5000)
                actividad_lupa_locator.dblclick()
                output_messages.append("Doble clic en lupa 'Actividad'...")
                page.wait_for_timeout(3000)  # Delay para dropdown/search load
                
                # Búsqueda
                page.fill('input[type="text"]:visible', "venta al por menor")  # Fill en input visible
                output_messages.append("Buscando 'venta al por menor' en Actividad...")
                page.wait_for_timeout(2000)  # Delay para filtro
                
                # Clic en el código "472120" (o 47210) en el resultado td
                page.click('td:has-text("472120")')  # Cambia a "47210" si es el código exacto
                output_messages.append("Clic en código '472120' para seleccionar...")
                page.wait_for_timeout(1000)  # Delay para cierre dropdown
                
                # Screenshot post-selección
                page.screenshot(path="debug_actividad.png")
                output_messages.append("Screenshot guardado: debug_actividad.png")
                
                # Clic en lupa Facturación y select #0
                facturacion_lupa_locator = page.locator("#d_facturacion_lupa")
                facturacion_lupa_locator.wait_for(state="visible", timeout=5000)
                facturacion_lupa_locator.click()
                output_messages.append("Clic en lupa 'Facturación'...")
                page.wait_for_selector("#0", timeout=5000)
                page.click("#0")
                output_messages.append("Seleccionada opción '0' en Facturación...")
                page.wait_for_timeout(1000)
                
                # Rellenar base imponible
                page.fill("#i_base_imponible", base_imponible)
                output_messages.append(f"Rellenada base imponible: {base_imponible}")
                page.wait_for_timeout(1000)
                
                # Clic en lupa Alícuota y select #0
                alicuota_lupa_locator = page.locator("#p_alicuota_lupa")
                alicuota_lupa_locator.wait_for(state="visible", timeout=5000)
                alicuota_lupa_locator.click()
                output_messages.append("Clic en lupa 'Alícuota'...")
                page.wait_for_selector("#0", timeout=5000)
                page.click("#0")
                output_messages.append("Seleccionada opción '0' en Alícuota...")
                page.wait_for_timeout(1000)
                
                # Clic en lupa Bonificación y select #1
                bonificacion_lupa_locator = page.locator("#p_bonificacion_lupa")
                bonificacion_lupa_locator.wait_for(state="visible", timeout=5000)
                bonificacion_lupa_locator.click()
                output_messages.append("Clic en lupa 'Bonificación'...")
                page.wait_for_selector("#1", timeout=5000)
                page.click("#1")
                output_messages.append("Seleccionada opción '1' en Bonificación...")
                page.wait_for_timeout(1000)
                
                # Clic en Guardar
                guardar_locator = page.locator("#sData")
                guardar_locator.wait_for(state="visible", timeout=5000)
                guardar_locator.click()
                output_messages.append("Clic en 'Guardar'...")
                page.wait_for_load_state("networkidle")
                output_messages.append("✅ Rubro agregado y guardado exitosamente.")
                
                # Screenshot final
                page.screenshot(path="debug_final.png")
                output_messages.append("Screenshot final guardado: debug_final.png")
            
            output_messages.append("\nPROCESO COMPLETO DEL BOT FINALIZADO.")
            browser.close()  # Cierra la conexión (no el browser físico)
            status = 'Success'

    except Exception as e:
        error_messages.append(f"Error durante el proceso: {e}")
    
    return status, "\n".join(output_messages), "\n".join(error_messages)

# ==============================================================================
# EJECUCIÓN DIRECTA (para tests; en Django, llamá run_rentabot)
# ==============================================================================
if __name__ == "__main__":
    # Ejemplo: run_rentabot("path/to/tu_archivo.xlsx") o None para descargar primero
    status, output, error = run_rentabot(None)  # None = descarga auto
    print(output)
    if error:
        print(f"Error: {error}")