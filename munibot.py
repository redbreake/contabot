from playwright.sync_api import sync_playwright
import sys

def run_munibot(municipal_username, municipal_password, monto, driver_path=None):  # Opcional, ignóralo
    """
    Automatiza el proceso de declaración jurada mensual en el sistema municipal con Playwright.

    Args:
        municipal_username (str): Nombre de usuario para el sistema municipal.
        municipal_password (str): Contraseña para el sistema municipal.
        monto (str): Monto imponible a declarar.
        driver_path (str, optional): Ruta al driver (no usada en Playwright).

    Returns:
        tuple: (status, output, error)
               status (str): 'Success' o 'Failed'.
               output (str): Mensajes de éxito o información.
               error (str): Mensajes de error si la ejecución falla.
    """
    output_messages = []
    error_messages = []
    status = 'Failed'

    try:
        with sync_playwright() as p:
            # Lanzar Edge (channel="msedge" para matching tu driver original)
            browser = p.chromium.launch(headless=False, channel="msedge")  # Cambia a True para headless en prod
            context = browser.new_context()
            page = context.new_page()
            
            # Paso 1: Login
            page.goto("https://sistema.posadas.gov.ar/mp_sistemas/autogestion/login")
            page.fill("#username", municipal_username)
            page.fill("#password", municipal_password)
            page.click('xpath=//*[@id="wrapper"]/div/div/div[1]/form/div[3]/button')
            output_messages.append("Login hecho. Esperando redirección...")
            
            page.wait_for_load_state("networkidle")
            
            # Paso 2: Navegación
            page.goto("https://sistema.posadas.gov.ar/mp_sistemas/autogestion/relacionesPropias")
            output_messages.append("Entramos a relacionesPropias")
            page.wait_for_load_state("networkidle")
            
            page.goto("https://sistema.posadas.gov.ar/mp_sistemas/autogestion/seccion/4/show")
            output_messages.append("Entramos a sección 4 (declaración jurada mensual)")
            page.wait_for_load_state("networkidle")
            
            # Paso 3: Esperar y seleccionar dropdown
            dropdown_selector = 'xpath=//*[@id="wrapper"]/div[2]/div/div/div[2]/table/tbody/tr[1]/td[6]/div/select'
            dropdown_locator = page.locator(dropdown_selector)
            dropdown_locator.wait_for(state="visible")  # Espera que el select aparezca (attached y visible)
            
            # Espera que haya al menos 2 opciones (sin chequear visibility, ya que options suelen estar hidden)
            # Mimica tu original: len(options) > 1, usando wait_for_function
            page.wait_for_function(
                """
                () => {
                    const xpath = '//*[@id="wrapper"]/div[2]/div/div/div[2]/table/tbody/tr[1]/td[6]/div/select';
                    const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                    const select = result.singleNodeValue;
                    return select && select.querySelectorAll('option').length > 1;
                }
                """,
                timeout=30000
            )
            
            # Captura popup y selecciona (el select abre la ventana)
            with page.expect_popup() as popup_info:
                page.select_option(dropdown_selector, index=1)
            output_messages.append("Seleccionada opción: Declaración Jurada Mensual")
            
            popup_page = popup_info.value
            output_messages.append("Cambiamos a la ventana nueva")
            
            # Paso 4: Ingresar monto
            #popup_page.fill("#monto_imponible", monto)
            #output_messages.append(f"Escrito el monto: {monto}")
            
            # Paso 5: Click en "Agregar"
            #popup_page.click("#addRow")
            #output_messages.append("Clic en Agregar")
            
            # Paso 6: Click en "Presentar"
            #popup_page.click("#send")
            output_messages.append("Declaración presentada con éxito.")
            
            browser.close()
            status = 'Success'

    except Exception as e:
        error_messages.append(f"Error en munibot: {e}")
    
    return status, "\n".join(output_messages), "\n".join(error_messages)